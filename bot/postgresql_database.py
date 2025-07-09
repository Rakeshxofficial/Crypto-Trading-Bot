"""
PostgreSQL database operations for the crypto trading bot
"""

import asyncio
import asyncpg
import os
from datetime import datetime
from typing import Dict, List, Optional
from utils.logger import BotLogger

class PostgreSQLDatabase:
    """PostgreSQL database handler for crypto bot data"""
    
    def __init__(self, config):
        self.config = config
        self.logger = BotLogger(__name__)
        # Ensure logger has proper methods
        if not hasattr(self.logger, 'error'):
            import logging
            self.logger = logging.getLogger(__name__)
        self.pool = None
        self.database_url = os.getenv('DATABASE_URL')
        
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not found")
    
    async def initialize(self):
        """Initialize database connection pool and tables"""
        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=30
            )
            
            # Create tables
            await self._create_tables()
            
            self.logger.info("PostgreSQL database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize PostgreSQL database: {e}")
            raise
    
    async def _create_tables(self):
        """Create database tables"""
        async with self.pool.acquire() as conn:
            # Token checks table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS token_checks (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    chain TEXT NOT NULL,
                    token_address TEXT NOT NULL,
                    token_name TEXT,
                    token_symbol TEXT,
                    price_usd DECIMAL(20, 10),
                    volume_24h DECIMAL(20, 2),
                    liquidity_usd DECIMAL(20, 2),
                    market_cap DECIMAL(20, 2),
                    status TEXT NOT NULL,
                    risk_score DECIMAL(5, 2),
                    tax_percentage DECIMAL(5, 2),
                    is_honeypot BOOLEAN DEFAULT FALSE,
                    alert_sent BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Alerts table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    token_address TEXT NOT NULL,
                    token_name TEXT,
                    token_symbol TEXT,
                    chain TEXT NOT NULL,
                    price_usd DECIMAL(20, 10),
                    volume_24h DECIMAL(20, 2),
                    liquidity_usd DECIMAL(20, 2),
                    market_cap DECIMAL(20, 2),
                    risk_score DECIMAL(5, 2),
                    alert_type TEXT DEFAULT 'trading_opportunity',
                    message TEXT,
                    sent_successfully BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Bot stats table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    chain TEXT NOT NULL,
                    tokens_scanned INTEGER DEFAULT 0,
                    alerts_sent INTEGER DEFAULT 0,
                    errors_count INTEGER DEFAULT 0,
                    scan_duration DECIMAL(10, 3)
                )
            """)
            
            # Create indexes for better performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_token_checks_timestamp ON token_checks(timestamp)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_token_checks_chain ON token_checks(chain)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_chain ON alerts(chain)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_bot_stats_timestamp ON bot_stats(timestamp)")
    
    async def log_token_check(self, token_data: Dict):
        """Log token check to database"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO token_checks (
                        chain, token_address, token_name, token_symbol, price_usd,
                        volume_24h, liquidity_usd, market_cap, status, risk_score,
                        tax_percentage, is_honeypot, alert_sent
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """, 
                    token_data.get('chain', ''),
                    token_data.get('token_address', ''),
                    token_data.get('token_name', ''),
                    token_data.get('token_symbol', ''),
                    float(token_data.get('price_usd', 0)),
                    float(token_data.get('volume_24h', 0)),
                    float(token_data.get('liquidity_usd', 0)),
                    float(token_data.get('market_cap', 0)),
                    token_data.get('status', ''),
                    float(token_data.get('risk_score', 0)),
                    float(token_data.get('tax_percentage', 0)),
                    token_data.get('is_honeypot', False),
                    token_data.get('alert_sent', False)
                )
                
        except Exception as e:
            self.logger.error(f"Error logging token check: {e}")
    
    async def log_alert(self, alert_data: Dict):
        """Log sent alert to database"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO alerts (
                        token_address, token_name, token_symbol, chain, price_usd,
                        volume_24h, liquidity_usd, market_cap, risk_score, alert_type,
                        message, sent_successfully
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    alert_data.get('token_address', ''),
                    alert_data.get('token_name', ''),
                    alert_data.get('token_symbol', ''),
                    alert_data.get('chain', ''),
                    float(alert_data.get('price_usd', 0)),
                    float(alert_data.get('volume_24h', 0)),
                    float(alert_data.get('liquidity_usd', 0)),
                    float(alert_data.get('market_cap', 0)),
                    float(alert_data.get('risk_score', 0)),
                    alert_data.get('alert_type', 'trading_opportunity'),
                    alert_data.get('message', ''),
                    alert_data.get('sent_successfully', True)
                )
                
                self.logger.info(f"Logged alert for {alert_data.get('token_name', 'Unknown')} on {alert_data.get('chain', 'Unknown')}")
                
        except Exception as e:
            self.logger.error(f"Error logging alert: {e}")
    
    async def log_bot_stats(self, stats_data: Dict):
        """Log bot statistics"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO bot_stats (
                        chain, tokens_scanned, alerts_sent, errors_count, scan_duration
                    ) VALUES ($1, $2, $3, $4, $5)
                """,
                    stats_data.get('chain', ''),
                    stats_data.get('tokens_scanned', 0),
                    stats_data.get('alerts_sent', 0),
                    stats_data.get('errors_count', 0),
                    float(stats_data.get('scan_duration', 0))
                )
                
        except Exception as e:
            self.logger.error(f"Error logging bot stats: {e}")
    
    async def get_recent_tokens(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """Get recent token checks"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM token_checks 
                    WHERE timestamp > NOW() - INTERVAL '%s hours'
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """ % (hours, limit))
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Error getting recent tokens: {e}")
            return []
    
    async def get_alerts_summary(self, hours: int = 24) -> Dict:
        """Get summary of alerts sent"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_alerts,
                        COUNT(DISTINCT chain) as chains_active,
                        AVG(risk_score) as avg_risk_score,
                        MIN(timestamp) as first_alert,
                        MAX(timestamp) as last_alert
                    FROM alerts 
                    WHERE timestamp > NOW() - INTERVAL '%s hours'
                """ % hours)
                
                return dict(result) if result else {}
                
        except Exception as e:
            self.logger.error(f"Error getting alerts summary: {e}")
            return {}
    
    async def get_token_stats(self, hours: int = 24) -> Dict:
        """Get token scanning statistics"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_scanned,
                        COUNT(CASE WHEN status = 'passed' THEN 1 END) as passed_checks,
                        COUNT(CASE WHEN status = 'rug_risk' THEN 1 END) as rug_risks,
                        COUNT(CASE WHEN status = 'fake_volume' THEN 1 END) as fake_volume,
                        COUNT(CASE WHEN alert_sent = true THEN 1 END) as alerts_sent,
                        COUNT(DISTINCT chain) as chains_scanned
                    FROM token_checks 
                    WHERE timestamp > NOW() - INTERVAL '%s hours'
                """ % hours)
                
                return dict(result) if result else {}
                
        except Exception as e:
            self.logger.error(f"Error getting token stats: {e}")
            return {}
    
    async def get_top_risk_tokens(self, limit: int = 10) -> List[Dict]:
        """Get tokens with highest risk scores"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT token_name, token_symbol, chain, risk_score, timestamp
                    FROM token_checks 
                    WHERE risk_score > 0 
                    ORDER BY risk_score DESC 
                    LIMIT %s
                """ % limit)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Error getting top risk tokens: {e}")
            return []
    
    async def get_profitable_alerts(self, limit: int = 10) -> List[Dict]:
        """Get tokens that passed all checks (potentially profitable)"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM alerts 
                    WHERE risk_score < 40 AND sent_successfully = true
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """ % limit)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Error getting profitable alerts: {e}")
            return []
    
    async def export_data(self, table_name: str, hours: int = 24) -> List[Dict]:
        """Export data from a specific table"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM %s 
                    WHERE timestamp > NOW() - INTERVAL '%s hours'
                    ORDER BY timestamp DESC
                """ % (table_name, hours))
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Error exporting data from {table_name}: {e}")
            return []
    
    async def check_recent_alert(self, token_address: str, chain: str, minutes: int = 30) -> Optional[int]:
        """Check if alert was sent for this token recently"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT EXTRACT(EPOCH FROM (NOW() - timestamp))/60 as minutes_ago
                    FROM alerts 
                    WHERE token_address = $1 AND chain = $2 
                    AND timestamp > NOW() - INTERVAL '{} minutes'
                    ORDER BY timestamp DESC
                    LIMIT 1
                """.format(minutes), token_address, chain)
                
                if result:
                    return int(result['minutes_ago'])
                return None
                
        except Exception as e:
            self.logger.log_database_operation("check_recent_alert", False, str(e))
            return None
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.logger.info("PostgreSQL connection pool closed")