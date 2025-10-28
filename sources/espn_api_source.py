"""
ESPN API Source - Priority 2
Uses ESPN's public JSON API
"""

from typing import List, Dict, Optional
from datetime import datetime
import requests
import time


def _parse_espn_player_stats(athlete_data: dict, team_abbr: str, game_id: str, game_date: str) -> Optional[Dict]:
    """Parse ESPN athlete statistics into standardized format"""
    try:
        stats_dict = {}
        for stat in athlete_data.get("stats", []):
            name = stat.get("name", "").lower()
            value = stat.get("displayValue", "0")
            stats_dict[name] = value

        # Get minutes played
        minutes = stats_dict.get("minutes", "0:00")

        # Skip players who didn't play (DNP)
        if not minutes or minutes in ["0", "0:00", "0.0", ""]:
            return None

        # Convert stats
        pts = float(stats_dict.get("points", 0) or stats_dict.get("pts", 0) or 0)
        reb = float(stats_dict.get("rebounds", 0) or stats_dict.get("reb", 0) or 0)
        ast = float(stats_dict.get("assists", 0) or stats_dict.get("ast", 0) or 0)

        return {
            "game_id": game_id,
            "game_date": game_date,
            "player": athlete_data.get("athlete", {}).get("displayName", "Unknown"),
            "team": team_abbr,
            "pts": int(pts),
            "reb": int(reb),
            "ast": int(ast),
            "stl": int(float(stats_dict.get("steals", 0) or stats_dict.get("stl", 0) or 0)),
            "blk": int(float(stats_dict.get("blocks", 0) or stats_dict.get("blk", 0) or 0)),
            "fg_pct": 0.0,
            "fg3_pct": 0.0,
            "ft_pct": 0.0,
            "min": minutes,
            "source": "ESPN_API",
            "timestamp_utc": datetime.utcnow().isoformat() + "Z"
        }
    except Exception:
        return None


def fetch_boxscores(date_str: str, game_id: Optional[str] = None) -> List[Dict]:
    """
    Fetch box scores from ESPN API

    Args:
        date_str: Date in YYYY-MM-DD format
        game_id: Optional specific ESPN event ID

    Returns:
        List of standardized player box score dictionaries
    """
    results = []

    try:
        # Convert YYYY-MM-DD to YYYYMMDD
        date_formatted = date_str.replace("-", "")

        # Get games for the date
        if game_id:
            event_ids = [game_id]
        else:
            scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_formatted}"
            resp = requests.get(scoreboard_url, timeout=10)
            data = resp.json()
            event_ids = [event.get("id") for event in data.get("events", [])]

        # Fetch box score for each game
        for event_id in event_ids:
            time.sleep(0.2)  # Rate limiting (faster for serverless)

            # Try summary endpoint first
            for endpoint in ["summary", "boxscore"]:
                try:
                    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/{endpoint}?event={event_id}"
                    resp = requests.get(url, timeout=10)
                    data = resp.json()

                    boxscore = data.get("boxscore", {})
                    if not boxscore:
                        continue

                    # Parse teams and players
                    for team_data in boxscore.get("teams", []) + boxscore.get("players", []):
                        team_info = team_data.get("team", {})
                        team_abbr = team_info.get("abbreviation", "UNK")

                        for stat_group in team_data.get("statistics", []):
                            for athlete_data in stat_group.get("athletes", []):
                                player_stat = _parse_espn_player_stats(
                                    athlete_data, team_abbr, event_id, date_str
                                )
                                if player_stat:
                                    results.append(player_stat)

                    if results:
                        break  # Got data, no need to try other endpoint

                except Exception:
                    continue

    except Exception:
        pass

    return results
