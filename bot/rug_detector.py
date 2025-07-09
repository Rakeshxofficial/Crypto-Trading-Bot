"""
Rug pull detection logic and custom analysis
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class RugDetector:
    """Rug pull detection using multiple analysis methods"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    async def check_token(self, token_address: str, chain: str) -> Dict:
        """Comprehensive rug pull check for a token"""
        try:
            # Initialize result
            result = {
                'is_rug_risk': False,
                'is_honeypot': False,
                'tax_percentage': 0.0,
                'is_blacklisted': False,
                'liquidity_locked': False,
                'owner_renounced': False,
                'risk_score': 0.0,
                'risk_factors': []
            }
            
            # Try external API first (Rugcheck)
            from .api_handlers import RugcheckAPI
            rugcheck_api = RugcheckAPI(self.config)
            
            try:
                external_result = await rugcheck_api.check_token(token_address, chain)
                result.update(external_result)
                self.logger.debug(f"External rug check completed for {token_address}")
            except Exception as e:
                self.logger.warning(f"External rug check failed for {token_address}: {e}")
                # Continue with custom analysis
            
            # Perform custom analysis
            custom_result = await self._custom_rug_analysis(token_address, chain)
            
            # Combine results
            result = self._combine_results(result, custom_result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in rug detection for {token_address}: {e}")
            return self._safe_default_result()
    
    async def _custom_rug_analysis(self, token_address: str, chain: str) -> Dict:
        """Custom rug pull analysis logic"""
        result = {
            'is_rug_risk': False,
            'risk_factors': [],
            'custom_risk_score': 0.0
        }
        
        try:
            # Get token information for analysis
            from .api_handlers import DexscreenerAPI
            dexscreener_api = DexscreenerAPI(self.config)
            token_info = await dexscreener_api.get_token_info(token_address, chain)
            
            if not token_info:
                result['risk_factors'].append("Token information not available")
                result['custom_risk_score'] += 20
                return result
            
            # Analyze liquidity patterns
            liquidity_risk = self._analyze_liquidity(token_info)
            result['custom_risk_score'] += liquidity_risk
            
            # Analyze trading patterns
            trading_risk = self._analyze_trading_patterns(token_info)
            result['custom_risk_score'] += trading_risk
            
            # Analyze holder distribution
            holder_risk = self._analyze_holder_distribution(token_info)
            result['custom_risk_score'] += holder_risk
            
            # Analyze contract age
            age_risk = self._analyze_contract_age(token_info)
            result['custom_risk_score'] += age_risk
            
            # Determine if it's a rug risk
            if result['custom_risk_score'] > 60:
                result['is_rug_risk'] = True
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in custom rug analysis: {e}")
            return result
    
    def _analyze_liquidity(self, token_info: Dict) -> float:
        """Analyze liquidity patterns for rug pull indicators"""
        risk_score = 0.0
        
        try:
            # Get liquidity information
            liquidity_usd = token_info.get('liquidity', {}).get('usd', 0)
            
            # Check liquidity thresholds
            if liquidity_usd < self.config.min_liquidity_usd:
                risk_score += 30
                self.logger.debug(f"Low liquidity detected: ${liquidity_usd:,.2f}")
            elif liquidity_usd < self.config.min_liquidity_usd * 2:
                risk_score += 15
            
            # Check for liquidity drops (if historical data available)
            if 'liquidityHistory' in token_info:
                liquidity_history = token_info['liquidityHistory']
                if self._detect_liquidity_drop(liquidity_history):
                    risk_score += 40
                    self.logger.debug("Liquidity drop detected")
            
            return risk_score
            
        except Exception as e:
            self.logger.error(f"Error analyzing liquidity: {e}")
            return 0.0
    
    def _analyze_trading_patterns(self, token_info: Dict) -> float:
        """Analyze trading patterns for suspicious activity"""
        risk_score = 0.0
        
        try:
            # Get trading volume
            volume_24h = token_info.get('volume', {}).get('h24', 0)
            market_cap = token_info.get('fdv', 0) or token_info.get('marketCap', 0)
            
            # Check volume to market cap ratio
            if market_cap > 0:
                volume_ratio = volume_24h / market_cap
                
                # Extremely high volume ratio can indicate manipulation
                if volume_ratio > 5.0:
                    risk_score += 25
                    self.logger.debug(f"Extremely high volume ratio: {volume_ratio:.2f}")
                elif volume_ratio > 2.0:
                    risk_score += 15
                
                # Very low volume can indicate lack of interest
                if volume_ratio < 0.01:
                    risk_score += 10
                    self.logger.debug(f"Very low volume ratio: {volume_ratio:.2f}")
            
            # Check for price manipulation patterns
            price_change_24h = token_info.get('priceChange', {}).get('h24', 0)
            if abs(price_change_24h) > 500:  # 500% change
                risk_score += 20
                self.logger.debug(f"Extreme price change: {price_change_24h}%")
            
            return risk_score
            
        except Exception as e:
            self.logger.error(f"Error analyzing trading patterns: {e}")
            return 0.0
    
    def _analyze_holder_distribution(self, token_info: Dict) -> float:
        """Analyze holder distribution for concentration risks"""
        risk_score = 0.0
        
        try:
            # Check if holder information is available
            if 'holders' in token_info:
                holder_count = token_info['holders']
                
                # Very few holders is a red flag
                if holder_count < 50:
                    risk_score += 30
                    self.logger.debug(f"Very few holders: {holder_count}")
                elif holder_count < 100:
                    risk_score += 15
                elif holder_count < 200:
                    risk_score += 5
            
            # Check for whale concentration (if data available)
            if 'topHolders' in token_info:
                top_holders = token_info['topHolders']
                if self._check_whale_concentration(top_holders):
                    risk_score += 25
                    self.logger.debug("High whale concentration detected")
            
            return risk_score
            
        except Exception as e:
            self.logger.error(f"Error analyzing holder distribution: {e}")
            return 0.0
    
    def _analyze_contract_age(self, token_info: Dict) -> float:
        """Analyze contract age for risk assessment"""
        risk_score = 0.0
        
        try:
            # Get contract creation time
            created_at = token_info.get('pairCreatedAt')
            if created_at:
                if isinstance(created_at, (int, float)):
                    creation_time = datetime.fromtimestamp(created_at / 1000)
                else:
                    creation_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                # Calculate age
                age = datetime.now() - creation_time
                
                # Very new contracts are riskier
                if age < timedelta(hours=1):
                    risk_score += 20
                    self.logger.debug(f"Very new contract: {age}")
                elif age < timedelta(hours=24):
                    risk_score += 10
                elif age < timedelta(days=7):
                    risk_score += 5
            
            return risk_score
            
        except Exception as e:
            self.logger.error(f"Error analyzing contract age: {e}")
            return 0.0
    
    def _detect_liquidity_drop(self, liquidity_history: List[Dict]) -> bool:
        """Detect sudden liquidity drops"""
        try:
            if len(liquidity_history) < 2:
                return False
            
            # Sort by timestamp
            sorted_history = sorted(liquidity_history, key=lambda x: x.get('timestamp', 0))
            
            # Check for sudden drops (>50% in short time)
            for i in range(1, len(sorted_history)):
                current = sorted_history[i].get('liquidity', 0)
                previous = sorted_history[i-1].get('liquidity', 0)
                
                if previous > 0 and current < previous * 0.5:
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error detecting liquidity drop: {e}")
            return False
    
    def _check_whale_concentration(self, top_holders: List[Dict]) -> bool:
        """Check for excessive whale concentration"""
        try:
            if not top_holders:
                return False
            
            # Calculate top holder percentages
            total_top_5_percentage = 0
            for i, holder in enumerate(top_holders[:5]):
                percentage = holder.get('percentage', 0)
                total_top_5_percentage += percentage
            
            # If top 5 holders own more than 70%, it's risky
            return total_top_5_percentage > 70
            
        except Exception as e:
            self.logger.error(f"Error checking whale concentration: {e}")
            return False
    
    def _combine_results(self, external_result: Dict, custom_result: Dict) -> Dict:
        """Combine external and custom analysis results"""
        combined = external_result.copy()
        
        # Add custom risk factors
        combined['risk_factors'] = custom_result.get('risk_factors', [])
        
        # Combine risk scores
        external_score = external_result.get('risk_score', 0)
        custom_score = custom_result.get('custom_risk_score', 0)
        combined['risk_score'] = min((external_score + custom_score) / 2, 100.0)
        
        # Update rug risk status
        if custom_result.get('is_rug_risk', False):
            combined['is_rug_risk'] = True
        
        return combined
    
    def _safe_default_result(self) -> Dict:
        """Return a safe default result when analysis fails"""
        return {
            'is_rug_risk': True,  # Default to risky when in doubt
            'is_honeypot': False,
            'tax_percentage': 0.0,
            'is_blacklisted': False,
            'liquidity_locked': False,
            'owner_renounced': False,
            'risk_score': 100.0,
            'risk_factors': ['Analysis failed - treating as high risk']
        }
