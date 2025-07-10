"""
Main crypto trading bot class that orchestrates all components
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from .api_handlers import DexscreenerAPI, RugcheckAPI
from .rug_detector import RugDetector
from .volume_filter import VolumeFilter
from .telegram_notifier import TelegramNotifier
from .database import Database
from .postgresql_database import PostgreSQLDatabase
from utils.rate_limiter import RateLimiter

class CryptoTradingBot:
    """Main crypto trading bot class"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.dexscreener_api = DexscreenerAPI(config)
        self.rugcheck_api = RugcheckAPI(config)
        self.rug_detector = RugDetector(config)
        self.volume_filter = VolumeFilter(config)
        self.telegram_notifier = TelegramNotifier(config)
        # Initialize database (PostgreSQL or SQLite)
        if getattr(config, 'use_postgresql', True):
            self.database = PostgreSQLDatabase(config)
        else:
            self.database = Database(config)
        self.rate_limiter = RateLimiter(config.api_calls_per_minute)
        
        # Bot state
        self.is_running = False
        self.processed_tokens = set()
        self.last_scan_time = {}
        self.alerts_sent_this_minute = 0
        self.last_minute_reset = datetime.now().replace(second=0, microsecond=0)
        self.pending_alerts = []  # Queue of tokens ready to send
        
    async def start(self):
        """Start the crypto trading bot"""
        self.logger.info("Initializing crypto trading bot...")
        
        # Initialize database
        await self.database.initialize()
        
        # Start telegram bot
        await self.telegram_notifier.start()
        
        self.is_running = True
        self.logger.info("Crypto trading bot started successfully")
        
        # Start main monitoring loop
        await self._monitoring_loop()
    
    async def stop(self):
        """Stop the crypto trading bot"""
        self.logger.info("Stopping crypto trading bot...")
        self.is_running = False
        
        # Stop telegram bot
        await self.telegram_notifier.stop()
        
        # Close database
        await self.database.close()
        
        self.logger.info("Crypto trading bot stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop that scans for trading opportunities"""
        scan_count = 0
        while self.is_running:
            try:
                # Check and reset alerts per minute counter
                current_minute = datetime.now().replace(second=0, microsecond=0)
                if current_minute > self.last_minute_reset:
                    self.alerts_sent_this_minute = 0
                    self.last_minute_reset = current_minute
                    self.logger.info(f"Reset alerts counter for new minute. Target: {self.config.alerts_per_minute_target} alerts")
                
                # Clear processed tokens every 100 scans (about 15-20 minutes) to allow re-checking
                scan_count += 1
                if scan_count % 100 == 0:
                    # Keep only recent tokens to avoid re-alerting too soon
                    current_time = datetime.now()
                    tokens_to_remove = []
                    for token_key in self.processed_tokens:
                        if token_key not in self.last_scan_time:
                            tokens_to_remove.append(token_key)
                        elif current_time - self.last_scan_time[token_key] > timedelta(minutes=self.config.token_cooldown_minutes):
                            tokens_to_remove.append(token_key)
                    
                    for token_key in tokens_to_remove:
                        self.processed_tokens.discard(token_key)
                        self.last_scan_time.pop(token_key, None)
                    
                    self.logger.info(f"Cleaned up {len(tokens_to_remove)} old tokens from cache")
                
                # Scan all supported blockchains concurrently
                tasks = []
                for chain in self.config.supported_chains:
                    task = self._scan_chain(chain)
                    tasks.append(task)
                
                # Wait for all chain scans to complete
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Send pending alerts if we have any and haven't reached the target
                await self._send_pending_alerts()
                
                # Log scan completion
                self.logger.info(f"Completed scan cycle for {len(self.config.supported_chains)} chains. Alerts sent this minute: {self.alerts_sent_this_minute}/{self.config.alerts_per_minute_target}")
                
                # Send periodic status update every 300 scans (about 50 minutes)
                if scan_count % 300 == 0:
                    await self.telegram_notifier.send_alert({
                        'token_name': '🤖 Status Update',
                        'token_symbol': 'BOT',
                        'token_address': 'N/A',
                        'chain': 'system',
                        'price_usd': 0,
                        'volume_24h': 0,
                        'liquidity_usd': 0,
                        'market_cap': 0,
                        'risk_score': 0,
                        'tax_percentage': 0,
                        'message': f'Bot is active! Scanned {scan_count} cycles. Working perfectly to find quality tokens for you.'
                    })
                
                # Wait before next scan (reduced for more frequent scanning)
                await asyncio.sleep(self.config.request_delay_seconds * 5)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _scan_chain(self, chain: str):
        """Scan a specific blockchain for trading opportunities"""
        try:
            self.logger.info(f"Scanning {chain} for trading opportunities...")
            
            # Apply rate limiting
            await self.rate_limiter.wait()
            
            # Fetch token data from Dexscreener
            tokens = await self.dexscreener_api.get_tokens(chain)
            
            if not tokens:
                self.logger.warning(f"No tokens found for {chain}")
                return
            
            # Filter tokens by market cap
            filtered_tokens = self._filter_by_market_cap(tokens)
            self.logger.info(f"Found {len(filtered_tokens)} tokens under ${self.config.max_market_cap:,.0f} market cap on {chain}")
            
            # Process each token
            for token in filtered_tokens:
                await self._process_token(token, chain)
                
        except Exception as e:
            self.logger.error(f"Error scanning {chain}: {e}")
    
    def _filter_by_market_cap(self, tokens: List[Dict]) -> List[Dict]:
        """Filter tokens by market cap threshold"""
        filtered = []
        for token in tokens:
            try:
                market_cap = token.get('fdv', 0) or token.get('marketCap', 0)
                if (market_cap and 
                    self.config.min_market_cap <= market_cap < self.config.max_market_cap):
                    filtered.append(token)
            except (ValueError, TypeError):
                continue
        return filtered
    
    async def _process_token(self, token: Dict, chain: str):
        """Process a single token for trading opportunities"""
        try:
            # Extract token information
            token_address = token.get('baseToken', {}).get('address', '')
            token_name = token.get('baseToken', {}).get('name', 'Unknown')
            token_symbol = token.get('baseToken', {}).get('symbol', 'Unknown')
            
            # Skip if already processed recently (check database for recent alerts)
            # Check both by token address AND by token name to prevent duplicates
            token_key = f"{chain}:{token_address}"
            
            # Check if we sent an alert for this token recently (by address)
            recent_alert = await self.database.check_recent_alert(
                token_address, chain, minutes=self.config.token_cooldown_minutes
            )
            if recent_alert:
                self.logger.info(f"Skipping {token_name} - alert already sent {recent_alert:.0f} minutes ago")
                return
            
            # Additional check by token name to prevent same token with different addresses
            recent_name_alert = await self.database.check_recent_alert_by_name(
                token_name, chain, minutes=self.config.token_cooldown_minutes
            )
            if recent_name_alert:
                self.logger.info(f"Skipping {token_name} - same token name already sent {recent_name_alert:.0f} minutes ago")
                return
            
            # Check token age
            if not self._is_token_old_enough(token):
                self.logger.debug(f"Skipping {token_name} ({token_symbol}) - too young")
                return
            
            # Apply rate limiting for API calls
            await self.rate_limiter.wait()
            
            # Perform rug pull detection
            rug_check_result = await self.rug_detector.check_token(token_address, chain)
            
            if rug_check_result.get('is_rug_risk', False):
                self.logger.info(f"Skipping {token_name} ({token_symbol}) - rug risk detected")
                await self._log_token_check(token, chain, "rug_risk", rug_check_result)
                return
            
            # Apply additional safety filters
            if not self._passes_safety_filters(token):
                self.logger.debug(f"Token {token_name} ({token_symbol}) failed safety filters, but adding to pending queue")
                # Add to pending alerts queue instead of skipping
                self.pending_alerts.append({
                    'token': token,
                    'chain': chain,
                    'rug_check_result': rug_check_result,
                    'priority': 'low'
                })
                await self._log_token_check(token, chain, "safety_filter_failed", {})
                return
            
            # Check for fake volume
            if self.volume_filter.is_fake_volume(token):
                self.logger.debug(f"Token {token_name} ({token_symbol}) has fake volume but adding to pending queue")
                # Add to pending alerts queue instead of skipping
                self.pending_alerts.append({
                    'token': token,
                    'chain': chain,
                    'rug_check_result': rug_check_result,
                    'priority': 'low'
                })
                await self._log_token_check(token, chain, "fake_volume", {})
                return
            
            # Token passed all checks - send alert immediately
            alert_sent = await self._send_trading_alert(token, chain, rug_check_result)
            
            # If alert was sent, increment counter
            if alert_sent:
                self.alerts_sent_this_minute += 1
            
            # Only mark as processed if alert was actually sent
            if alert_sent:
                # Mark as processed with timestamp
                self.processed_tokens.add(token_key)
                self.last_scan_time[token_key] = datetime.now()
            
            # Log successful check
            await self._log_token_check(token, chain, "passed", rug_check_result)
            
        except Exception as e:
            self.logger.error(f"Error processing token {token.get('baseToken', {}).get('name', 'Unknown')}: {e}")
    
    def _passes_safety_filters(self, token: Dict) -> bool:
        """Apply comprehensive safety filters to token"""
        try:
            # Extract token data
            liquidity_usd = token.get('liquidity', {}).get('usd', 0)
            volume_24h = token.get('volume', {}).get('h24', 0) 
            market_cap = token.get('fdv', 0) or token.get('marketCap', 0)
            txns = token.get('txns', {})
            
            # 1. Minimum Liquidity Filter
            if liquidity_usd < self.config.min_liquidity_usd:
                self.logger.info(f"Failed liquidity filter for {token.get('baseToken', {}).get('name', 'Unknown')}: ${liquidity_usd:.2f} < ${self.config.min_liquidity_usd}")
                return False
            
            # 2. Minimum Market Cap (already checked in filter_by_market_cap, but double-check)
            if market_cap < self.config.min_market_cap:
                self.logger.debug(f"Failed market cap filter: ${market_cap:.2f} < ${self.config.min_market_cap}")
                return False
            
            # 3. Minimum 24h Volume (more lenient)
            if volume_24h < self.config.min_volume_24h:
                self.logger.debug(f"Low volume for {token.get('baseToken', {}).get('name', 'Unknown')}: ${volume_24h:.2f} < ${self.config.min_volume_24h}")
                # Don't return False for low volume - allow it through
            
            # 4. Minimum Unique Transactions (more lenient)
            buys_1h = txns.get('h1', {}).get('buys', 0)
            sells_1h = txns.get('h1', {}).get('sells', 0)
            total_txns = buys_1h + sells_1h
            
            if buys_1h < self.config.min_unique_transactions:
                self.logger.debug(f"Low transaction activity for {token.get('baseToken', {}).get('name', 'Unknown')}: {buys_1h} buys")
                # Don't return False for low activity - allow it through
            
            # 5. Flag tokens with only 1 buyer/seller (suspicious) - RELAXED
            if buys_1h == 0:  # Only block if NO buys at all
                self.logger.debug(f"No buy transactions in last hour")
                return False
            
            # 6. Check for reasonable buy/sell ratio (avoid pump schemes) - RELAXED
            if sells_1h > 0:
                buy_sell_ratio = buys_1h / sells_1h
                if buy_sell_ratio > 20:  # Only block extreme cases (was 10)
                    self.logger.debug(f"Extremely suspicious buy/sell ratio: {buy_sell_ratio:.2f}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Error in safety filters: {e}")
            return False
    
    def _is_token_old_enough(self, token: Dict) -> bool:
        """Check if token is old enough based on configuration"""
        try:
            # Try to get token creation time from various fields
            created_at = token.get('pairCreatedAt')
            if not created_at:
                # If no creation time, assume it's old enough
                return True
            
            # Parse creation time
            if isinstance(created_at, (int, float)):
                creation_time = datetime.fromtimestamp(created_at / 1000)
            else:
                creation_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            # Check if token is old enough
            min_age = timedelta(minutes=self.config.min_token_age_minutes)
            return datetime.now() - creation_time >= min_age
            
        except Exception as e:
            self.logger.debug(f"Error checking token age: {e}")
            return True  # Default to allowing the token
    
    def _get_token_age(self, token: Dict) -> str:
        """Get token age as a human-readable string"""
        try:
            # Try to get token creation time from various fields
            created_at = token.get('pairCreatedAt')
            if not created_at:
                return "Unknown"
            
            # Parse creation time
            if isinstance(created_at, (int, float)):
                creation_time = datetime.fromtimestamp(created_at / 1000)
            else:
                creation_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            # Calculate age
            age = datetime.now() - creation_time
            
            # Format age as human-readable string
            if age.days > 0:
                return f"{age.days} days"
            elif age.seconds >= 3600:
                hours = age.seconds // 3600
                return f"{hours} hours"
            elif age.seconds >= 60:
                minutes = age.seconds // 60
                return f"{minutes} minutes"
            else:
                return "Less than 1 minute"
                
        except Exception as e:
            self.logger.debug(f"Error calculating token age: {e}")
            return "Unknown"
    
    async def _send_trading_alert(self, token: Dict, chain: str, rug_check_result: Dict) -> bool:
        """Send trading alert via Telegram"""
        try:
            # Extract token information
            base_token = token.get('baseToken', {})
            token_name = base_token.get('name', 'Unknown')
            token_symbol = base_token.get('symbol', 'Unknown')
            token_address = base_token.get('address', '')
            
            # Price and volume information
            price_usd = token.get('priceUsd', 0)
            volume_24h = token.get('volume', {}).get('h24', 0)
            liquidity_usd = token.get('liquidity', {}).get('usd', 0)
            market_cap = token.get('fdv', 0) or token.get('marketCap', 0)
            
            # Calculate risk score and token age
            risk_score = self._calculate_risk_score(token, rug_check_result)
            token_age = self._get_token_age(token)
            
            # Create alert message
            alert_data = {
                'token_name': token_name,
                'token_symbol': token_symbol,
                'token_address': token_address,
                'chain': chain,
                'price_usd': price_usd,
                'volume_24h': volume_24h,
                'liquidity_usd': liquidity_usd,
                'market_cap': market_cap,
                'risk_score': risk_score,
                'tax_percentage': rug_check_result.get('tax_percentage', 0),
                'chart_url': token.get('url', ''),
                'pair_address': token.get('pairAddress', ''),
                'token_age': token_age
            }
            
            # Send alert - returns True if successful
            alert_sent = await self.telegram_notifier.send_alert(alert_data)
            
            if alert_sent:
                # Log alert to database only if successfully sent
                await self._log_alert_to_database(alert_data)
                self.logger.info(f"Sent trading alert for {token_name} ({token_symbol}) on {chain}")
                return True
            else:
                self.logger.info(f"Alert not sent for {token_name} ({token_symbol}) - likely in cooldown or rate limited")
                return False
            
        except Exception as e:
            self.logger.error(f"Error sending trading alert: {e}")
            return False
    
    async def _log_alert_to_database(self, alert_data: Dict):
        """Log sent alert to database"""
        try:
            await self.database.log_alert({
                'token_name': alert_data['token_name'],
                'token_symbol': alert_data['token_symbol'],
                'token_address': alert_data['token_address'],
                'chain': alert_data['chain'],
                'price_usd': alert_data['price_usd'],
                'volume_24h': alert_data['volume_24h'],
                'liquidity_usd': alert_data['liquidity_usd'],
                'market_cap': alert_data['market_cap'],
                'risk_score': alert_data['risk_score'],
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            self.logger.error(f"Error logging alert to database: {e}")
    
    def _calculate_risk_score(self, token: Dict, rug_check_result: Dict) -> float:
        """Calculate risk score for a token (0-100, lower is better)"""
        risk_score = 0.0
        
        # Tax percentage risk
        tax_percentage = rug_check_result.get('tax_percentage', 0)
        risk_score += min(tax_percentage * 2, 30)  # Max 30 points for tax
        
        # Liquidity risk
        liquidity_usd = token.get('liquidity', {}).get('usd', 0)
        if liquidity_usd < self.config.min_liquidity_usd:
            risk_score += 20
        elif liquidity_usd < self.config.min_liquidity_usd * 2:
            risk_score += 10
        
        # Market cap risk
        market_cap = token.get('fdv', 0) or token.get('marketCap', 0)
        if market_cap < 100_000:
            risk_score += 15
        elif market_cap < 500_000:
            risk_score += 10
        elif market_cap < 1_000_000:
            risk_score += 5
        
        # Volume risk
        volume_24h = token.get('volume', {}).get('h24', 0)
        if volume_24h < 1000:
            risk_score += 10
        
        # Honeypot risk
        if rug_check_result.get('is_honeypot', False):
            risk_score += 50
        
        return min(risk_score, 100.0)
    
    async def _log_token_check(self, token: Dict, chain: str, status: str, check_result: Dict):
        """Log token check to database"""
        try:
            base_token = token.get('baseToken', {})
            
            txns = token.get('txns', {})
            buys_1h = txns.get('h1', {}).get('buys', 0)
            sells_1h = txns.get('h1', {}).get('sells', 0)
            
            log_data = {
                'timestamp': datetime.now(),
                'chain': chain,
                'token_address': base_token.get('address', ''),
                'token_name': base_token.get('name', 'Unknown'),
                'token_symbol': base_token.get('symbol', 'Unknown'),
                'price_usd': token.get('priceUsd', 0),
                'volume_24h': token.get('volume', {}).get('h24', 0),
                'liquidity_usd': token.get('liquidity', {}).get('usd', 0),
                'market_cap': token.get('fdv', 0) or token.get('marketCap', 0),
                'status': status,
                'risk_score': self._calculate_risk_score(token, check_result),
                'tax_percentage': check_result.get('tax_percentage', 0),
                'is_honeypot': check_result.get('is_honeypot', False),
                'buys_1h': buys_1h,
                'sells_1h': sells_1h
            }
            
            await self.database.log_token_check(log_data)
            
        except Exception as e:
            self.logger.error(f"Error logging token check: {e}")
    
    async def _send_pending_alerts(self):
        """Send pending alerts if we haven't reached the target alerts per minute"""
        if self.alerts_sent_this_minute >= self.config.alerts_per_minute_target:
            return
            
        alerts_to_send = self.config.alerts_per_minute_target - self.alerts_sent_this_minute
        
        if not self.pending_alerts:
            return
            
        # Sort pending alerts by priority (high priority first)
        self.pending_alerts.sort(key=lambda x: x.get('priority', 'medium') == 'high', reverse=True)
        
        alerts_sent = 0
        for alert_data in self.pending_alerts[:alerts_to_send]:
            try:
                alert_sent = await self._send_trading_alert(
                    alert_data['token'], 
                    alert_data['chain'], 
                    alert_data['rug_check_result']
                )
                
                if alert_sent:
                    alerts_sent += 1
                    self.alerts_sent_this_minute += 1
                    
                    # Remove from pending alerts
                    self.pending_alerts.remove(alert_data)
                    
                    # Mark as processed
                    token_address = alert_data['token'].get('baseToken', {}).get('address', '')
                    token_key = f"{alert_data['chain']}:{token_address}"
                    self.processed_tokens.add(token_key)
                    self.last_scan_time[token_key] = datetime.now()
                    
                    if alerts_sent >= alerts_to_send:
                        break
                        
            except Exception as e:
                self.logger.error(f"Error sending pending alert: {e}")
                
        if alerts_sent > 0:
            self.logger.info(f"Sent {alerts_sent} pending alerts to reach target of {self.config.alerts_per_minute_target} alerts per minute")
