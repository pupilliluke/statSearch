"""
Flask API for NBA Stat Tracker
Exposes the scraper functionality via REST endpoints
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import date, timedelta
import sys
import io
import tracker

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """
    Get NBA stats based on query parameters
    Query params:
        - date: YYYY-MM-DD (optional, defaults to today)
        - pts: points threshold (optional)
        - ast: assists threshold (optional)
        - reb: rebounds threshold (optional)
        - logic: 'any' or 'all' (default: 'any')
    """
    try:
        # Parse parameters
        target_date = request.args.get('date')
        pts_thr = request.args.get('pts', type=int)
        ast_thr = request.args.get('ast', type=int)
        reb_thr = request.args.get('reb', type=int)
        logic = request.args.get('logic', 'any')

        # Default to today if no date provided
        if not target_date:
            target_date = date.today().strftime("%Y-%m-%d")

        # Suppress print statements from tracker module (Windows emoji encoding issue)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            # Fetch stats
            players, source = tracker.get_all_stats(target_date, pts_thr, ast_thr, reb_thr, logic)

            # If no results and no specific date was requested, try yesterday
            if not players and not request.args.get('date'):
                yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
                players, source = tracker.get_all_stats(yesterday, pts_thr, ast_thr, reb_thr, logic)
                target_date = yesterday
        finally:
            sys.stdout = old_stdout

        # Build response
        response = {
            'success': True,
            'date': target_date,
            'source': source,
            'count': len(players),
            'players': players,
            'filters': {
                'pts': pts_thr,
                'ast': ast_thr,
                'reb': reb_thr,
                'logic': logic
            }
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
