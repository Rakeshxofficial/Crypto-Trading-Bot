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
                # Clear processed tokens every 200 scans (about 30-40 minutes) to re-alert on good opportunities
                scan_count += 1
                if scan_count % 200 == 0:
                    self.processed_tokens.clear()
                    self.logger.info("Cleared processed tokens cache for fresh alerts")
                
                # Scan all supported blockchains concurrently
                tasks = []
                for chain in self.config.supported_chains:
                    task = self._scan_chain(chain)
                    tasks.append(task)
                
                # Wait for all chain scans to complete
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log scan completion
                self.logger.info(f"Completed scan cycle for {len(self.config.supported_chains)} chains")
                
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
                
                # Wait before next scan
                await asyncio.sleep(self.config.request_delay_seconds * 10)
                
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
            token_key = f"{chain}:{token_address}"
            
            # Check if we sent an alert for this token in the last 60 minutes to prevent duplicates
            recent_alert = await self.database.check_recent_alert(token_address, chain, minutes=60)
            if recent_alert:
                self.logger.info(f"Skipping {token_name} - alert already sent {recent_alert:.0f} minutes ago")
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
                self.logger.info(f"Skipping {token_name} ({token_symbol}) - failed safety filters")
                await self._log_token_check(token, chain, "safety_filter_failed", {})
                return
            
            # Check for fake volume
            if self.volume_filter.is_fake_volume(token):
                self.logger.info(f"Skipping {token_name} ({token_symbol}) - fake volume detected")
                await self._log_token_check(token, chain, "fake_volume", {})
                return
            
            # Token passed all checks - send alert
            await self._send_trading_alert(token, chain, rug_check_result)
            
            # Mark as processed
            self.processed_tokens.add(token_key)
            
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
                self.logger.debug(f"Failed liquidity filter: ${liquidity_usd:.2f} < ${self.config.min_liquidity_usd}")
                return False
            
            # 2. Minimum Market Cap (already checked in filter_by_market_cap, but double-check)
            if market_cap < self.config.min_market_cap:
                self.logger.debug(f"Failed market cap filter: ${market_cap:.2f} < ${self.config.min_market_cap}")
                return False
            
            # 3. Minimum 24h Volume
            if volume_24h < self.config.min_volume_24h:
                self.logger.debug(f"Failed volume filter: ${volume_24h:.2f} < ${self.config.min_volume_24h}")
                return False
            
            # 4. Minimum Unique Transactions
            buys_1h = txns.get('h1', {}).get('buys', 0)
            sells_1h = txns.get('h1', {}).get('sells', 0)
            total_txns = buys_1h + sells_1h
            
            if buys_1h < self.config.min_unique_transactions:
                self.logger.debug(f"Failed transaction filter: {buys_1h} buys < {self.config.min_unique_transactions}")
                return False
            
            # 5. Flag tokens with only 1 buyer/seller (suspicious)
            if buys_1h <= 1 or sells_1h == 0:
                self.logger.debug(f"Suspicious transaction pattern: {buys_1h} buys, {sells_1h} sells")
                return False
            
            # 6. Check for reasonable buy/sell ratio (avoid pump schemes)
            if sells_1h > 0:
                buy_sell_ratio = buys_1h / sells_1h
                if buy_sell_ratio > 10 or buy_sell_ratio < 0.1:  # Too one-sided
                    self.logger.debug(f"Suspicious buy/sell ratio: {buy_sell_ratio:.2f}")
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
    
    async def _send_trading_alert(self, token: Dict, chain: str, rug_check_result: Dict):
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
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(token, rug_check_result)
            
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
                'pair_address': token.get('pairAddress', '')
            }
            
            # Send alert
            await self.telegram_notifier.send_alert(alert_data)
            
            # Log alert to database
            await self._log_alert_to_database(alert_data)
            
            self.logger.info(f"Sent trading alert for {token_name} ({token_symbol}) on {chain}")
            
        except Exception as e:
            self.logger.error(f"Error sending trading alert: {e}")
    
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
