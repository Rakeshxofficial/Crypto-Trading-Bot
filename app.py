#!/usr/bin/env python3
"""
Main application entry point for deployment
Runs both the crypto bot and dashboard together
"""

import asyncio
import threading
import time
import os
import logging
from flask import Flask
from dashboard.postgresql_app import app as dashboard_app
from config import Config
from bot.crypto_bot import CryptoTradingBot

# Configure logging
# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/crypto_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_bot():
    """Run the crypto bot in a separate thread"""
    try:
        logger.info("Starting crypto bot...")
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def bot_main():
            """Main bot function"""
            try:
                # Initialize configuration
                config = Config()
                
                # Create and start bot
                bot = CryptoTradingBot(config)
                await bot.start()
                
            except Exception as e:
                logger.error(f"Bot initialization error: {e}")
                raise
        
        # Run the bot
        loop.run_until_complete(bot_main())
        
    except Exception as e:
        logger.error(f"Bot thread error: {e}")

def run_dashboard():
    """Run the Flask dashboard"""
    try:
        logger.info("Starting dashboard on port 5000...")
        dashboard_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")

def main():
    """Main entry point"""
    logger.info("Starting Crypto Trading Bot with Dashboard...")
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Start bot in separate thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Give bot time to start
    time.sleep(3)
    
    # Start dashboard (this will block)
    run_dashboard()

if __name__ == "__main__":
    main()