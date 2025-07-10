"""
Telegram-specific rate limiter to prevent API spam
"""

import asyncio
import time
from collections import deque
from typing import Dict, Optional
import logging

class TelegramRateLimiter:
    """Rate limiter specifically for Telegram messages"""
    
    def __init__(self, max_messages_per_minute: int = 5):
        self.max_messages_per_minute = max_messages_per_minute
        self.message_timestamps = deque()
        self.logger = logging.getLogger(__name__)
        self._lock = asyncio.Lock()
        
    async def wait_if_needed(self):
        """Wait if we've hit the rate limit"""
        async with self._lock:
            current_time = time.time()
            
            # Remove timestamps older than 1 minute
            while self.message_timestamps and self.message_timestamps[0] < current_time - 60:
                self.message_timestamps.popleft()
            
            # Check if we've hit the rate limit
            if len(self.message_timestamps) >= self.max_messages_per_minute:
                # Calculate how long to wait
                oldest_timestamp = self.message_timestamps[0]
                wait_time = 60 - (current_time - oldest_timestamp) + 0.1  # Add small buffer
                
                if wait_time > 0:
                    self.logger.info(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                    await asyncio.sleep(wait_time)
                    
                    # Clean up old timestamps after waiting
                    current_time = time.time()
                    while self.message_timestamps and self.message_timestamps[0] < current_time - 60:
                        self.message_timestamps.popleft()
            
            # Record this message
            self.message_timestamps.append(current_time)
            
    def get_current_rate(self) -> int:
        """Get current message count in the last minute"""
        current_time = time.time()
        
        # Clean up old timestamps
        while self.message_timestamps and self.message_timestamps[0] < current_time - 60:
            self.message_timestamps.popleft()
            
        return len(self.message_timestamps)


class TokenTracker:
    """Track sent tokens to prevent duplicates"""
    
    def __init__(self, cooldown_minutes: int = 30):
        self.cooldown_minutes = cooldown_minutes
        self.sent_tokens: Dict[str, float] = {}  # token_key -> timestamp
        self.logger = logging.getLogger(__name__)
        self._lock = asyncio.Lock()
        
    async def is_token_allowed(self, chain: str, token_address: str) -> bool:
        """Check if token can be sent (not in cooldown)"""
        async with self._lock:
            token_key = f"{chain}:{token_address.lower()}"
            current_time = time.time()
            
            # Clean up expired entries
            expired_keys = [
                key for key, timestamp in self.sent_tokens.items()
                if current_time - timestamp > self.cooldown_minutes * 60
            ]
            for key in expired_keys:
                del self.sent_tokens[key]
            
            # Check if token is in cooldown
            if token_key in self.sent_tokens:
                time_since_sent = current_time - self.sent_tokens[token_key]
                remaining_cooldown = (self.cooldown_minutes * 60) - time_since_sent
                
                if remaining_cooldown > 0:
                    self.logger.debug(
                        f"Token {token_address} on {chain} in cooldown for "
                        f"{remaining_cooldown/60:.1f} more minutes"
                    )
                    return False
            
            return True
    
    async def mark_token_sent(self, chain: str, token_address: str):
        """Mark token as sent"""
        async with self._lock:
            token_key = f"{chain}:{token_address.lower()}"
            self.sent_tokens[token_key] = time.time()
            self.logger.debug(f"Marked token {token_address} on {chain} as sent")
    
    def get_active_cooldowns(self) -> int:
        """Get number of tokens currently in cooldown"""
        current_time = time.time()
        active_count = sum(
            1 for timestamp in self.sent_tokens.values()
            if current_time - timestamp < self.cooldown_minutes * 60
        )
        return active_count