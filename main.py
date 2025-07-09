#!/usr/bin/env python3
"""
Crypto Trading Bot Main Entry Point
Monitors multiple blockchains for trading opportunities with rug pull detection
"""

import asyncio
import logging
import signal
import sys
from bot.crypto_bot import CryptoTradingBot
from utils.logger import setup_logger
from config import Config

def signal_handler(signum, frame):
    """Handle graceful shutdown"""
    print("\nReceived interrupt signal. Shutting down gracefully...")
    sys.exit(0)

async def main():
    """Main entry point for the crypto trading bot"""
    # Setup logging
    logger = setup_logger()
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Load configuration
        config = Config()
        
        # Initialize and start the bot
        bot = CryptoTradingBot(config)
        logger.info("Starting Crypto Trading Bot...")
        
        # Start the bot
        await bot.start()
        
    except Exception as e:
        logger.error(f"Fatal error starting bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
