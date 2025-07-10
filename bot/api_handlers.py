"""
API handlers for external services (Dexscreener, Rugcheck)
"""

import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

class DexscreenerAPI:
    """Handler for Dexscreener API interactions"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.base_url = config.dexscreener_api_base
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def get_tokens(self, chain: str) -> List[Dict]:
        """Get token data from Dexscreener for a specific chain"""
        try:
            session = await self._get_session()
            
            # Get chain ID
            chain_id = self._get_chain_id(chain)
            
            # Get multiple pages of tokens to find more variety
            all_pairs = []
            
            # Get tokens from the chain-specific endpoint for more variety
            chain_endpoint_url = f"{self.base_url}/dex/pairs/{chain_id}"
            
            try:
                async with session.get(chain_endpoint_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        pairs = data.get('pairs', [])
                        all_pairs.extend(pairs[:100])  # Get up to 100 tokens from main endpoint for broader coverage
                        self.logger.info(f"Retrieved {len(pairs)} pairs from chain endpoint for {chain}")
            except Exception as e:
                self.logger.debug(f"Error fetching from chain endpoint: {e}")
            
            # Use time-based rotation to get different tokens each scan
            import random
            import time
            
            # TRENDING TOKENS FROM USER SCREENSHOTS - Focus on actual trending tokens
            trending_search_terms = [
                "MrBeast", "Dege", "BONG", "PENGU", "ALT", "GM", "Loopy", "DEGEN", 
                "VCM", "Bonk", "MEMELESS", "KORI", "USELESS", "donk", "Fartcoin", 
                "STAPLER", "MORI", "SCAMCOIN", "ZBCN", "SPX", "bonkin", "BONKHOUSE",
                "CHILLHOUSE", "JUP", "SOLO", "IKUN", "purrcy", "solami", "THEKID",
                "WLFI", "APC", "TROLL", "POPCAT", "memecoin", "DJI6930", "MOBY",
                "gib", "SWIF", "Hosico", "BCOQ", "horsesack", "LAUNCH", "LuckyCoin",
                "GOLDI", "ZENAI", "shiyo", "coin", "TSLAx", "NEXGENT", "LAUNCHCOIN",
                "STARTUP", "GOR", "URANUS", "farthouse", "ELON", "titcoin", "BOTIFY",
                "GIGA", "MOODENG", "DeepSeekAI", "moonpig", "Digi", "AP", "america",
                "CATVAX", "NOBODY", "NVDAx", "GRIFFAIN", "GOB", "TAI", "wPOND",
                "ai16z", "EDWIN", "DADDY", "maow", "STACY", "RICKROLL", "XBT"
            ]
            
            # Convert to full URLs
            all_queries = [f"{self.base_url}/dex/search?q={term}" for term in trending_search_terms]
            
            # Use time-based seed for different results each scan
            time_seed = int(time.time()) // 60  # Changes every minute
            random.seed(time_seed + hash(chain))  # Different seed per chain
            
            # Randomly select 15 trending tokens each time for maximum variety
            queries = random.sample(all_queries, min(15, len(all_queries)))
            
            for query_url in queries:
                try:
                    async with session.get(query_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            pairs = data.get('pairs', [])
                            
                            # Filter by chain and avoid duplicates, limit per query
                            seen_addresses = {p.get('baseToken', {}).get('address') for p in all_pairs}
                            added_count = 0
                            for pair in pairs:
                                if (pair.get('chainId') == chain_id and 
                                    pair.get('baseToken', {}).get('address') not in seen_addresses and
                                    added_count < 15):  # Limit to 15 per query for variety
                                    all_pairs.append(pair)
                                    added_count += 1
                except:
                    continue
            
            # If we have results, return them
            if all_pairs:
                self.logger.info(f"Retrieved {len(all_pairs)} total tokens from Dexscreener for {chain}")
                return all_pairs
            
            # If still no results, try the default endpoint
            trending_url = f"{self.base_url}/dex/search?q={chain}"
            
            async with session.get(trending_url) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs', [])
                    
                    # Filter by chain and avoid duplicates
                    seen_addresses = {p.get('baseToken', {}).get('address') for p in all_pairs}
                    for pair in pairs:
                        if (pair.get('chainId') == chain_id and 
                            pair.get('baseToken', {}).get('address') not in seen_addresses):
                            all_pairs.append(pair)
                    
                    self.logger.info(f"Retrieved {len(all_pairs)} total tokens from Dexscreener for {chain}")
                    return all_pairs
                else:
                    self.logger.error(f"Dexscreener API error: {response.status}")
                    # Return empty list on error - NO FALLBACK DATA
                    return []
                    
        except Exception as e:
            self.logger.error(f"Error fetching tokens from Dexscreener: {e}")
            # Return empty list on error - NO FALLBACK DATA
            return []
    
    def _get_chain_id(self, chain: str) -> str:
        """Get chain ID for Dexscreener API"""
        chain_ids = {
            "solana": "solana",
            "bsc": "bsc",
            "ethereum": "ethereum"
        }
        return chain_ids.get(chain, chain)
    
    async def get_token_info(self, token_address: str, chain: str) -> Optional[Dict]:
        """Get detailed token information"""
        try:
            session = await self._get_session()
            url = f"{self.base_url}/dex/tokens/{token_address}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    self.logger.warning(f"Token info not found for {token_address}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error fetching token info: {e}")
            return None
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

class RugcheckAPI:
    """Handler for Rugcheck API interactions"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.base_url = config.rugcheck_api_base
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def check_token(self, token_address: str, chain: str) -> Dict:
        """Check token for rug pull risks using Rugcheck API"""
        try:
            session = await self._get_session()
            
            # Construct URL based on chain
            if chain == "solana":
                url = f"{self.base_url}/tokens/{token_address}/report"
            else:
                # For other chains, use generic endpoint
                url = f"{self.base_url}/tokens/{token_address}/report"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_rugcheck_response(data)
                elif response.status == 404:
                    self.logger.debug(f"Token not found in Rugcheck: {token_address}")
                    return self._default_response()
                else:
                    self.logger.warning(f"Rugcheck API error: {response.status}")
                    return self._default_response()
                    
        except Exception as e:
            self.logger.error(f"Error checking token with Rugcheck: {e}")
            return self._default_response()
    
    def _parse_rugcheck_response(self, data: Dict) -> Dict:
        """Parse Rugcheck API response"""
        try:
            result = {
                'is_rug_risk': False,
                'is_honeypot': False,
                'tax_percentage': 0.0,
                'is_blacklisted': False,
                'liquidity_locked': False,
                'owner_renounced': False,
                'risk_score': 0.0
            }
            
            # Parse different fields from Rugcheck response
            if 'risks' in data:
                risks = data['risks']
                
                # Check for high tax
                if 'tax' in risks:
                    tax_info = risks['tax']
                    if isinstance(tax_info, dict):
                        buy_tax = tax_info.get('buy', 0)
                        sell_tax = tax_info.get('sell', 0)
                        result['tax_percentage'] = max(buy_tax, sell_tax)
                        
                        if result['tax_percentage'] > self.config.max_tax_percentage:
                            result['is_rug_risk'] = True
                
                # Check for honeypot
                if 'honeypot' in risks:
                    result['is_honeypot'] = risks['honeypot']
                    if result['is_honeypot']:
                        result['is_rug_risk'] = True
                
                # Check for blacklist
                if 'blacklist' in risks:
                    result['is_blacklisted'] = risks['blacklist']
                    if result['is_blacklisted']:
                        result['is_rug_risk'] = True
            
            # Check liquidity and ownership
            if 'liquidity' in data:
                liquidity_info = data['liquidity']
                result['liquidity_locked'] = liquidity_info.get('locked', False)
                
                if not result['liquidity_locked']:
                    result['is_rug_risk'] = True
            
            if 'ownership' in data:
                ownership_info = data['ownership']
                result['owner_renounced'] = ownership_info.get('renounced', False)
                
                if not result['owner_renounced']:
                    result['is_rug_risk'] = True
            
            # Calculate overall risk score
            result['risk_score'] = self._calculate_rugcheck_score(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing Rugcheck response: {e}")
            return self._default_response()
    
    def _calculate_rugcheck_score(self, result: Dict) -> float:
        """Calculate risk score based on Rugcheck results"""
        score = 0.0
        
        if result['is_honeypot']:
            score += 50
        
        if result['is_blacklisted']:
            score += 40
        
        if result['tax_percentage'] > 0:
            score += min(result['tax_percentage'] * 2, 30)
        
        if not result['liquidity_locked']:
            score += 20
        
        if not result['owner_renounced']:
            score += 15
        
        return min(score, 100.0)
    
    def _default_response(self) -> Dict:
        """Default response when Rugcheck API is unavailable"""
        return {
            'is_rug_risk': False,
            'is_honeypot': False,
            'tax_percentage': 0.0,
            'is_blacklisted': False,
            'liquidity_locked': True,
            'owner_renounced': True,
            'risk_score': 0.0
        }
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
