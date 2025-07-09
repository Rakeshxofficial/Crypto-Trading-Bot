"""
Database operations for logging and data storage
"""

import sqlite3
import aiosqlite
import logging
from typing import Dict, List, Optional
from datetime import datetime
import json

class Database:
    """Database handler for crypto bot data"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.db_path = config.database_path
        
    async def initialize(self):
        """Initialize database tables"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Create tokens table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS token_checks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME,
                        chain TEXT,
                        token_address TEXT,
                        token_name TEXT,
                        token_symbol TEXT,
                        price_usd REAL,
                        volume_24h REAL,
                        liquidity_usd REAL,
                        market_cap REAL,
                        status TEXT,
                        risk_score REAL,
                        tax_percentage REAL,
                        is_honeypot BOOLEAN,
                        alert_sent BOOLEAN DEFAULT 0
                    )
                ''')
                
                # Create alerts table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME,
                        token_address TEXT,
                        chain TEXT,
                        alert_type TEXT,
                        message TEXT,
                        risk_score REAL,
                        sent_successfully BOOLEAN
                    )
                ''')
                
                # Create bot_stats table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS bot_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME,
                        chain TEXT,
                        tokens_scanned INTEGER,
                        alerts_sent INTEGER,
                        errors_count INTEGER,
                        scan_duration REAL
                    )
                ''')
                
                # Create indices for better performance
                await db.execute('CREATE INDEX IF NOT EXISTS idx_token_address ON token_checks(token_address)')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON token_checks(timestamp)')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_chain ON token_checks(chain)')
                await db.execute('CREATE INDEX IF NOT EXISTS idx_status ON token_checks(status)')
                
                await db.commit()
                
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    async def log_token_check(self, token_data: Dict):
        """Log token check to database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO token_checks (
                        timestamp, chain, token_address, token_name, token_symbol,
                        price_usd, volume_24h, liquidity_usd, market_cap, status,
                        risk_score, tax_percentage, is_honeypot
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    token_data['timestamp'],
                    token_data['chain'],
                    token_data['token_address'],
                    token_data['token_name'],
                    token_data['token_symbol'],
                    token_data['price_usd'],
                    token_data['volume_24h'],
                    token_data['liquidity_usd'],
                    token_data['market_cap'],
                    token_data['status'],
                    token_data['risk_score'],
                    token_data['tax_percentage'],
                    token_data['is_honeypot']
                ))
                
                await db.commit()
                
        except Exception as e:
            self.logger.error(f"Error logging token check: {e}")
    
    async def log_alert(self, alert_data: Dict):
        """Log sent alert to database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO alerts (
                        timestamp, token_address, chain, alert_type, message,
                        risk_score, sent_successfully
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now(),
                    alert_data.get('token_address', ''),
                    alert_data.get('chain', ''),
                    alert_data.get('alert_type', 'trading'),
                    alert_data.get('message', ''),
                    alert_data.get('risk_score', 0),
                    alert_data.get('sent_successfully', False)
                ))
                
                await db.commit()
                
        except Exception as e:
            self.logger.error(f"Error logging alert: {e}")
    
    async def log_bot_stats(self, stats_data: Dict):
        """Log bot statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO bot_stats (
                        timestamp, chain, tokens_scanned, alerts_sent,
                        errors_count, scan_duration
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now(),
                    stats_data.get('chain', ''),
                    stats_data.get('tokens_scanned', 0),
                    stats_data.get('alerts_sent', 0),
                    stats_data.get('errors_count', 0),
                    stats_data.get('scan_duration', 0)
                ))
                
                await db.commit()
                
        except Exception as e:
            self.logger.error(f"Error logging bot stats: {e}")
    
    async def get_recent_tokens(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """Get recent token checks"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute('''
                    SELECT * FROM token_checks 
                    WHERE timestamp > datetime('now', '-{} hours')
                    ORDER BY timestamp DESC 
                    LIMIT ?
                '''.format(hours), (limit,))
                
                rows = await cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Error getting recent tokens: {e}")
            return []
    
    async def get_alerts_summary(self, hours: int = 24) -> Dict:
        """Get summary of alerts sent"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Count total alerts
                cursor = await db.execute('''
                    SELECT COUNT(*) as total_alerts,
                           SUM(CASE WHEN sent_successfully = 1 THEN 1 ELSE 0 END) as successful_alerts
                    FROM alerts 
                    WHERE timestamp > datetime('now', '-{} hours')
                '''.format(hours))
                
                row = await cursor.fetchone()
                
                # Count alerts by chain
                cursor = await db.execute('''
                    SELECT chain, COUNT(*) as count
                    FROM alerts 
                    WHERE timestamp > datetime('now', '-{} hours')
                    GROUP BY chain
                '''.format(hours))
                
                chain_counts = await cursor.fetchall()
                
                return {
                    'total_alerts': row[0] if row else 0,
                    'successful_alerts': row[1] if row else 0,
                    'chain_breakdown': {row[0]: row[1] for row in chain_counts}
                }
                
        except Exception as e:
            self.logger.error(f"Error getting alerts summary: {e}")
            return {}
    
    async def get_token_stats(self, hours: int = 24) -> Dict:
        """Get token scanning statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Count tokens by status
                cursor = await db.execute('''
                    SELECT status, COUNT(*) as count
                    FROM token_checks 
                    WHERE timestamp > datetime('now', '-{} hours')
                    GROUP BY status
                '''.format(hours))
                
                status_counts = await cursor.fetchall()
                
                # Count tokens by chain
                cursor = await db.execute('''
                    SELECT chain, COUNT(*) as count
                    FROM token_checks 
                    WHERE timestamp > datetime('now', '-{} hours')
                    GROUP BY chain
                '''.format(hours))
                
                chain_counts = await cursor.fetchall()
                
                # Average risk score
                cursor = await db.execute('''
                    SELECT AVG(risk_score) as avg_risk
                    FROM token_checks 
                    WHERE timestamp > datetime('now', '-{} hours')
                '''.format(hours))
                
                avg_risk = await cursor.fetchone()
                
                return {
                    'status_breakdown': {row[0]: row[1] for row in status_counts},
                    'chain_breakdown': {row[0]: row[1] for row in chain_counts},
                    'average_risk_score': avg_risk[0] if avg_risk and avg_risk[0] else 0
                }
                
        except Exception as e:
            self.logger.error(f"Error getting token stats: {e}")
            return {}
    
    async def get_top_risk_tokens(self, limit: int = 10) -> List[Dict]:
        """Get tokens with highest risk scores"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute('''
                    SELECT token_name, token_symbol, chain, risk_score, 
                           market_cap, volume_24h, timestamp
                    FROM token_checks 
                    WHERE status = 'rug_risk'
                    ORDER BY risk_score DESC, timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                rows = await cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Error getting top risk tokens: {e}")
            return []
    
    async def get_profitable_alerts(self, limit: int = 10) -> List[Dict]:
        """Get tokens that passed all checks (potentially profitable)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute('''
                    SELECT token_name, token_symbol, chain, risk_score, 
                           market_cap, volume_24h, liquidity_usd, timestamp
                    FROM token_checks 
                    WHERE status = 'passed'
                    ORDER BY risk_score ASC, market_cap ASC, timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                rows = await cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Error getting profitable alerts: {e}")
            return []
    
    async def export_data(self, table_name: str, hours: int = 24) -> List[Dict]:
        """Export data from a specific table"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute(f'''
                    SELECT * FROM {table_name} 
                    WHERE timestamp > datetime('now', '-{hours} hours')
                    ORDER BY timestamp DESC
                ''')
                
                rows = await cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Error exporting data from {table_name}: {e}")
            return []
    
    async def close(self):
        """Close database connection"""
        try:
            # aiosqlite doesn't need explicit closing for connection
            # as we use context managers
            self.logger.info("Database operations completed")
            
        except Exception as e:
            self.logger.error(f"Error closing database: {e}")
