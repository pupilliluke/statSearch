"""
Fantasy Sync Service
Fetches, cleans, and normalizes ESPN Fantasy Basketball data
"""

from typing import Dict, List
import pandas as pd
from datetime import datetime
import os
import json
from pathlib import Path
from fantasy.espn_client import create_client_from_env

# In-memory cache for serverless environments (e.g., Vercel)
_fantasy_cache = {
    "timestamp": None,
    "data": {}
}


def sync_fantasy_data(output_dir: str = "data/fantasy") -> Dict:
    """
    Sync ESPN Fantasy Basketball data and save to disk (or cache in-memory if read-only)

    Args:
        output_dir: Base directory for fantasy data storage

    Returns:
        Dictionary with sync results and metadata
    """
    global _fantasy_cache

    result = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "failed",
        "teams_count": 0,
        "rosters_count": 0,
        "matchups_count": 0,
        "free_agents_count": 0,
        "errors": []
    }

    try:
        # Create client
        print("Connecting to ESPN Fantasy API...")
        client = create_client_from_env()

        # Get league settings
        settings = client.get_league_settings()
        print(f"Connected to: {settings['name']}")
        print(f"   Year: {settings['year']}, Week: {settings['current_week']}")

        # Fetch teams
        print("Fetching teams...")
        teams = client.get_teams()
        teams_df = pd.DataFrame(teams)
        result["teams_count"] = len(teams)

        # Fetch rosters
        print("Fetching rosters...")
        rosters = client.get_rosters()
        rosters_df = pd.DataFrame(rosters)
        result["rosters_count"] = len(rosters)

        # Fetch matchups
        print("Fetching matchups...")
        matchups = client.get_matchups()
        matchups_df = pd.DataFrame(matchups) if matchups else pd.DataFrame()
        result["matchups_count"] = len(matchups) if matchups else 0

        # Fetch free agents
        print("Fetching top free agents...")
        free_agents = client.get_free_agents(size=100)
        fa_df = pd.DataFrame(free_agents) if free_agents else pd.DataFrame()
        result["free_agents_count"] = len(free_agents) if free_agents else 0

        # Store in memory cache
        _fantasy_cache["timestamp"] = datetime.utcnow().isoformat() + "Z"
        _fantasy_cache["data"] = {
            "teams": teams_df,
            "rosters": rosters_df,
            "matchups": matchups_df,
            "free_agents": fa_df,
            "settings": settings
        }
        print("Data cached in memory")

        # Try to save to disk (optional - will fail gracefully on read-only file systems)
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            output_path = Path(output_dir) / today
            output_path.mkdir(parents=True, exist_ok=True)

            teams_file = output_path / "teams.csv"
            teams_df.to_csv(teams_file, index=False)
            print(f"   Saved {len(teams)} teams to {teams_file}")

            rosters_file = output_path / "rosters.csv"
            rosters_df.to_csv(rosters_file, index=False)
            print(f"   Saved {len(rosters)} roster entries to {rosters_file}")

            if not matchups_df.empty:
                matchups_file = output_path / "matchups.csv"
                matchups_df.to_csv(matchups_file, index=False)
                print(f"   Saved {len(matchups)} matchups to {matchups_file}")

            if not fa_df.empty:
                fa_file = output_path / "free_agents.csv"
                fa_df.to_csv(fa_file, index=False)
                print(f"   Saved {len(free_agents)} free agents to {fa_file}")

            settings_file = output_path / "league_settings.json"
            with open(settings_file, "w") as f:
                json.dump(settings, f, indent=2)
            print(f"   Saved league settings to {settings_file}")

        except Exception as e:
            print(f"Note: Could not save to disk (read-only filesystem): {e}")

        result["status"] = "success"
        print(f"\nFantasy data synced successfully")

    except Exception as e:
        error_msg = f"Sync failed: {str(e)}"
        result["errors"].append(error_msg)
        print(f"ERROR: {error_msg}")

    finally:
        # Try to save sync log (optional)
        try:
            log_dir = Path("logs/fantasy")
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"sync_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(log_file, "w") as f:
                json.dump(result, f, indent=2)

            print(f"Sync log saved to {log_file}")
        except Exception:
            pass  # Silently skip on read-only file systems

    return result


def get_latest_fantasy_data(data_dir: str = "data/fantasy") -> Dict[str, pd.DataFrame]:
    """
    Load the most recent fantasy data from disk or in-memory cache

    Args:
        data_dir: Base directory for fantasy data

    Returns:
        Dictionary with teams, rosters, matchups, free_agents DataFrames
    """
    global _fantasy_cache

    # Try in-memory cache first (for serverless environments)
    if _fantasy_cache["data"]:
        print("Using cached fantasy data")
        return _fantasy_cache["data"]

    # Try to load from disk
    data_path = Path(data_dir)

    if not data_path.exists():
        # No disk data, no cache - need to sync first
        print("No fantasy data available - syncing now...")
        sync_result = sync_fantasy_data(data_dir)
        if sync_result["status"] == "success" and _fantasy_cache["data"]:
            return _fantasy_cache["data"]
        else:
            raise FileNotFoundError(f"Fantasy data directory not found: {data_dir}")

    # Find the most recent date directory
    date_dirs = sorted([d for d in data_path.iterdir() if d.is_dir()], reverse=True)

    if not date_dirs:
        # No disk data - sync first
        print("No fantasy data available - syncing now...")
        sync_result = sync_fantasy_data(data_dir)
        if sync_result["status"] == "success" and _fantasy_cache["data"]:
            return _fantasy_cache["data"]
        else:
            raise FileNotFoundError("No fantasy data available")

    latest_dir = date_dirs[0]

    result = {}

    # Load each CSV file
    for file_name in ["teams", "rosters", "matchups", "free_agents"]:
        csv_file = latest_dir / f"{file_name}.csv"
        if csv_file.exists():
            result[file_name] = pd.read_csv(csv_file)
        else:
            result[file_name] = pd.DataFrame()  # Return empty DataFrame instead of skipping

    return result


if __name__ == "__main__":
    # Run sync
    result = sync_fantasy_data()

    if result["status"] == "success":
        print("\n" + "="*50)
        print("SYNC SUMMARY")
        print("="*50)
        print(f"Teams:        {result['teams_count']}")
        print(f"Rosters:      {result['rosters_count']}")
        print(f"Matchups:     {result['matchups_count']}")
        print(f"Free Agents:  {result['free_agents_count']}")
        print("="*50)
    else:
        print(f"\n❌ Sync failed: {result['errors']}")
