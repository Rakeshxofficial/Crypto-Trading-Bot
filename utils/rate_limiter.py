"""
Rate limiting utilities for API calls
"""

import asyncio
import time
import logging
from collections import defaultdict, deque
from typing import Dict, Optional

class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, calls_per_minute: int = 60, burst_limit: int = 10):
        self.calls_per_minute = calls_per_minute
        self.burst_limit = burst_limit
        self.logger = logging.getLogger(__name__)
        
        # Track call times for each API
        self.call_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=calls_per_minute))
        self.burst_calls: Dict[str, deque] = defaultdict(lambda: deque(maxlen=burst_limit))
        
        # Calculate delay between calls
        self.min_delay = 60.0 / calls_per_minute
        
    async def wait(self, api_name: str = "default"):
        """Wait if necessary to respect rate limits"""
        current_time = time.time()
        
        # Check burst limit (short-term)
        await self._check_burst_limit(api_name, current_time)
        
        # Check per-minute limit (long-term)
        await self._check_per_minute_limit(api_name, current_time)
        
        # Record this call
        self.call_times[api_name].append(current_time)
        self.burst_calls[api_name].append(current_time)
        
        self.logger.debug(f"API call allowed for {api_name}")
    
    async def _check_burst_limit(self, api_name: str, current_time: float):
        """Check and enforce burst limit"""
        burst_calls = self.burst_calls[api_name]
        
        # Remove old calls (older than 10 seconds)
        while burst_calls and current_time - burst_calls[0] > 10:
            burst_calls.popleft()
        
        # Check if we're at burst limit
        if len(burst_calls) >= self.burst_limit:
            # Calculate wait time
            oldest_call = burst_calls[0]
            wait_time = 10 - (current_time - oldest_call)
            
            if wait_time > 0:
                self.logger.debug(f"Burst limit reached for {api_name}, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
    
    async def _check_per_minute_limit(self, api_name: str, current_time: float):
        """Check and enforce per-minute limit"""
        call_times = self.call_times[api_name]
        
        # Remove old calls (older than 1 minute)
        while call_times and current_time - call_times[0] > 60:
            call_times.popleft()
        
        # Check if we're at per-minute limit
        if len(call_times) >= self.calls_per_minute:
            # Calculate wait time
            oldest_call = call_times[0]
            wait_time = 60 - (current_time - oldest_call)
            
            if wait_time > 0:
                self.logger.debug(f"Per-minute limit reached for {api_name}, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
    
    def get_stats(self, api_name: str = "default") -> Dict:
        """Get rate limiting statistics"""
        current_time = time.time()
        call_times = self.call_times[api_name]
        burst_calls = self.burst_calls[api_name]
        
        # Count recent calls
        recent_calls = sum(1 for call_time in call_times if current_time - call_time <= 60)
        recent_burst = sum(1 for call_time in burst_calls if current_time - call_time <= 10)
        
        return {
            'api_name': api_name,
            'calls_last_minute': recent_calls,
            'calls_per_minute_limit': self.calls_per_minute,
            'burst_calls_last_10s': recent_burst,
            'burst_limit': self.burst_limit,
            'utilization_percent': (recent_calls / self.calls_per_minute) * 100
        }

class APIRateLimiter:
    """Specialized rate limiter for different APIs"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Different rate limits for different APIs
        self.limiters = {
            'dexscreener': RateLimiter(calls_per_minute=100, burst_limit=20),
            'rugcheck': RateLimiter(calls_per_minute=60, burst_limit=15),
            'telegram': RateLimiter(calls_per_minute=30, burst_limit=5),
            'general': RateLimiter(calls_per_minute=60, burst_limit=10)
        }
    
    async def wait_for_api(self, api_name: str):
        """Wait for specific API rate limit"""
        limiter = self.limiters.get(api_name, self.limiters['general'])
        await limiter.wait(api_name)
    
    async def wait_for_dexscreener(self):
        """Wait for Dexscreener API rate limit"""
        await self.wait_for_api('dexscreener')
    
    async def wait_for_rugcheck(self):
        """Wait for Rugcheck API rate limit"""
        await self.wait_for_api('rugcheck')
    
    async def wait_for_telegram(self):
        """Wait for Telegram API rate limit"""
        await self.wait_for_api('telegram')
    
    def get_all_stats(self) -> Dict:
        """Get statistics for all APIs"""
        return {
            api_name: limiter.get_stats(api_name)
            for api_name, limiter in self.limiters.items()
        }

class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on API responses"""
    
    def __init__(self, initial_calls_per_minute: int = 60):
        self.calls_per_minute = initial_calls_per_minute
        self.logger = logging.getLogger(__name__)
        
        # Base rate limiter
        self.base_limiter = RateLimiter(initial_calls_per_minute)
        
        # Adaptive parameters
        self.consecutive_errors = 0
        self.consecutive_successes = 0
        self.last_adjustment_time = time.time()
        
        # Adjustment thresholds
        self.error_threshold = 3
        self.success_threshold = 10
        self.min_calls_per_minute = 10
        self.max_calls_per_minute = 200
    
    async def wait_with_response(self, api_name: str = "default"):
        """Wait and return a context manager for response handling"""
        await self.base_limiter.wait(api_name)
        return self.ResponseContext(self, api_name)
    
    def _increase_rate(self):
        """Increase rate limit due to successful calls"""
        if self.calls_per_minute < self.max_calls_per_minute:
            old_rate = self.calls_per_minute
            self.calls_per_minute = min(
                self.calls_per_minute + 10,
                self.max_calls_per_minute
            )
            self.base_limiter = RateLimiter(self.calls_per_minute)
            self.logger.info(f"Increased rate limit: {old_rate} -> {self.calls_per_minute} calls/min")
    
    def _decrease_rate(self):
        """Decrease rate limit due to errors"""
        if self.calls_per_minute > self.min_calls_per_minute:
            old_rate = self.calls_per_minute
            self.calls_per_minute = max(
                self.calls_per_minute - 20,
                self.min_calls_per_minute
            )
            self.base_limiter = RateLimiter(self.calls_per_minute)
            self.logger.warning(f"Decreased rate limit: {old_rate} -> {self.calls_per_minute} calls/min")
    
    def _handle_success(self):
        """Handle successful API call"""
        self.consecutive_errors = 0
        self.consecutive_successes += 1
        
        if self.consecutive_successes >= self.success_threshold:
            self._increase_rate()
            self.consecutive_successes = 0
    
    def _handle_error(self, error_type: str = "general"):
        """Handle API error"""
        self.consecutive_successes = 0
        self.consecutive_errors += 1
        
        if self.consecutive_errors >= self.error_threshold:
            self._decrease_rate()
            self.consecutive_errors = 0
        
        self.logger.warning(f"API error ({error_type}): {self.consecutive_errors} consecutive errors")
    
    class ResponseContext:
        """Context manager for handling API responses"""
        
        def __init__(self, limiter, api_name):
            self.limiter = limiter
            self.api_name = api_name
            self.start_time = time.time()
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                self.limiter._handle_success()
            else:
                self.limiter._handle_error(str(exc_type.__name__))
            return False
    
    def get_current_rate(self) -> int:
        """Get current rate limit"""
        return self.calls_per_minute
    
    def get_stats(self) -> Dict:
        """Get adaptive rate limiter statistics"""
        return {
            'current_calls_per_minute': self.calls_per_minute,
            'consecutive_errors': self.consecutive_errors,
            'consecutive_successes': self.consecutive_successes,
            'min_limit': self.min_calls_per_minute,
            'max_limit': self.max_calls_per_minute
        }
