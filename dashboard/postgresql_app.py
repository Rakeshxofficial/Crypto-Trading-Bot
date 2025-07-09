"""
PostgreSQL Flask dashboard for monitoring the crypto trading bot
"""

import asyncio
import asyncpg
import os
from flask import Flask, render_template, jsonify
from datetime import datetime

app = Flask(__name__)

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')

async def get_db_connection():
    """Get database connection"""
    return await asyncpg.connect(DATABASE_URL)

async def get_dashboard_stats():
    """Get dashboard statistics using PostgreSQL"""
    conn = await get_db_connection()
    
    try:
        # Get comprehensive stats
        result = await conn.fetchrow("""
            SELECT COUNT(*) as total_scanned,
                   COUNT(DISTINCT chain) as chains_monitored,
                   AVG(risk_score) as avg_risk_score,
                   MAX(timestamp) as last_scan_time,
                   COUNT(CASE WHEN status = 'rug_risk' THEN 1 END) as rug_detected,
                   COUNT(CASE WHEN status = 'fake_volume' THEN 1 END) as fake_volume,
                   COUNT(CASE WHEN status = 'passed' THEN 1 END) as passed_checks
            FROM token_checks 
            WHERE timestamp > NOW() - INTERVAL '24 hours'
        """)
        
        # Get alerts count
        alert_result = await conn.fetchrow("""
            SELECT COUNT(*) as total_alerts
            FROM alerts 
            WHERE timestamp > NOW() - INTERVAL '24 hours'
        """)
        
        # Get chain breakdown
        chain_results = await conn.fetch("""
            SELECT chain, COUNT(*) as count
            FROM token_checks 
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY chain
        """)
        
        # Get recent tokens
        token_results = await conn.fetch("""
            SELECT token_name, token_symbol, chain, risk_score, 
                   status, timestamp, market_cap, volume_24h
            FROM token_checks 
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            ORDER BY timestamp DESC 
            LIMIT 20
        """)
        
        # Build comprehensive response
        stats = {
            'summary': {
                'total_scanned': result['total_scanned'] or 0,
                'rug_detected': result['rug_detected'] or 0,
                'fake_volume': result['fake_volume'] or 0,
                'passed_checks': result['passed_checks'] or 0,
                'alerts_sent': alert_result['total_alerts'] or 0,
                'average_risk_score': float(result['avg_risk_score'] or 0)
            },
            'chain_breakdown': {row['chain']: row['count'] for row in chain_results},
            'recent_tokens': [{
                'token_name': row['token_name'],
                'token_symbol': row['token_symbol'],
                'chain': row['chain'],
                'risk_score': float(row['risk_score'] or 0),
                'status': row['status'],
                'timestamp': row['timestamp'].isoformat(),
                'market_cap': float(row['market_cap'] or 0),
                'volume_24h': float(row['volume_24h'] or 0)
            } for row in token_results],
            'last_updated': result['last_scan_time'].isoformat() if result['last_scan_time'] else None
        }
        
        return stats
        
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        return {
            'summary': {
                'total_scanned': 0,
                'rug_detected': 0,
                'fake_volume': 0,
                'passed_checks': 0,
                'alerts_sent': 0,
                'average_risk_score': 0.0
            },
            'chain_breakdown': {},
            'recent_tokens': [],
            'last_updated': None
        }
    finally:
        await conn.close()

@app.route('/')
def dashboard():
    """Main dashboard page"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stats = loop.run_until_complete(get_dashboard_stats())
    loop.close()
    
    return render_template('dashboard.html', stats=stats)

@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard statistics"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stats = loop.run_until_complete(get_dashboard_stats())
    loop.close()
    
    return jsonify(stats)

@app.route('/api/tokens')
def api_tokens():
    """API endpoint for recent tokens"""
    async def get_tokens():
        conn = await get_db_connection()
        try:
            rows = await conn.fetch("""
                SELECT token_name, token_symbol, chain, risk_score, 
                       status, timestamp, market_cap, volume_24h
                FROM token_checks 
                WHERE timestamp > NOW() - INTERVAL '24 hours'
                ORDER BY timestamp DESC 
                LIMIT 50
            """)
            
            tokens = []
            for row in rows:
                tokens.append({
                    'token_name': row['token_name'],
                    'token_symbol': row['token_symbol'],
                    'chain': row['chain'],
                    'risk_score': float(row['risk_score'] or 0),
                    'status': row['status'],
                    'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'market_cap': float(row['market_cap'] or 0),
                    'volume_24h': float(row['volume_24h'] or 0)
                })
            
            return tokens
            
        except Exception as e:
            print(f"Error getting tokens: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            await conn.close()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tokens = loop.run_until_complete(get_tokens())
    loop.close()
    
    return jsonify(tokens)

@app.route('/api/alerts')
def api_alerts():
    """API endpoint for recent alerts"""
    async def get_alerts():
        conn = await get_db_connection()
        try:
            rows = await conn.fetch("""
                SELECT token_name, token_symbol, chain, risk_score, 
                       timestamp, market_cap, volume_24h
                FROM alerts 
                WHERE timestamp > NOW() - INTERVAL '24 hours'
                ORDER BY timestamp DESC 
                LIMIT 50
            """)
            
            alerts = []
            for row in rows:
                alerts.append({
                    'token_name': row['token_name'],
                    'token_symbol': row['token_symbol'],
                    'chain': row['chain'],
                    'risk_score': float(row['risk_score'] or 0),
                    'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'market_cap': float(row['market_cap'] or 0),
                    'volume_24h': float(row['volume_24h'] or 0)
                })
            
            return alerts
            
        except Exception as e:
            print(f"Error getting alerts: {e}")
            return []
        finally:
            await conn.close()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    alerts = loop.run_until_complete(get_alerts())
    loop.close()
    
    return jsonify(alerts)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)