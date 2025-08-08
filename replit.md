# Crypto Trading Bot

## Overview
This project is a comprehensive Python-based cryptocurrency trading bot designed to identify trading opportunities across multiple blockchains (Solana, BSC, Ethereum). Its primary purpose is to provide users with real-time alerts on potential high-quality tokens, featuring advanced rug pull detection, volume filtering, and an integrated web dashboard for monitoring. The bot aims to safeguard users from fraudulent schemes while highlighting promising assets, contributing to a safer and more efficient cryptocurrency trading environment.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Architecture
- **Asynchronous Python Backend**: Built with `asyncio` for concurrent processing of multiple blockchain data streams.
- **Database**: Primarily uses SQLite for development, with a production-ready PostgreSQL option for storing token checks, alerts, and historical data.
- **Web Dashboard**: Flask-based interface for real-time monitoring.
- **Telegram Integration**: For real-time alerts and user interactions.
- **API Integration Layer**: Handles external services like Dexscreener and Rugcheck APIs.

### Key Design Decisions
- **Modular Component Design**: Functionalities like rug detection, volume filtering, and notifications are separated into dedicated modules.
- **Configuration-Driven**: Centralized configuration management with environment variable support.
- **Rate Limiting**: Built-in rate limiting to respect API quotas.
- **Error Handling**: Comprehensive logging and graceful error handling.
- **Duplicate Prevention**: Multi-layered system using case-insensitive name matching, in-memory tracking, and database-level checks (address and name) to prevent duplicate alerts.
- **Risk Classification System**: A 5-tier risk assessment (Ultra Risk, Medium Risk, Mini Gem, Real Gem, Premium Gem) based on price returns and other metrics.
- **Inclusive Filtering**: Configurable filters for market cap, volume, liquidity, and token holders to allow a diverse flow of tokens while maintaining basic safety.
- **Alert Rate Guarantee**: A system to ensure a consistent flow of alerts (e.g., 5 tokens per minute) by queuing pending alerts.
- **Deployment**: Unified `app.py` for combined bot and dashboard operation, configured for production deployment with HTTP server listening on port 5000.

### Feature Specifications
- **Token Discovery**: Continuously scans supported chains via Dexscreener API, with randomized and targeted search queries for trending tokens.
- **Security Analysis**: Multi-layered rug pull detection using external APIs (Rugcheck) and custom analysis, including volume-to-market cap ratio for ultra-risk identification.
- **Volume Filtering**: Detects fake volume through ratio analysis, spike detection, and wash trading patterns.
- **Notification System**: Sends detailed alerts to Telegram, including token age, price changes (1h, 6h, 24h), status classification, and token address. Interactive buttons provide quick access to DEX platforms.
- **Data Persistence**: Stores all checks and alerts in the database for analytics and historical tracking.
- **Real-time Monitoring**: Web dashboard displays scanning results and statistics.

## External Dependencies

### APIs
- **Dexscreener API**: For fetching token and trading pair data across multiple chains.
- **Rugcheck API**: For external rug pull detection.
- **Telegram Bot API**: For message sending and interactive bot features.

### Python Libraries
- **aiohttp**: Asynchronous HTTP client for API calls.
- **aiosqlite**: Asynchronous SQLite database operations.
- **asyncpg**: Asynchronous PostgreSQL database operations.
- **python-telegram-bot**: Telegram bot framework.
- **Flask**: Web dashboard framework.
- **asyncio**: Core asynchronous functionality.