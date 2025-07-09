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
    
    # Trading Parameters
    max_market_cap: float = 5_000_000  # $5M
    min_market_cap: float = 10_000  # $10K minimum market cap
    min_token_age_minutes: int = 5  # Tokens must be at least 5 minutes old
    max_tax_percentage: float = 10.0
    min_liquidity_usd: float = 5_000  # $5K minimum liquidity
    min_volume_24h: float = 500  # $500 minimum 24h volume
    min_unique_transactions: int = 10  # Minimum 10 unique buys in last hour
    volume_to_mcap_ratio_threshold: float = 0.1
    
    # Rate Limiting
    api_calls_per_minute: int = 60
    request_delay_seconds: float = 1.0
    
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
                self.volume_to_mcap_ratio_threshold = trading_section.getfloat("volume_to_mcap_ratio_threshold", self.volume_to_mcap_ratio_threshold)
            
            # Rate limiting section
            if "rate_limiting" in config_parser:
                rate_section = config_parser["rate_limiting"]
                self.api_calls_per_minute = rate_section.getint("api_calls_per_minute", self.api_calls_per_minute)
                self.request_delay_seconds = rate_section.getfloat("request_delay_seconds", self.request_delay_seconds)
    
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
