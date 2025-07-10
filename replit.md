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

## Recent Changes (July 10, 2025)

### Comprehensive Risk Classification System with Inclusive Filtering (Latest Update)
1. **Implemented Inclusive Filters**: Added basic safety filters with comprehensive risk transparency
   - **Market Cap**: Minimum $50K (very inclusive, configurable via config.yaml)
   - **Volume**: Minimum $100 24h volume (very inclusive, configurable)
   - **Liquidity**: Minimum $1K liquidity (very inclusive, configurable)
   - **Token Holders**: Minimum 10 holders (very inclusive, configurable)
   - **Token Age**: Any age is fine (even 1 hour old tokens accepted)

2. **Added Status Classification System**: 5-tier risk assessment based on price returns
   - **⚠️ Ultra Risk – Not Recommended**: All returns (1h, 6h, 24h) are negative
   - **⚠️ Medium Risk**: 1h return ≥+1% but 6h & 24h not positive
   - **🟡 Mini Gem**: 1h ≥+1% and 6h ≥+1%, but 24h not positive
   - **🟢 Real Gem – Low Risk**: 1h, 6h, and 24h all meet positive thresholds
   - **💎 Premium Gem (Top Label)**: Same as Real Gem + Market Cap ≥$100M & Volume >$1M

3. **Enhanced Alert Messages**: Added comprehensive price change tracking
   - Shows 1hr, 6hr, and 24hr price changes with + or - indicators
   - Status classification displayed with appropriate emoji and label
   - Token holders count still displayed in all alerts
   - Token address shown as copyable text for easy access

4. **Updated Configuration**: New filter thresholds in config.yaml
   - Price return thresholds: 1hr (±1%), 6hr (±1%), 24hr (≥+5%)
   - Premium gem criteria: $100M market cap, $1M volume
   - All parameters configurable for easy adjustment

### Telegram Channel Configuration (Previous Update)
1. **Alert Destination Changed**: Successfully updated bot to send alerts to Telegram channel
   - Changed from individual user ID to channel ID: -1002767799900
   - All future crypto token alerts will be sent to "Rich Alert..." channel
   - Bot restarted and confirmed working with new channel configuration

### Token Discovery and Diagnostic System (Latest Fix)
1. **Resolved Token Flow Issue**: Fixed the problem where bot stopped sending alerts
   - Reduced cooldown from 5 → 3 minutes for faster token rotation
   - Implemented randomized search queries (16 different terms) for maximum variety
   - Added diagnostic messages when no tokens found to explain the situation
   - Successfully sending fresh tokens: PIKACHU INU, Department Of Governm, etc.

2. **Enhanced API Discovery**: Improved token discovery mechanisms
   - Random selection of 7 out of 16 search terms each scan for variety
   - Increased total token retrieval (101 Solana, 51 BSC tokens per scan)
   - Better rotation prevents getting stuck on same token sets

### Deployment Configuration (Latest)
1. **Production-Ready Application**: Created unified app.py for deployment
   - Combines bot and dashboard in single process
   - Proper threading for concurrent operation
   - HTTP server listening on port 5000 for Autoscale compatibility
   - Configured for background worker deployment

2. **Deployment Fixes**: Resolved all deployment errors
   - Fixed undefined $file variable issues
   - Ensured HTTP server runs for Autoscale requirements
   - Proper run command configuration
   - Both bot and dashboard operational simultaneously

### Alert System Improvements
1. **Duplicate Prevention**: Enhanced token tracking with configurable cooldown period
   - 30-minute cooldown for same token alerts (configurable)
   - Memory-based tracking in TelegramNotifier
   - Database-based duplicate checking

2. **Rate Limiting**: Implemented Telegram-compliant rate limiting
   - Maximum 5 alerts per minute (configurable)
   - Automatic waiting when limit reached
   - Prevents Telegram API bans

3. **Stability Enhancements**: Added retry logic and better error handling
   - Exponential backoff for failed sends
   - Up to 3 retry attempts
   - Continues operation after errors

4. **Configuration**: All settings now configurable via config.ini
   - `telegram_rate_limit_per_minute`: Control alert speed
   - `token_cooldown_minutes`: Duplicate prevention period
   - `retry_on_error`: Enable/disable retry logic
   - `max_retry_attempts`: Number of retries
   - `retry_delay_seconds`: Initial retry delay

### Alert Rate Guarantee System (Latest Update)
1. **Proactive Token Sending**: Bot now guarantees exactly 5 tokens per minute
   - Pending alerts queue system for tokens that fail initial filters
   - Automatic sending of queued tokens to meet 5 tokens/minute target
   - Minute-by-minute tracking and reset of alert counters
   - Priority-based alert sending (high priority tokens first)

2. **Enhanced Alert Information**: Added token age display in notifications
   - Shows token age directly in Telegram alerts (e.g., "2 hours", "15 minutes")
   - Helps users assess token freshness and trading opportunities
   - Displays human-readable format for better decision making

3. **Improved Duplicate Detection**: Enhanced system to prevent sending same tokens repeatedly
   - Dual-layer checking: by token address AND token name
   - Memory-based tracking in TelegramNotifier with token names
   - Database-based duplicate checking with name validation
   - Successfully sending diverse tokens: PIKACHU INU, Department Of Governm, Department of Gov Efficiency, No Cash Value, Dogecoin

4. **Relaxed Safety Filters**: Significantly more lenient to allow diverse token flow
   - Minimum liquidity: $1K → $100 (more inclusive)
   - Minimum volume: $100 → $50 (allows newer tokens)
   - Minimum transactions: 1 → 0 (allows brand new tokens)
   - Reduced token cooldown: 30 → 3 minutes (more frequent alerts)
   - Volume and transaction filters now advisory rather than blocking

5. **Enhanced Scanning Frequency**: Faster scanning to find more tokens
   - Reduced scan delay from 10 seconds to 3 seconds
   - More frequent checks to build pending alerts queue
   - Improved token discovery rate across all chains
   - Added randomized search queries (16 different terms) rotating for maximum variety
   - Diagnostic messages sent when no tokens found (explains why alerts stopped)

### Earlier Updates
1. **Removed All Fallback Data**: Bot now exclusively uses real Dexscreener API data
   - No hardcoded or fallback tokens
   - Returns empty data on API errors instead of synthetic tokens
   - Added API error notifications to Telegram

## Recent Changes (July 9, 2025)
1. **Enhanced Safety Filters**: Added comprehensive filters to prevent low-quality token alerts
   - Minimum $5,000 liquidity requirement
   - Minimum $10,000 market cap requirement
   - Minimum $500 volume and 10 unique transactions
   - Single buyer/seller detection
   - Buy/sell ratio checks

2. **Duplicate Alert Prevention**: Implemented 60-minute cooldown to prevent duplicate alerts
   - Checks database for recent alerts before sending
   - Prevents same token from being alerted multiple times
   - Clear logging of skipped duplicates

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

### 5. Data Layer 
- **PostgreSQL Database** (`bot/postgresql_database.py`): Production database with asyncpg connection pooling
- **SQLite Database** (`bot/database.py`): Legacy database option for local development
- Async database operations with connection pooling
- Data persistence for analytics and historical tracking
- Tables: token_checks, alerts, bot_stats

### 6. Web Dashboard 
- **PostgreSQL Dashboard** (`dashboard/postgresql_app.py`): Production dashboard with PostgreSQL integration
- **SQLite Dashboard** (`dashboard/simple_app.py`): Legacy dashboard for local development
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