"""
Flask dashboard for monitoring the crypto trading bot
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
import logging

# Add parent directory to path to import bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.database import Database
from config import Config

app = Flask(__name__)
app.config['SECRET_KEY'] = 'crypto-bot-dashboard'

# Initialize configuration and database
config = Config()
database = Database(config)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
async def dashboard():
    """Main dashboard page"""
    try:
        # Get recent statistics
        stats = await get_dashboard_stats()
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template('dashboard.html', stats={}, error=str(e))

@app.route('/api/stats')
async def api_stats():
    """API endpoint for dashboard statistics"""
    try:
        stats = await get_dashboard_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tokens')
async def api_tokens():
    """API endpoint for recent tokens"""
    try:
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        tokens = await database.get_recent_tokens(hours, limit)
        return jsonify(tokens)
    except Exception as e:
        logger.error(f"Error getting tokens: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts')
async def api_alerts():
    """API endpoint for recent alerts"""
    try:
        hours = request.args.get('hours', 24, type=int)
        
        alerts_summary = await database.get_alerts_summary(hours)
        return jsonify(alerts_summary)
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/top-risks')
async def api_top_risks():
    """API endpoint for top risk tokens"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        top_risks = await database.get_top_risk_tokens(limit)
        return jsonify(top_risks)
    except Exception as e:
        logger.error(f"Error getting top risks: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/profitable')
async def api_profitable():
    """API endpoint for profitable alerts"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        profitable = await database.get_profitable_alerts(limit)
        return jsonify(profitable)
    except Exception as e:
        logger.error(f"Error getting profitable alerts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/<table>')
async def api_export(table):
    """API endpoint for exporting data"""
    try:
        hours = request.args.get('hours', 24, type=int)
        
        if table not in ['token_checks', 'alerts', 'bot_stats']:
            return jsonify({'error': 'Invalid table name'}), 400
        
        data = await database.export_data(table, hours)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        return jsonify({'error': str(e)}), 500

async def get_dashboard_stats():
    """Get comprehensive dashboard statistics"""
    try:
        # Get statistics for last 24 hours
        token_stats = await database.get_token_stats(24)
        alerts_summary = await database.get_alerts_summary(24)
        recent_tokens = await database.get_recent_tokens(24, 10)
        top_risks = await database.get_top_risk_tokens(5)
        profitable = await database.get_profitable_alerts(5)
        
        # Calculate additional metrics
        total_scanned = sum(token_stats.get('status_breakdown', {}).values())
        rug_detected = token_stats.get('status_breakdown', {}).get('rug_risk', 0)
        fake_volume = token_stats.get('status_breakdown', {}).get('fake_volume', 0)
        passed_checks = token_stats.get('status_breakdown', {}).get('passed', 0)
        
        # Calculate percentages
        rug_percentage = (rug_detected / total_scanned * 100) if total_scanned > 0 else 0
        fake_volume_percentage = (fake_volume / total_scanned * 100) if total_scanned > 0 else 0
        pass_percentage = (passed_checks / total_scanned * 100) if total_scanned > 0 else 0
        
        return {
            'summary': {
                'total_scanned': total_scanned,
                'rug_detected': rug_detected,
                'fake_volume': fake_volume,
                'passed_checks': passed_checks,
                'alerts_sent': alerts_summary.get('total_alerts', 0),
                'successful_alerts': alerts_summary.get('successful_alerts', 0),
                'rug_percentage': round(rug_percentage, 1),
                'fake_volume_percentage': round(fake_volume_percentage, 1),
                'pass_percentage': round(pass_percentage, 1),
                'average_risk_score': round(token_stats.get('average_risk_score', 0), 1)
            },
            'chain_breakdown': token_stats.get('chain_breakdown', {}),
            'status_breakdown': token_stats.get('status_breakdown', {}),
            'recent_tokens': recent_tokens,
            'top_risks': top_risks,
            'profitable_alerts': profitable,
            'alerts_by_chain': alerts_summary.get('chain_breakdown', {}),
            'last_updated': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {'error': str(e)}

# Custom async route decorator
def async_route(f):
    """Decorator to handle async routes in Flask"""
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(f(*args, **kwargs))
    
    wrapper.__name__ = f.__name__
    return wrapper

# Apply async decorator to routes
@app.route('/')
def dashboard_route():
    return asyncio.run(dashboard())

@app.route('/api/stats')
def api_stats_route():
    return asyncio.run(api_stats())

@app.route('/api/tokens')
def api_tokens_route():
    return asyncio.run(api_tokens())

@app.route('/api/alerts')
def api_alerts_route():
    return asyncio.run(api_alerts())

@app.route('/api/top-risks')
def api_top_risks_route():
    return asyncio.run(api_top_risks())

@app.route('/api/profitable')
def api_profitable_route():
    return asyncio.run(api_profitable())

@app.route('/api/export/<table>')
def api_export_route(table):
    return asyncio.run(api_export(table))

if __name__ == '__main__':
    # Initialize database
    loop = asyncio.get_event_loop()
    loop.run_until_complete(database.initialize())
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
