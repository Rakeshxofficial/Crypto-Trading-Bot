# Crypto Trading Bot

## Overview

This is a comprehensive Python-based cryptocurrency trading bot that monitors multiple blockchains (Solana, BSC, Ethereum) for trading opportunities. The bot features advanced rug pull detection, volume filtering, and real-time Telegram notifications with an integrated web dashboard for monitoring.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Architecture
- **Asynchronous Python Backend**: Built with asyncio for concurrent processing of multiple blockchain data streams
- **SQLite Database**: Lightweight database for storing token checks, alerts, and historical data
- **Web Dashboard**: Flask-based real-time monitoring interface
- **Telegram Integration**: Bot interface for real-time alerts and user interactions
- **API Integration Layer**: Handlers for external services (Dexscreener, Rugcheck APIs)

### Key Design Decisions
- **Modular Component Design**: Each major functionality (rug detection, volume filtering, notifications) is separated into dedicated modules
- **Configuration-Driven**: Centralized configuration management with environment variable support
- **Rate Limiting**: Built-in rate limiting to respect API quotas
- **Error Handling**: Comprehensive logging and graceful error handling throughout

## Key Components

### 1. Bot Core (`bot/crypto_bot.py`)
- Main orchestration class that coordinates all components
- Manages bot lifecycle and scanning workflows
- Handles token processing and filtering pipeline

### 2. API Handlers (`bot/api_handlers.py`)
- **DexscreenerAPI**: Interface for fetching token and trading pair data
- **RugcheckAPI**: Integration with external rug pull detection service
- Implements proper rate limiting and error handling

### 3. Security Analysis
- **Rug Detector** (`bot/rug_detector.py`): Multi-layered rug pull detection using external APIs and custom analysis
- **Volume Filter** (`bot/volume_filter.py`): Detects fake volume through ratio analysis, spike detection, and wash trading patterns

### 4. Notification System (`bot/telegram_notifier.py`)
- Telegram bot integration for real-time alerts
- Interactive buttons for quick access to DEX platforms
- Command handlers for bot status and help

### 5. Data Layer (`bot/database.py`)
- SQLite database with tables for token checks and alerts
- Async database operations using aiosqlite
- Data persistence for analytics and historical tracking

### 6. Web Dashboard (`dashboard/app.py`)
- Flask-based web interface for monitoring
- Real-time statistics and token scanning results
- Bootstrap-based responsive UI

## Data Flow

1. **Token Discovery**: Bot continuously scans supported chains via Dexscreener API
2. **Filtering Pipeline**: 
   - Market cap filtering (under $5M)
   - Volume analysis and fake volume detection
   - Minimum liquidity requirements
3. **Security Analysis**:
   - External rug pull check via Rugcheck API
   - Custom analysis for honeypots, tax rates, liquidity locks
4. **Risk Assessment**: Combines multiple factors into risk score
5. **Notification**: High-quality opportunities sent via Telegram
6. **Data Storage**: All checks and alerts stored in SQLite database
7. **Dashboard Updates**: Real-time display of scanning results and statistics

## External Dependencies

### APIs
- **Dexscreener API**: Token and trading pair data across multiple chains
- **Rugcheck API**: External rug pull detection service
- **Telegram Bot API**: Message sending and interactive bot features

### Python Libraries
- **aiohttp**: Async HTTP client for API calls
- **aiosqlite**: Async SQLite database operations
- **python-telegram-bot**: Telegram bot framework
- **Flask**: Web dashboard framework
- **asyncio**: Core async functionality

### Configuration Requirements
- Telegram Bot Token (from @BotFather)
- Telegram Chat ID for notifications
- API rate limiting parameters
- Blockchain and trading parameters (market cap limits, tax thresholds, etc.)

## Deployment Strategy

### Local Development
- Python 3.8+ environment
- SQLite database (file-based)
- Environment variables for sensitive configuration
- Logging to both console and rotating files

### Production Considerations
- Process management for continuous operation
- Log rotation and monitoring
- Database backup strategy
- API key security
- Rate limiting compliance
- Error alerting and monitoring

### Key Files
- `main.py`: Entry point with signal handling
- `config.py`: Configuration management
- `requirements.txt`: Python dependencies (implied but not present)
- `logs/`: Directory for log files
- `crypto_bot.db`: SQLite database file

The architecture supports horizontal scaling by adding more API endpoints, additional blockchain support, and enhanced analysis algorithms while maintaining the core modular design.