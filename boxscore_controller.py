"""
Box Score Controller
Orchestrates fallback strategy across multiple data sources
"""

from typing import List, Dict, Optional
import json
import os
from datetime import datetime
from pathlib import Path

# Import source modules
from sources import nba_api_source, espn_api_source


def validate_boxscores(boxscores: List[Dict]) -> bool:
    """
    Validate box score data

    Args:
        boxscores: List of box score dictionaries

    Returns:
        True if valid, False otherwise
    """
    if not boxscores:
        return False

    # Check required fields
    required_fields = ["game_id", "game_date", "player", "team", "pts", "reb", "ast"]

    for box in boxscores:
        for field in required_fields:
            if field not in box:
                return False

        # Check numeric bounds
        if not (0 <= box["pts"] <= 100):
            return False
        if not (0 <= box["reb"] <= 40):
            return False
        if not (0 <= box["ast"] <= 30):
            return False

    return True


def persist_boxscores(boxscores: List[Dict], source: str, date_str: str):
    """
    Save box scores to disk (optional - skips if directory creation fails)

    Args:
        boxscores: List of box score dictionaries
        source: Name of the data source
        date_str: Date string (YYYY-MM-DD)
    """
    try:
        # Create directories if they don't exist
        raw_dir = Path("data/raw") / source / date_str
        raw_dir.mkdir(parents=True, exist_ok=True)

        processed_dir = Path("data/processed")
        processed_dir.mkdir(parents=True, exist_ok=True)

        logs_dir = Path("data/logs")
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Save raw JSON
        raw_file = raw_dir / f"boxscores_{datetime.utcnow().timestamp()}.json"
        with open(raw_file, "w") as f:
            json.dump(boxscores, f, indent=2)

        # Save processed CSV
        import pandas as pd
        df = pd.DataFrame(boxscores)
        csv_file = processed_dir / f"boxscores_{date_str}.csv"
        df.to_csv(csv_file, index=False)

        # Log metadata
        log_entry = {
            "date": date_str,
            "source": source,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "games_found": len(set(box["game_id"] for box in boxscores)),
            "players_found": len(boxscores),
            "status": "success"
        }

        log_file = logs_dir / f"scrape_log_{date_str}.json"
        logs = []
        if log_file.exists():
            with open(log_file, "r") as f:
                logs = json.load(f)

        logs.append(log_entry)

        with open(log_file, "w") as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        # Silently skip persistence on read-only file systems (e.g., Vercel)
        print(f"Note: Could not persist data (read-only filesystem): {e}")


def fetch_boxscores(date_str: str, game_id: Optional[str] = None, force_source: Optional[str] = None) -> Dict:
    """
    Main controller to fetch box scores with fallback strategy

    Args:
        date_str: Date in YYYY-MM-DD format
        game_id: Optional specific game ID
        force_source: Optional force a specific source

    Returns:
        Dictionary with results and metadata
    """
    # Define fallback order
    sources = [
        ("NBA_API", nba_api_source.fetch_boxscores),
        ("ESPN_API", espn_api_source.fetch_boxscores),
    ]

    # If force_source specified, only use that one
    if force_source:
        sources = [(name, func) for name, func in sources if name == force_source]

    result = {
        "success": False,
        "date": date_str,
        "game_id": game_id,
        "source": None,
        "boxscores": [],
        "errors": []
    }

    for source_name, source_func in sources:
        try:
            print(f"Trying {source_name} for {date_str}...")

            boxscores = source_func(date_str, game_id)

            if boxscores and validate_boxscores(boxscores):
                print(f"✓ {source_name} returned {len(boxscores)} player records")

                # Persist data
                persist_boxscores(boxscores, source_name, date_str)

                result["success"] = True
                result["source"] = source_name
                result["boxscores"] = boxscores
                return result
            else:
                print(f"✗ {source_name} returned no valid data")

        except Exception as e:
            error_msg = f"{source_name} error: {str(e)}"
            print(f"✗ {error_msg}")
            result["errors"].append(error_msg)

    # If we get here, all sources failed
    result["errors"].append("All sources failed to return valid box scores")
    return result


if __name__ == "__main__":
    # Test with a known date
    test_date = "2025-06-05"  # NBA Finals Game 1
    result = fetch_boxscores(test_date)

    print(f"\nResults:")
    print(f"Success: {result['success']}")
    print(f"Source: {result['source']}")
    print(f"Players: {len(result['boxscores'])}")

    if result['boxscores']:
        print(f"\nSample player:")
        print(json.dumps(result['boxscores'][0], indent=2))
