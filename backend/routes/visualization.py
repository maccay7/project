import json
from flask import request, jsonify
from utils.db import get_db
from datetime import datetime, timedelta
from pages.calculations_details import calculate_data


def create_visualization_cache_table():
    """Create the visualization_cache table if it doesn't exist."""
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visualization_cache (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cache_key VARCHAR(255) UNIQUE,
                instrument_type VARCHAR(50),
                country VARCHAR(50),
                currency VARCHAR(50),
                maturity VARCHAR(50),
                chart_data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating visualization_cache table: {e}")
        conn.close()
        return False


def get_cached_visualization(cache_key):
    """Get cached visualization data if not expired."""
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM visualization_cache WHERE cache_key = %s AND expires_at > NOW()",
            (cache_key,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
        
        return {
            'id': row['id'],
            'cache_key': row['cache_key'],
            'instrument_type': row['instrument_type'],
            'country': row['country'],
            'currency': row['currency'],
            'maturity': row['maturity'],
            'chart_data': json.loads(row['chart_data']) if row['chart_data'] else {},
            'created_at': row['created_at'].isoformat() if row['created_at'] else None
        }
    except Exception as e:
        print(f"Error getting cached visualization: {e}")
        conn.close()
        return None


def cache_visualization(cache_key, instrument_type, country, currency, maturity, chart_data, cache_duration_minutes=5):
    """Cache visualization data."""
    conn = get_db()
    if not conn:
        return False
    try:
        expires_at = datetime.now() + timedelta(minutes=cache_duration_minutes)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO visualization_cache 
               (cache_key, instrument_type, country, currency, maturity, chart_data, expires_at) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               chart_data = VALUES(chart_data),
               created_at = CURRENT_TIMESTAMP,
               expires_at = VALUES(expires_at)""",
            (cache_key, instrument_type, country, currency, maturity, json.dumps(chart_data), expires_at)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error caching visualization: {e}")
        conn.close()
        return False


def prepare_yield_curve_data(instrument_type, country, currency, maturity):
    """
    Prepare yield curve data for visualization.
    Returns: { labels: [], datasets: [] }
    """
    # Generate cache key
    cache_key = f"yield_curve_{instrument_type}_{country}_{currency}_{maturity}"
    
    # Check cache first
    cached = get_cached_visualization(cache_key)
    if cached:
        return cached['chart_data']
    
    # Generate mock yield curve data (in production, this would call FRED API)
    labels = []
    datasets = []
    
    # Generate time labels based on maturity
    maturity_months = {
        '1M': 1, '3M': 3, '6M': 6, '1Y': 12,
        '2Y': 24, '5Y': 60, '10Y': 120, '30Y': 360,
        '4W': 1, '8W': 2, '13W': 3, '26W': 6, '52W': 12
    }
    
    months = maturity_months.get(maturity, 12)
    
    # Generate labels for the selected period
    for i in range(12):
        date = datetime.now() - timedelta(days=30 * i)
        labels.append(date.strftime('%Y-%m'))
    
    labels.reverse()
    
    # Generate dataset with mock rates
    base_rate = 4.5  # Base rate in percentage
    dataset = {
        'label': f'{country} {maturity} Yield Curve',
        'data': [base_rate + (i * 0.1) for i in range(12)],
        'borderColor': 'rgb(75, 192, 192)',
        'backgroundColor': 'rgba(75, 192, 192, 0.2)',
        'fill': False
    }
    datasets.append(dataset)
    
    chart_data = {
        'labels': labels,
        'datasets': datasets
    }
    
    # Cache the result
    cache_visualization(cache_key, instrument_type, country, currency, maturity, chart_data)
    
    return chart_data


def prepare_chart_data(data, instrument_type):
    """
    Prepare chart data for instrument comparison.
    Returns: { labels: [], datasets: [] }
    """
    if not data or not isinstance(data, list):
        return {'labels': [], 'datasets': []}
    
    labels = []
    values = []
    
    for item in data:
        name = item.get('Instrument') or item.get('BondName') or item.get('TBillName') or f'Instrument {len(labels) + 1}'
        value = item.get('CalculatedValue') or item.get('FaceValue') or 0
        labels.append(name)
        values.append(float(value))
    
    dataset = {
        'label': 'Instrument Values',
        'data': values,
        'backgroundColor': [
            'rgba(255, 99, 132, 0.6)',
            'rgba(54, 162, 235, 0.6)',
            'rgba(255, 206, 86, 0.6)',
            'rgba(75, 192, 192, 0.6)',
            'rgba(153, 102, 255, 0.6)'
        ]
    }
    
    return {
        'labels': labels,
        'datasets': [dataset]
    }


def prepare_dashboard_statistics(session_id):
    """
    Prepare dashboard statistics.
    Returns: statistics object
    """
    conn = get_db()
    if not conn:
        return {}
    
    try:
        cursor = conn.cursor()
        
        # Get portfolio data for session
        cursor.execute("SELECT * FROM portfolios WHERE session_id = %s", (session_id,))
        portfolios = cursor.fetchall()
        
        # Get session data
        cursor.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
        session = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        stats = {
            'total_sessions': 0,
            'active_sessions': 0,
            'total_instruments': 0,
            'total_value': 0,
            'portfolio_count': len(portfolios)
        }
        
        if session:
            stats['session_name'] = session['name']
            stats['instrument_type'] = session['instrument_type']
        
        for portfolio in portfolios:
            stats['total_instruments'] += portfolio['instrument_count']
            stats['total_value'] += float(portfolio['total_value'])
        
        return stats
        
    except Exception as e:
        print(f"Error preparing dashboard statistics: {e}")
        conn.close()
        return {}


def visualization_routes(app):
    """Register all visualization routes."""
    
    # Create table on module load
    create_visualization_cache_table()
    
    @app.route('/api/visualization/yield-curve', methods=['POST', 'OPTIONS'])
    def yield_curve_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        instrument_type = payload.get('instrument_type', 'money-market')
        country = payload.get('country', 'US')
        currency = payload.get('currency', 'USD')
        maturity = payload.get('maturity', '1Y')
        
        chart_data = prepare_yield_curve_data(instrument_type, country, currency, maturity)
        
        return jsonify({
            'success': True,
            'data': chart_data
        })
    
    @app.route('/api/visualization/chart-data', methods=['POST', 'OPTIONS'])
    def chart_data_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        data = payload.get('data', [])
        instrument_type = payload.get('instrument_type', 'money-market')
        
        chart_data = prepare_chart_data(data, instrument_type)
        
        return jsonify({
            'success': True,
            'data': chart_data
        })
    
    @app.route('/api/visualization/dashboard/<int:session_id>', methods=['GET', 'OPTIONS'])
    def dashboard_statistics_endpoint(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        
        stats = prepare_dashboard_statistics(session_id)
        
        return jsonify({
            'success': True,
            'data': stats
        })
    
    @app.route('/api/visualization/cache/clear', methods=['DELETE', 'OPTIONS'])
    def clear_cache_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM visualization_cache WHERE expires_at < NOW()")
            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'data': {'deleted_count': deleted_count}
            })
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500
