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


def sync_fantasy_data(output_dir: str = "data/fantasy") -> Dict:
    """
    Sync ESPN Fantasy Basketball data and save to disk

    Args:
        output_dir: Base directory for fantasy data storage

    Returns:
        Dictionary with sync results and metadata
    """
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

        # Create output directory with timestamp
        today = datetime.now().strftime("%Y-%m-%d")
        output_path = Path(output_dir) / today
        output_path.mkdir(parents=True, exist_ok=True)

        # Fetch teams
        print("Fetching teams...")
        teams = client.get_teams()
        teams_df = pd.DataFrame(teams)
        teams_file = output_path / "teams.csv"
        teams_df.to_csv(teams_file, index=False)
        result["teams_count"] = len(teams)
        print(f"   Saved {len(teams)} teams to {teams_file}")

        # Fetch rosters
        print("Fetching rosters...")
        rosters = client.get_rosters()
        rosters_df = pd.DataFrame(rosters)
        rosters_file = output_path / "rosters.csv"
        rosters_df.to_csv(rosters_file, index=False)
        result["rosters_count"] = len(rosters)
        print(f"   Saved {len(rosters)} roster entries to {rosters_file}")

        # Fetch matchups
        print("Fetching matchups...")
        matchups = client.get_matchups()
        if matchups:
            matchups_df = pd.DataFrame(matchups)
            matchups_file = output_path / "matchups.csv"
            matchups_df.to_csv(matchups_file, index=False)
            result["matchups_count"] = len(matchups)
            print(f"   Saved {len(matchups)} matchups to {matchups_file}")

        # Fetch free agents
        print("Fetching top free agents...")
        free_agents = client.get_free_agents(size=100)
        if free_agents:
            fa_df = pd.DataFrame(free_agents)
            fa_file = output_path / "free_agents.csv"
            fa_df.to_csv(fa_file, index=False)
            result["free_agents_count"] = len(free_agents)
            print(f"   Saved {len(free_agents)} free agents to {fa_file}")

        # Save league settings
        settings_file = output_path / "league_settings.json"
        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=2)
        print(f"   Saved league settings to {settings_file}")

        result["status"] = "success"
        print(f"\nFantasy data synced successfully for {today}")

    except Exception as e:
        error_msg = f"Sync failed: {str(e)}"
        result["errors"].append(error_msg)
        print(f"ERROR: {error_msg}")

    finally:
        # Save sync log
        log_dir = Path("logs/fantasy")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"sync_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(log_file, "w") as f:
            json.dump(result, f, indent=2)

        print(f"Sync log saved to {log_file}")

    return result


def get_latest_fantasy_data(data_dir: str = "data/fantasy") -> Dict[str, pd.DataFrame]:
    """
    Load the most recent fantasy data from disk

    Args:
        data_dir: Base directory for fantasy data

    Returns:
        Dictionary with teams, rosters, matchups, free_agents DataFrames
    """
    data_path = Path(data_dir)

    if not data_path.exists():
        raise FileNotFoundError(f"Fantasy data directory not found: {data_dir}")

    # Find the most recent date directory
    date_dirs = sorted([d for d in data_path.iterdir() if d.is_dir()], reverse=True)

    if not date_dirs:
        raise FileNotFoundError("No fantasy data available")

    latest_dir = date_dirs[0]
    # Removed emoji to avoid Windows encoding issues

    result = {}

    # Load each CSV file
    for file_name in ["teams", "rosters", "matchups", "free_agents"]:
        csv_file = latest_dir / f"{file_name}.csv"
        if csv_file.exists():
            result[file_name] = pd.read_csv(csv_file)
        else:
            pass  # Silent skip for missing files

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
