"""
Logging configuration and utilities
"""

import logging
import logging.handlers
import os
from datetime import datetime

def setup_logger(log_level="INFO", log_file="crypto_bot.log"):
    """Setup logging configuration"""
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", log_file)
    
    # Configure logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_log_path = os.path.join("logs", "errors.log")
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_path,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # Set specific loggers
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    
    logger.info("Logging system initialized")
    return logger

class BotLogger:
    """Custom logger for bot operations"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_token_scan(self, chain: str, token_count: int, duration: float):
        """Log token scan operation"""
        self.logger.info(f"Scanned {token_count} tokens on {chain} in {duration:.2f}s")
    
    def log_alert_sent(self, token_name: str, chain: str, risk_score: float):
        """Log alert sent"""
        self.logger.info(f"Alert sent: {token_name} on {chain} (Risk: {risk_score:.1f})")
    
    def log_rug_detected(self, token_name: str, chain: str, reason: str):
        """Log rug pull detection"""
        self.logger.warning(f"Rug detected: {token_name} on {chain} - {reason}")
    
    def log_fake_volume(self, token_name: str, chain: str, volume_ratio: float):
        """Log fake volume detection"""
        self.logger.warning(f"Fake volume: {token_name} on {chain} - Ratio: {volume_ratio:.2f}")
    
    def log_api_error(self, api_name: str, error: str):
        """Log API error"""
        self.logger.error(f"API Error ({api_name}): {error}")
    
    def log_rate_limit(self, api_name: str, wait_time: float):
        """Log rate limiting"""
        self.logger.debug(f"Rate limit applied for {api_name}: waiting {wait_time:.2f}s")
    
    def log_database_operation(self, operation: str, success: bool, error: str = None):
        """Log database operation"""
        if success:
            self.logger.debug(f"Database operation successful: {operation}")
        else:
            self.logger.error(f"Database operation failed: {operation} - {error}")
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = ""):
        """Log performance metric"""
        self.logger.info(f"Performance: {metric_name} = {value:.2f} {unit}")
    
    def log_configuration_loaded(self, config_source: str):
        """Log configuration loading"""
        self.logger.info(f"Configuration loaded from {config_source}")
    
    def log_startup_complete(self):
        """Log successful startup"""
        self.logger.info("Bot startup completed successfully")
    
    def log_shutdown_initiated(self):
        """Log shutdown initiation"""
        self.logger.info("Bot shutdown initiated")
    
    def log_critical_error(self, error: str, component: str = ""):
        """Log critical error"""
        component_str = f" in {component}" if component else ""
        self.logger.critical(f"Critical error{component_str}: {error}")
    
    def log_security_alert(self, alert: str):
        """Log security alert"""
        self.logger.warning(f"Security Alert: {alert}")
    
    def log_market_condition(self, condition: str, details: str = ""):
        """Log market condition"""
        details_str = f" - {details}" if details else ""
        self.logger.info(f"Market condition: {condition}{details_str}")
