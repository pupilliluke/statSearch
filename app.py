"""
Flask API for NBA Stat Tracker
Exposes the scraper functionality via REST endpoints
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import date, timedelta
import sys
import io
import requests
import tracker
import boxscore_controller

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

@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    """
    Get NBA game schedule for a specific date using ESPN API
    Query params:
        - date: YYYY-MM-DD (optional, defaults to today)
    """
    try:
        target_date = request.args.get('date')

        if not target_date:
            target_date = date.today().strftime("%Y-%m-%d")

        # Convert YYYY-MM-DD to YYYYMMDD for ESPN API
        date_str = target_date.replace("-", "")

        # Fetch from ESPN API
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
        response = requests.get(url, timeout=10)
        data = response.json()

        games = []
        events = data.get("events", [])

        for event in events:
            game_id = event.get("id")
            game_name = event.get("name", "")
            game_date = event.get("date", "")
            status = event.get("status", {})
            game_status = status.get("type", {}).get("description", "Scheduled")
            game_state = status.get("type", {}).get("state", "pre")

            competitions = event.get("competitions", [])
            if not competitions:
                continue

            competition = competitions[0]
            competitors = competition.get("competitors", [])

            home_team = None
            away_team = None

            for team in competitors:
                team_info = {
                    "id": team.get("id"),
                    "name": team.get("team", {}).get("displayName", ""),
                    "abbreviation": team.get("team", {}).get("abbreviation", ""),
                    "logo": team.get("team", {}).get("logo", ""),
                    "score": team.get("score", "0"),
                    "record": team.get("records", [{}])[0].get("summary", "") if team.get("records") else ""
                }

                if team.get("homeAway") == "home":
                    home_team = team_info
                else:
                    away_team = team_info

            games.append({
                "id": game_id,
                "name": game_name,
                "date": game_date,
                "status": game_status,
                "state": game_state,
                "home": home_team,
                "away": away_team
            })

        return jsonify({
            'success': True,
            'date': target_date,
            'count': len(games),
            'games': games
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/boxscore', methods=['GET'])
def get_boxscore():
    """
    Get box score for a specific game
    Query params:
        - game_id: Game ID (required)
        - date: YYYY-MM-DD (optional, for context)
        - source: Force specific source (optional)
    """
    try:
        game_id = request.args.get('game_id')
        date_param = request.args.get('date')
        force_source = request.args.get('source')

        if not game_id and not date_param:
            return jsonify({
                'success': False,
                'error': 'Either game_id or date is required'
            }), 400

        # Suppress print statements from controller
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            # Fetch box scores
            if date_param:
                result = boxscore_controller.fetch_boxscores(
                    date_param,
                    game_id=game_id,
                    force_source=force_source
                )
            else:
                # If only game_id provided, need to infer date (use today as fallback)
                result = boxscore_controller.fetch_boxscores(
                    date.today().strftime("%Y-%m-%d"),
                    game_id=game_id,
                    force_source=force_source
                )
        finally:
            sys.stdout = old_stdout

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/schedule')
def schedule_page():
    return app.send_static_file('schedule.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
