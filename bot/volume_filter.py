"""
Volume filtering to detect fake/manipulated volume
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class VolumeFilter:
    """Filter for detecting fake or manipulated volume"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def is_fake_volume(self, token: Dict) -> bool:
        """Check if token has fake or manipulated volume"""
        try:
            # Extract volume and market cap data
            volume_24h = token.get('volume', {}).get('h24', 0)
            market_cap = token.get('fdv', 0) or token.get('marketCap', 0)
            
            if not volume_24h or not market_cap:
                self.logger.debug("Missing volume or market cap data")
                return False
            
            # Check volume to market cap ratio
            if self._check_volume_ratio(volume_24h, market_cap):
                self.logger.info(f"Fake volume detected: Volume ratio too high")
                return True
            
            # Check for volume spikes
            if self._check_volume_spikes(token):
                self.logger.info(f"Fake volume detected: Volume spike pattern")
                return True
            
            # Check for wash trading patterns
            if self._check_wash_trading(token):
                self.logger.info(f"Fake volume detected: Wash trading pattern")
                return True
            
            # Check for bot trading patterns
            if self._check_bot_trading(token):
                self.logger.info(f"Fake volume detected: Bot trading pattern")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking fake volume: {e}")
            return False
    
    def _check_volume_ratio(self, volume_24h: float, market_cap: float) -> bool:
        """Check if volume to market cap ratio is suspicious"""
        try:
            ratio = volume_24h / market_cap
            
            # Extremely high ratio indicates potential manipulation
            if ratio > 10.0:
                self.logger.debug(f"Extremely high volume ratio: {ratio:.2f}")
                return True
            
            # Very high ratio for small cap tokens
            if market_cap < 100_000 and ratio > 5.0:
                self.logger.debug(f"High volume ratio for small cap: {ratio:.2f}")
                return True
            
            # Check against configured threshold
            if ratio > self.config.volume_to_mcap_ratio_threshold * 50:
                self.logger.debug(f"Volume ratio exceeds threshold: {ratio:.2f}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking volume ratio: {e}")
            return False
    
    def _check_volume_spikes(self, token: Dict) -> bool:
        """Check for suspicious volume spikes"""
        try:
            # Get volume data for different time periods
            volume_1h = token.get('volume', {}).get('h1', 0)
            volume_6h = token.get('volume', {}).get('h6', 0)
            volume_24h = token.get('volume', {}).get('h24', 0)
            
            # Check for sudden volume spikes
            if volume_1h > 0 and volume_6h > 0:
                # If 1h volume is more than 50% of 6h volume, it's suspicious
                if volume_1h > volume_6h * 0.5:
                    self.logger.debug(f"Suspicious 1h volume spike: {volume_1h} vs {volume_6h}")
                    return True
            
            if volume_6h > 0 and volume_24h > 0:
                # If 6h volume is more than 80% of 24h volume, it's suspicious
                if volume_6h > volume_24h * 0.8:
                    self.logger.debug(f"Suspicious 6h volume spike: {volume_6h} vs {volume_24h}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking volume spikes: {e}")
            return False
    
    def _check_wash_trading(self, token: Dict) -> bool:
        """Check for wash trading patterns"""
        try:
            # Get transaction count data
            txns_24h = token.get('txns', {}).get('h24', {})
            
            if not txns_24h:
                return False
            
            buys = txns_24h.get('buys', 0)
            sells = txns_24h.get('sells', 0)
            
            if buys == 0 or sells == 0:
                return False
            
            # Check for suspicious buy/sell ratios
            buy_sell_ratio = buys / sells
            
            # Extremely balanced buy/sell ratio can indicate wash trading
            if 0.95 <= buy_sell_ratio <= 1.05:
                # Check if volume is high with balanced trades
                volume_24h = token.get('volume', {}).get('h24', 0)
                if volume_24h > 100_000:  # High volume with perfect balance
                    self.logger.debug(f"Suspicious wash trading pattern: {buy_sell_ratio:.3f} ratio")
                    return True
            
            # Check for repetitive transaction patterns
            if self._check_repetitive_transactions(token):
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking wash trading: {e}")
            return False
    
    def _check_repetitive_transactions(self, token: Dict) -> bool:
        """Check for repetitive transaction patterns"""
        try:
            # This would require detailed transaction data
            # For now, we'll use proxy indicators
            
            txns_24h = token.get('txns', {}).get('h24', {})
            if not txns_24h:
                return False
            
            total_txns = txns_24h.get('buys', 0) + txns_24h.get('sells', 0)
            volume_24h = token.get('volume', {}).get('h24', 0)
            
            if total_txns == 0 or volume_24h == 0:
                return False
            
            # Calculate average transaction size
            avg_txn_size = volume_24h / total_txns
            
            # Check if all transactions are very similar in size
            # This is a simplified check - real implementation would need more data
            if avg_txn_size > 0:
                # If we have very high transaction count with consistent sizes
                if total_txns > 1000 and volume_24h / total_txns < 100:
                    self.logger.debug(f"Suspicious repetitive transactions: {total_txns} txns, avg size ${avg_txn_size:.2f}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking repetitive transactions: {e}")
            return False
    
    def _check_bot_trading(self, token: Dict) -> bool:
        """Check for bot trading patterns"""
        try:
            # Get transaction timing data if available
            txns_24h = token.get('txns', {}).get('h24', {})
            if not txns_24h:
                return False
            
            # Check for unusually high transaction frequency
            total_txns = txns_24h.get('buys', 0) + txns_24h.get('sells', 0)
            
            # More than 1 transaction per minute for 24 hours is suspicious
            if total_txns > 1440:  # 24 * 60 minutes
                self.logger.debug(f"Suspicious bot trading: {total_txns} transactions in 24h")
                return True
            
            # Check for perfect timing patterns (would need more detailed data)
            # For now, we'll use volume consistency as a proxy
            volume_1h = token.get('volume', {}).get('h1', 0)
            volume_24h = token.get('volume', {}).get('h24', 0)
            
            if volume_24h > 0 and volume_1h > 0:
                # If volume is too consistent (1h volume is exactly 1/24 of 24h)
                expected_1h_volume = volume_24h / 24
                if abs(volume_1h - expected_1h_volume) / expected_1h_volume < 0.1:
                    self.logger.debug(f"Suspicious consistent volume pattern")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking bot trading: {e}")
            return False
    
    def get_volume_metrics(self, token: Dict) -> Dict:
        """Get volume metrics for analysis"""
        try:
            volume_24h = token.get('volume', {}).get('h24', 0)
            market_cap = token.get('fdv', 0) or token.get('marketCap', 0)
            
            metrics = {
                'volume_24h': volume_24h,
                'market_cap': market_cap,
                'volume_to_mcap_ratio': volume_24h / market_cap if market_cap > 0 else 0,
                'is_fake_volume': self.is_fake_volume(token)
            }
            
            # Add transaction metrics
            txns_24h = token.get('txns', {}).get('h24', {})
            if txns_24h:
                metrics['total_transactions'] = txns_24h.get('buys', 0) + txns_24h.get('sells', 0)
                metrics['buy_sell_ratio'] = txns_24h.get('buys', 0) / max(txns_24h.get('sells', 1), 1)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting volume metrics: {e}")
            return {}
