"""
Configuration management for the crypto trading bot
"""

import os
import configparser
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Config:
    """Configuration class for the crypto trading bot"""
    
    # API Configuration
    dexscreener_api_base: str = "https://api.dexscreener.com/latest"
    rugcheck_api_base: str = "https://api.rugcheck.xyz/v1"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    
    # Trading Parameters - Updated with comprehensive filters
    max_market_cap: float = 100_000_000_000  # $100B - virtually unlimited
    min_market_cap: float = 50_000  # $50K minimum market cap (much more inclusive)
    min_token_age_minutes: int = 0  # No minimum age - even 1 hour old is fine
    max_tax_percentage: float = 100.0  # Allow any tax percentage
    min_liquidity_usd: float = 1_000  # $1K minimum liquidity (more inclusive)
    min_volume_24h: float = 100  # $100 minimum 24h volume (more inclusive)
    min_unique_transactions: int = 0  # No minimum transactions
    volume_to_mcap_ratio_threshold: float = 100.0  # Allow any volume ratio
    min_token_holders: int = 100  # Minimum 100 token holders required
    
    # Price Return Thresholds for Status Classification
    min_return_1h: float = 1.0  # 1% minimum 1-hour return
    min_return_6h: float = 1.0  # 1% minimum 6-hour return
    min_return_24h: float = 5.0  # 5% minimum 24-hour return
    
    # Premium Gem Thresholds
    premium_gem_min_market_cap: float = 100_000_000  # $100M for premium gems
    premium_gem_min_volume: float = 1_000_000  # $1M volume for premium gems
    
    # Rate Limiting
    api_calls_per_minute: int = 60
    request_delay_seconds: float = 1.0
    
    # Telegram Alert Settings
    telegram_rate_limit_per_minute: int = 1000  # Unlimited alerts per minute
    token_cooldown_minutes: int = 24*60  # 24 hours cooldown - prevent any duplicates
    alerts_per_minute_target: int = 1000  # Send as many tokens as possible
    retry_on_error: bool = True  # Retry failed operations
    max_retry_attempts: int = 3  # Maximum retry attempts
    retry_delay_seconds: float = 2.0  # Initial retry delay (exponential backoff)
    
    # Supported Blockchains
    supported_chains: List[str] = None
    
    # Database
    database_path: str = "crypto_bot.db"
    use_postgresql: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "crypto_bot.log"
    
    # Dashboard
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 5000
    
    def __post_init__(self):
        """Initialize configuration from environment variables and config file"""
        if self.supported_chains is None:
            self.supported_chains = ["solana", "bsc", "ethereum"]
        
        # Load from environment variables
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        
        # Load from config file if it exists
        self._load_config_file()
        
        # Validate required configuration
        self._validate_config()
    
    def _load_config_file(self):
        """Load configuration from config.ini file"""
        config_parser = configparser.ConfigParser()
        
        if os.path.exists("config.ini"):
            config_parser.read("config.ini")
            
            # API section
            if "api" in config_parser:
                api_section = config_parser["api"]
                self.dexscreener_api_base = api_section.get("dexscreener_base", self.dexscreener_api_base)
                self.rugcheck_api_base = api_section.get("rugcheck_base", self.rugcheck_api_base)
            
            # Trading section
            if "trading" in config_parser:
                trading_section = config_parser["trading"]
                self.max_market_cap = trading_section.getfloat("max_market_cap", self.max_market_cap)
                self.min_token_age_minutes = trading_section.getint("min_token_age_minutes", self.min_token_age_minutes)
                self.max_tax_percentage = trading_section.getfloat("max_tax_percentage", self.max_tax_percentage)
                self.min_liquidity_usd = trading_section.getfloat("min_liquidity_usd", self.min_liquidity_usd)
                self.min_market_cap = trading_section.getfloat("min_market_cap", self.min_market_cap)
                self.volume_to_mcap_ratio_threshold = trading_section.getfloat("volume_to_mcap_ratio_threshold", self.volume_to_mcap_ratio_threshold)
                self.min_token_holders = trading_section.getint("min_token_holders", self.min_token_holders)
                self.min_return_1h = trading_section.getfloat("min_return_1h", self.min_return_1h)
                self.min_return_6h = trading_section.getfloat("min_return_6h", self.min_return_6h)
                self.min_return_24h = trading_section.getfloat("min_return_24h", self.min_return_24h)
                self.premium_gem_min_market_cap = trading_section.getfloat("premium_gem_min_market_cap", self.premium_gem_min_market_cap)
                self.premium_gem_min_volume = trading_section.getfloat("premium_gem_min_volume", self.premium_gem_min_volume)
            
            # Rate limiting section
            if "rate_limiting" in config_parser:
                rate_section = config_parser["rate_limiting"]
                self.api_calls_per_minute = rate_section.getint("api_calls_per_minute", self.api_calls_per_minute)
                self.request_delay_seconds = rate_section.getfloat("request_delay_seconds", self.request_delay_seconds)
            
            # Alerts section
            if "alerts" in config_parser:
                alerts_section = config_parser["alerts"]
                self.telegram_rate_limit_per_minute = alerts_section.getint("telegram_rate_limit_per_minute", self.telegram_rate_limit_per_minute)
                self.token_cooldown_minutes = alerts_section.getint("token_cooldown_minutes", self.token_cooldown_minutes)
                self.retry_on_error = alerts_section.getboolean("retry_on_error", self.retry_on_error)
                self.max_retry_attempts = alerts_section.getint("max_retry_attempts", self.max_retry_attempts)
                self.retry_delay_seconds = alerts_section.getfloat("retry_delay_seconds", self.retry_delay_seconds)
    
    def _validate_config(self):
        """Validate required configuration parameters"""
        if not self.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        if not self.telegram_chat_id:
            raise ValueError("TELEGRAM_CHAT_ID environment variable is required")
        
        if self.max_market_cap <= 0:
            raise ValueError("max_market_cap must be greater than 0")
        
        if self.min_token_age_minutes < 0:
            raise ValueError("min_token_age_minutes must be non-negative")
