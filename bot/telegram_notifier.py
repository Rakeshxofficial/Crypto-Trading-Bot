"""
Telegram bot integration for sending trading alerts
"""

import logging
import asyncio
from typing import Dict, Optional
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler
from telegram.error import TelegramError
from utils.telegram_rate_limiter import TelegramRateLimiter, TokenTracker

class TelegramNotifier:
    """Handles Telegram notifications and bot interactions"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.bot = None
        self.application = None
        self.rate_limiter = TelegramRateLimiter(config.telegram_rate_limit_per_minute)
        self.token_tracker = TokenTracker(config.token_cooldown_minutes)
        
    async def start(self):
        """Start the Telegram bot"""
        try:
            # Initialize bot
            self.bot = Bot(token=self.config.telegram_bot_token)
            
            # Create application
            self.application = Application.builder().token(self.config.telegram_bot_token).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self._start_command))
            self.application.add_handler(CommandHandler("help", self._help_command))
            self.application.add_handler(CommandHandler("status", self._status_command))
            self.application.add_handler(CallbackQueryHandler(self._button_callback))
            
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            
            # Start polling for updates
            await self.application.updater.start_polling()
            
            self.logger.info("Telegram bot started successfully and polling for commands")
            
            # Send startup message
            await self._send_startup_message()
            
        except Exception as e:
            self.logger.error(f"Error starting Telegram bot: {e}")
            raise
    
    async def stop(self):
        """Stop the Telegram bot"""
        try:
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            self.logger.info("Telegram bot stopped")
        except Exception as e:
            self.logger.error(f"Error stopping Telegram bot: {e}")
    
    async def send_alert(self, alert_data: Dict):
        """Send trading alert to Telegram with rate limiting and retry logic"""
        try:
            # Extract token info
            chain = alert_data.get('chain', '')
            token_address = alert_data.get('token_address', '')
            token_name = alert_data.get('token_name', 'Unknown')
            
            # Check if token is allowed (not in cooldown)
            if not await self.token_tracker.is_token_allowed(chain, token_address):
                self.logger.info(f"Skipping {token_name} - still in cooldown period")
                return False
            
            # Apply rate limiting
            await self.rate_limiter.wait_if_needed()
            
            # Format alert message
            message = self._format_alert_message(alert_data)
            
            # Create inline keyboard
            keyboard = self._create_alert_keyboard(alert_data)
            
            # Send message with retry logic
            retry_count = 0
            last_error = None
            
            while retry_count < self.config.max_retry_attempts:
                try:
                    await self.bot.send_message(
                        chat_id=self.config.telegram_chat_id,
                        text=message,
                        parse_mode='HTML',
                        reply_markup=keyboard,
                        disable_web_page_preview=True
                    )
                    
                    # Mark token as sent
                    await self.token_tracker.mark_token_sent(chain, token_address)
                    
                    self.logger.info(f"Alert sent for {token_name}")
                    return True
                    
                except TelegramError as e:
                    last_error = e
                    retry_count += 1
                    
                    if retry_count < self.config.max_retry_attempts:
                        # Exponential backoff
                        wait_time = self.config.retry_delay_seconds * (2 ** (retry_count - 1))
                        self.logger.warning(
                            f"Telegram error (attempt {retry_count}): {e}. "
                            f"Retrying in {wait_time} seconds..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        self.logger.error(f"Failed to send alert after {retry_count} attempts: {e}")
                        raise
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error sending alert for {alert_data.get('token_name', 'Unknown')}: {e}")
            return False
    
    def _format_alert_message(self, alert_data: Dict) -> str:
        """Format the alert message for Telegram"""
        try:
            # Check if this is a status update message
            if 'message' in alert_data:
                return f"📢 <b>{alert_data['token_name']}</b>\n\n{alert_data['message']}"
            # Extract data and ensure proper types
            token_name = alert_data.get('token_name', 'Unknown')
            token_symbol = alert_data.get('token_symbol', 'Unknown')
            chain = alert_data.get('chain', 'Unknown').upper()
            price_usd = float(alert_data.get('price_usd', 0))
            volume_24h = float(alert_data.get('volume_24h', 0))
            liquidity_usd = float(alert_data.get('liquidity_usd', 0))
            market_cap = float(alert_data.get('market_cap', 0))
            risk_score = float(alert_data.get('risk_score', 0))
            tax_percentage = float(alert_data.get('tax_percentage', 0))
            token_age = alert_data.get('token_age', 'Unknown')
            
            # Risk level indicator
            risk_emoji = self._get_risk_emoji(risk_score)
            
            # Format message
            message = f"""
🚨 <b>CRYPTO TRADING ALERT</b> 🚨

📊 <b>{token_name} ({token_symbol})</b>
🔗 <b>Chain:</b> {chain}
⏰ <b>Token Age:</b> {token_age}
💰 <b>Price:</b> ${price_usd:.8f}
📈 <b>24h Volume:</b> ${volume_24h:,.0f}
💧 <b>Liquidity:</b> ${liquidity_usd:,.0f}
🏦 <b>Market Cap:</b> ${market_cap:,.0f}

{risk_emoji} <b>Risk Score:</b> {risk_score:.1f}/100
🏷️ <b>Tax:</b> {tax_percentage:.1f}%

⚠️ <b>Status:</b> {"🔴 HIGH RISK" if risk_score > 70 else "🟡 MEDIUM RISK" if risk_score > 40 else "🟢 LOW RISK"}
"""
            
            return message.strip()
            
        except Exception as e:
            self.logger.error(f"Error formatting alert message: {e}")
            return f"Error formatting alert for {alert_data.get('token_name', 'Unknown')}"
    
    def _get_risk_emoji(self, risk_score: float) -> str:
        """Get risk emoji based on risk score"""
        if risk_score > 70:
            return "🔴"
        elif risk_score > 40:
            return "🟡"
        else:
            return "🟢"
    
    def _create_alert_keyboard(self, alert_data: Dict) -> InlineKeyboardMarkup:
        """Create inline keyboard for alert"""
        try:
            keyboard = []
            
            # Get data for buttons
            chain = alert_data.get('chain', '').lower()
            token_address = alert_data.get('token_address', '')
            pair_address = alert_data.get('pair_address', '')
            chart_url = alert_data.get('chart_url', '')
            
            # Chain-specific buttons
            if chain == 'solana':
                if token_address:
                    raydium_url = f"https://raydium.io/swap?inputCurrency=sol&outputCurrency={token_address}"
                    keyboard.append([InlineKeyboardButton("🔄 Buy on Raydium", url=raydium_url)])
                
                if token_address:
                    dextools_url = f"https://www.dextools.io/app/solana/pair-explorer/{pair_address or token_address}"
                    keyboard.append([InlineKeyboardButton("📊 DexTools", url=dextools_url)])
            
            elif chain == 'bsc':
                if token_address:
                    pancake_url = f"https://pancakeswap.finance/swap?outputCurrency={token_address}"
                    keyboard.append([InlineKeyboardButton("🥞 Buy on PancakeSwap", url=pancake_url)])
                
                if token_address:
                    dextools_url = f"https://www.dextools.io/app/bnb/pair-explorer/{pair_address or token_address}"
                    keyboard.append([InlineKeyboardButton("📊 DexTools", url=dextools_url)])
            
            elif chain == 'ethereum':
                if token_address:
                    uniswap_url = f"https://app.uniswap.org/#/swap?outputCurrency={token_address}"
                    keyboard.append([InlineKeyboardButton("🦄 Buy on Uniswap", url=uniswap_url)])
                
                if token_address:
                    dextools_url = f"https://www.dextools.io/app/ether/pair-explorer/{pair_address or token_address}"
                    keyboard.append([InlineKeyboardButton("📊 DexTools", url=dextools_url)])
            
            # Chart button
            if chart_url:
                keyboard.append([InlineKeyboardButton("📈 View Chart", url=chart_url)])
            
            # Additional buttons
            if token_address:
                keyboard.append([
                    InlineKeyboardButton("📋 Copy Address", callback_data=f"copy_{token_address}"),
                    InlineKeyboardButton("❌ Dismiss", callback_data="dismiss")
                ])
            
            return InlineKeyboardMarkup(keyboard)
            
        except Exception as e:
            self.logger.error(f"Error creating alert keyboard: {e}")
            return InlineKeyboardMarkup([[]])
    
    async def _start_command(self, update, context):
        """Handle /start command"""
        try:
            message = """
🤖 <b>Crypto Trading Bot</b>

Welcome! This bot monitors multiple blockchains for trading opportunities and alerts you about potential gems.

<b>Features:</b>
• 🔍 Multi-chain monitoring (Solana, BSC, Ethereum)
• 🛡️ Rug pull detection
• 📊 Volume analysis
• ⚡ Real-time alerts

<b>Commands:</b>
/help - Show this help message
/status - Check bot status

The bot will automatically send you alerts when it finds promising tokens!
"""
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            self.logger.error(f"Error in start command: {e}")
    
    async def _help_command(self, update, context):
        """Handle /help command"""
        try:
            message = """
🆘 <b>Help - Crypto Trading Bot</b>

<b>What this bot does:</b>
• Monitors Solana, BSC, and Ethereum for new tokens
• Filters tokens by market cap (under $5M)
• Detects rug pulls and scams
• Filters fake volume
• Sends alerts with trading opportunities

<b>Alert Information:</b>
• 🟢 Low Risk (0-40): Generally safe
• 🟡 Medium Risk (40-70): Proceed with caution
• 🔴 High Risk (70+): High risk of rug pull

<b>Commands:</b>
/start - Start the bot
/help - Show this help
/status - Check bot status

<b>Alert Buttons:</b>
• Buy buttons lead to DEX swap pages
• DexTools shows detailed charts
• Copy Address copies token contract

⚠️ <b>Disclaimer:</b> This is not financial advice. Always do your own research before trading!
"""
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            self.logger.error(f"Error in help command: {e}")
    
    async def _status_command(self, update, context):
        """Handle /status command"""
        try:
            message = """
📊 <b>Bot Status</b>

🟢 <b>Status:</b> Online and monitoring
🔍 <b>Chains:</b> Solana, BSC, Ethereum
💰 <b>Max Market Cap:</b> $5,000,000
⏰ <b>Last Updated:</b> Just now

<b>Current Settings:</b>
• Min Token Age: 5 minutes
• Max Tax: 10%
• Min Liquidity: $3,000
• Min Volume: $250
• Min Transactions: 5

✅ Bot is running normally!
"""
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            self.logger.error(f"Error in status command: {e}")
    
    async def _button_callback(self, update, context):
        """Handle button callbacks"""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data.startswith('copy_'):
                token_address = query.data.replace('copy_', '')
                await query.edit_message_text(
                    text=f"📋 Token Address:\n<code>{token_address}</code>\n\n(Tap to copy)",
                    parse_mode='HTML'
                )
            
            elif query.data == 'dismiss':
                await query.edit_message_text("❌ Alert dismissed")
            
        except Exception as e:
            self.logger.error(f"Error in button callback: {e}")
    
    async def _send_startup_message(self):
        """Send startup message to notify bot is online"""
        try:
            message = """
🚀 <b>Crypto Trading Bot Started!</b>

✅ Bot is now online and monitoring
🔍 Scanning Solana, BSC, and Ethereum
📊 Looking for tokens under $5M market cap

I'll send you alerts when I find promising trading opportunities!
"""
            await self.bot.send_message(
                chat_id=self.config.telegram_chat_id,
                text=message,
                parse_mode='HTML'
            )
            
        except Exception as e:
            self.logger.error(f"Error sending startup message: {e}")
    
    async def send_error_alert(self, error_message: str):
        """Send error alert to admin"""
        try:
            # Apply rate limiting for error alerts too
            await self.rate_limiter.wait_if_needed()
            message = f"""
🚨 <b>Bot Error Alert</b>

❌ <b>Error:</b> {error_message}
🕒 <b>Time:</b> {asyncio.get_event_loop().time()}

Please check the bot logs for more details.
"""
            await self.bot.send_message(
                chat_id=self.config.telegram_chat_id,
                text=message,
                parse_mode='HTML'
            )
            
        except Exception as e:
            self.logger.error(f"Error sending error alert: {e}")
            
    async def send_api_error(self, api_name: str, error_details: str):
        """Send API error notification"""
        try:
            message = f"""
⚠️ <b>API ERROR DETECTED</b> ⚠️

<b>API:</b> {api_name}
<b>Error:</b> {error_details}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The bot is unable to fetch token data. Please check:
- API availability
- Rate limits
- Network connectivity
"""
            await self.bot.send_message(
                chat_id=self.config.telegram_chat_id,
                text=message.strip(),
                parse_mode='HTML'
            )
        except Exception as e:
            self.logger.error(f"Error sending API error alert: {e}")
