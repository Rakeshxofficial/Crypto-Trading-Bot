# Crypto Trading Bot

A comprehensive Python-based cryptocurrency trading bot that monitors multiple blockchains for trading opportunities with advanced rug pull detection and Telegram alerts.

## Features

### 🔍 Multi-Chain Monitoring
- **Solana**: Real-time monitoring of Solana DEX pairs
- **BSC (Binance Smart Chain)**: Track BEP-20 tokens
- **Ethereum**: Monitor ERC-20 tokens and DeFi pairs
- **Market Cap Filtering**: Focus on tokens under $5M market cap

### 🛡️ Advanced Security
- **Rug Pull Detection**: Integration with rugcheck.xyz API
- **Custom Analysis**: Proprietary rug detection algorithms
- **Honeypot Detection**: Identify honeypot tokens
- **Tax Analysis**: Check for excessive buy/sell taxes
- **Liquidity Monitoring**: Track liquidity locks and concentration

### 📊 Volume Analysis
- **Fake Volume Detection**: Identify artificially inflated volume
- **Wash Trading Detection**: Spot suspicious trading patterns
- **Bot Trading Analysis**: Detect automated trading schemes
- **Volume-to-Market Cap Ratios**: Filter unrealistic trading volumes

### 📱 Telegram Integration
- **Real-time Alerts**: Instant notifications for trading opportunities
- **Interactive Buttons**: Quick access to DEX platforms and tools
- **Risk Scoring**: Clear risk assessment for each token
- **Chain-specific Actions**: Tailored buttons for each blockchain

### 📈 Dashboard & Analytics
- **Web Dashboard**: Real-time monitoring interface
- **Token Statistics**: Comprehensive scanning analytics
- **Alert History**: Track all sent notifications
- **Performance Metrics**: Monitor bot efficiency
- **Data Export**: Export data for analysis

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- SQLite3 (included with Python)

### Required API Keys
Before running the bot, you'll need:
1. **Telegram Bot Token**: Create a bot via [@BotFather](https://t.me/BotFather)
2. **Telegram Chat ID**: Your personal chat ID or group ID

### Setup Instructions

1. **Clone or download the project files**
2. **Install dependencies**:
   ```bash
   pip install aiohttp asyncio pandas sqlite3 configparser python-telegram-bot flask
   ```

3. **Configure environment variables**:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token_here"
   export TELEGRAM_CHAT_ID="your_chat_id_here"
   ```

4. **Copy and customize configuration**:
   ```bash
   cp config.ini.example config.ini
   # Edit config.ini with your preferred settings
   ```

5. **Run the bot**:
   ```bash
   python main.py
   ```

6. **Access the dashboard** (optional):
   ```bash
   python dashboard/app.py
   ```
   Then visit `http://localhost:5000` in your browser.

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | Yes |
| `TELEGRAM_CHAT_ID` | Your Telegram chat/group ID | Yes |

### Configuration File (config.ini)

The bot uses a configuration file for detailed settings. Key sections include:

#### Trading Parameters
```ini
[trading]
max_market_cap = 5000000          # Maximum market cap ($5M)
min_token_age_minutes = 1         # Minimum token age
max_tax_percentage = 10.0         # Maximum tax allowed
min_liquidity_usd = 10000         # Minimum liquidity required
