"""
Simple Flask dashboard for monitoring the crypto trading bot
"""
from flask import Flask, render_template, jsonify
import sqlite3
import json
from datetime import datetime
import threading
import time
import os
import sys

# Add project root to path
sys.path.append('..')

app = Flask(__name__)

# Database configuration
DB_PATH = "../crypto_bot.db"

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_dashboard_stats():
    """Get dashboard statistics using synchronous database calls"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get recent token checks (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) as total_scanned,
                   SUM(CASE WHEN status = 'rug_risk' THEN 1 ELSE 0 END) as rug_detected,
                   SUM(CASE WHEN status = 'fake_volume' THEN 1 ELSE 0 END) as fake_volume,
                   SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed_checks,
                   AVG(risk_score) as avg_risk_score
            FROM token_checks 
            WHERE timestamp > datetime('now', '-24 hours')
        """)
        
        stats = cursor.fetchone()
        
        # Get alerts count
        cursor.execute("""
            SELECT COUNT(*) as total_alerts
            FROM alerts 
            WHERE timestamp > datetime('now', '-24 hours')
        """)
        
        alerts = cursor.fetchone()
        
        # Get chain breakdown
        cursor.execute("""
            SELECT chain, COUNT(*) as count
            FROM token_checks 
            WHERE timestamp > datetime('now', '-24 hours')
            GROUP BY chain
        """)
        
        chain_breakdown = {}
        for row in cursor.fetchall():
            chain_breakdown[row['chain']] = row['count']
        
        # Get recent tokens
        cursor.execute("""
            SELECT token_name, token_symbol, chain, market_cap, risk_score, status, timestamp
            FROM token_checks 
            WHERE timestamp > datetime('now', '-24 hours')
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        
        recent_tokens = []
        for row in cursor.fetchall():
            recent_tokens.append({
                'token_name': row['token_name'],
                'token_symbol': row['token_symbol'],
                'chain': row['chain'],
                'market_cap': row['market_cap'],
                'risk_score': row['risk_score'],
                'status': row['status'],
                'timestamp': row['timestamp']
            })
        
        conn.close()
        
        total_scanned = stats['total_scanned'] or 0
        rug_detected = stats['rug_detected'] or 0
        fake_volume = stats['fake_volume'] or 0
        passed_checks = stats['passed_checks'] or 0
        
        return {
            'summary': {
                'total_scanned': total_scanned,
                'rug_detected': rug_detected,
                'fake_volume': fake_volume,
                'passed_checks': passed_checks,
                'alerts_sent': alerts['total_alerts'] or 0,
                'rug_percentage': round((rug_detected / total_scanned * 100) if total_scanned > 0 else 0, 1),
                'fake_volume_percentage': round((fake_volume / total_scanned * 100) if total_scanned > 0 else 0, 1),
                'pass_percentage': round((passed_checks / total_scanned * 100) if total_scanned > 0 else 0, 1),
                'average_risk_score': round(stats['avg_risk_score'] or 0, 1)
            },
            'chain_breakdown': chain_breakdown,
            'recent_tokens': recent_tokens,
            'last_updated': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        return {
            'summary': {
                'total_scanned': 0,
                'rug_detected': 0,
                'fake_volume': 0,
                'passed_checks': 0,
                'alerts_sent': 0,
                'rug_percentage': 0,
                'fake_volume_percentage': 0,
                'pass_percentage': 0,
                'average_risk_score': 0
            },
            'chain_breakdown': {},
            'recent_tokens': [],
            'last_updated': datetime.now().isoformat()
        }

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard statistics"""
    return jsonify(get_dashboard_stats())

@app.route('/api/tokens')
def api_tokens():
    """API endpoint for recent tokens"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT token_name, token_symbol, chain, market_cap, risk_score, status, timestamp
            FROM token_checks 
            WHERE timestamp > datetime('now', '-24 hours')
            ORDER BY timestamp DESC 
            LIMIT 50
        """)
        
        tokens = []
        for row in cursor.fetchall():
            tokens.append({
                'token_name': row['token_name'],
                'token_symbol': row['token_symbol'],
                'chain': row['chain'],
                'market_cap': row['market_cap'],
                'risk_score': row['risk_score'],
                'status': row['status'],
                'timestamp': row['timestamp']
            })
        
        conn.close()
        return jsonify(tokens)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts')
def api_alerts():
    """API endpoint for recent alerts"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if alerts table exists and has data
        cursor.execute("SELECT COUNT(*) FROM alerts")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Return empty list if no alerts
            conn.close()
            return jsonify([])
        
        cursor.execute("""
            SELECT token_name, token_symbol, chain, risk_score, timestamp
            FROM alerts 
            WHERE timestamp > datetime('now', '-24 hours')
            ORDER BY timestamp DESC 
            LIMIT 50
        """)
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                'token_name': row['token_name'],
                'token_symbol': row['token_symbol'], 
                'chain': row['chain'],
                'risk_score': row['risk_score'],
                'timestamp': row['timestamp']
            })
        
        conn.close()
        return jsonify(alerts)
        
    except Exception as e:
        print(f"Error in alerts API: {e}")
        return jsonify([]), 200  # Return empty list instead of error

if __name__ == '__main__':
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)