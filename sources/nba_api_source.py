"""
NBA API Source - Priority 1
Uses official NBA stats API via nba_api library
"""

from typing import List, Dict, Optional
from datetime import datetime
import time
import os


def fetch_boxscores(date_str: str, game_id: Optional[str] = None) -> List[Dict]:
    """
    Fetch box scores from NBA API

    Args:
        date_str: Date in YYYY-MM-DD format
        game_id: Optional specific game ID to fetch

    Returns:
        List of standardized player box score dictionaries
    """
    try:
        from nba_api.stats.endpoints import scoreboardv2, boxscoretraditionalv2
    except ImportError:
        return []

    results = []

    try:
        # Get games for the date
        if game_id:
            game_ids = [game_id]
        else:
            scoreboard = scoreboardv2.ScoreboardV2(game_date=date_str, day_offset=0)
            games_df = scoreboard.get_data_frames()[0]
            game_ids = games_df["GAME_ID"].unique().tolist()

            # Limit games on serverless to avoid timeout (10s on Vercel free)
            max_games = int(os.environ.get('MAX_GAMES_PER_REQUEST', '15'))
            if len(game_ids) > max_games:
                print(f"Warning: Limiting to first {max_games} games to avoid timeout")
                game_ids = game_ids[:max_games]

        # Fetch box score for each game
        for gid in game_ids:
            try:
                time.sleep(0.3)  # Rate limit: ~3 req/sec (faster for serverless)

                boxscore = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=gid)
                players_df = boxscore.get_data_frames()[0]

                for _, row in players_df.iterrows():
                    # Skip players who didn't play (DNP)
                    if not row["MIN"] or row["MIN"] == "" or row["MIN"] is None:
                        continue

                    # Also skip if minutes is 0 or 0:00
                    min_str = str(row["MIN"])
                    if min_str in ["0", "0:00", "0.0"]:
                        continue

                    results.append({
                        "game_id": gid,
                        "game_date": date_str,
                        "player": row["PLAYER_NAME"],
                        "team": row["TEAM_ABBREVIATION"],
                        "pts": int(row["PTS"]) if row["PTS"] else 0,
                        "reb": int(row["REB"]) if row["REB"] else 0,
                        "ast": int(row["AST"]) if row["AST"] else 0,
                        "stl": int(row["STL"]) if row["STL"] else 0,
                        "blk": int(row["BLK"]) if row["BLK"] else 0,
                        "fg_pct": float(row["FG_PCT"]) if row["FG_PCT"] else 0.0,
                        "fg3_pct": float(row["FG3_PCT"]) if row["FG3_PCT"] else 0.0,
                        "ft_pct": float(row["FT_PCT"]) if row["FT_PCT"] else 0.0,
                        "min": row["MIN"],
                        "source": "NBA_API",
                        "timestamp_utc": datetime.utcnow().isoformat() + "Z"
                    })

            except Exception as e:
                continue

        return results

    except Exception as e:
        return []
