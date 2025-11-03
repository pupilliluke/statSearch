"""
Merge Pipeline
Combines ESPN Fantasy data with real NBA box score data
"""

import pandas as pd
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
import re


def normalize_player_name(name: str) -> str:
    """
    Normalize player name for matching

    Args:
        name: Player name string

    Returns:
        Normalized name (lowercase, no special chars)
    """
    # Remove suffixes like Jr., Sr., III
    name = re.sub(r'\s+(Jr\.|Sr\.|III|II|IV)\.?$', '', name, flags=re.IGNORECASE)
    # Convert to lowercase and remove special characters
    name = re.sub(r'[^a-z\s]', '', name.lower())
    # Remove extra whitespace
    name = ' '.join(name.split())
    return name


def fuzzy_match_players(fantasy_df: pd.DataFrame, real_df: pd.DataFrame) -> pd.DataFrame:
    """
    Match fantasy players with real box score data using fuzzy matching

    Args:
        fantasy_df: DataFrame with fantasy roster data
        real_df: DataFrame with real box score data

    Returns:
        Merged DataFrame
    """
    # Normalize names for matching
    fantasy_df['player_normalized'] = fantasy_df['player_name'].apply(normalize_player_name)
    real_df['player_normalized'] = real_df['player'].apply(normalize_player_name)

    # Merge on normalized names
    merged = fantasy_df.merge(
        real_df,
        left_on='player_normalized',
        right_on='player_normalized',
        how='left',
        suffixes=('_fantasy', '_real')
    )

    # Drop normalized column
    merged = merged.drop(columns=['player_normalized'])

    return merged


def calculate_fantasy_points(row: pd.Series, scoring: Dict[str, float] = None) -> float:
    """
    Calculate fantasy points based on real stats

    Args:
        row: DataFrame row with stats
        scoring: Custom scoring dict (defaults to standard ESPN scoring)

    Returns:
        Calculated fantasy points
    """
    if scoring is None:
        # Standard ESPN Fantasy Basketball scoring
        scoring = {
            'pts': 1.0,
            'reb': 1.2,
            'ast': 1.5,
            'stl': 3.0,
            'blk': 3.0,
            'fg_made': 1.0,
            'fg_miss': -1.0,
            'ft_made': 1.0,
            'ft_miss': -1.0,
            'to': -1.0
        }

    pts = 0
    pts += row.get('pts', 0) * scoring.get('pts', 1.0)
    pts += row.get('reb', 0) * scoring.get('reb', 1.2)
    pts += row.get('ast', 0) * scoring.get('ast', 1.5)
    pts += row.get('stl', 0) * scoring.get('stl', 3.0)
    pts += row.get('blk', 0) * scoring.get('blk', 3.0)

    return round(pts, 2)


def merge_fantasy_with_boxscores(
    fantasy_rosters: pd.DataFrame,
    boxscores: pd.DataFrame,
    date_str: Optional[str] = None
) -> pd.DataFrame:
    """
    Main merge function combining fantasy rosters with box score data

    Args:
        fantasy_rosters: DataFrame from fantasy sync (rosters.csv)
        boxscores: DataFrame from box score scraper
        date_str: Optional date filter for box scores

    Returns:
        Merged DataFrame with fantasy and real stats
    """
    # Filter boxscores by date if provided
    if date_str and 'game_date' in boxscores.columns:
        boxscores = boxscores[boxscores['game_date'] == date_str].copy()

    # Perform fuzzy match
    merged = fuzzy_match_players(fantasy_rosters, boxscores)

    # Calculate estimated fantasy points from real stats
    merged['fantasy_pts_estimated'] = merged.apply(calculate_fantasy_points, axis=1)

    # Add variance column (difference between fantasy total and estimated)
    if 'total_points' in merged.columns:
        merged['pts_variance'] = merged['total_points'] - merged['fantasy_pts_estimated']

    # Add performance indicators
    merged['has_real_stats'] = merged['pts'].notna()
    merged['missed_game'] = (merged['has_real_stats'] == False) & (merged['injured'] == False)

    return merged


def generate_daily_fantasy_report(
    fantasy_data_dir: str = "data/fantasy",
    boxscore_data_dir: str = "data/processed",
    target_date: Optional[str] = None
) -> Dict:
    """
    Generate comprehensive daily fantasy report

    Args:
        fantasy_data_dir: Directory with fantasy data
        boxscore_data_dir: Directory with box score data
        target_date: Date to analyze (defaults to yesterday)

    Returns:
        Dictionary with report data
    """
    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    report = {
        "date": target_date,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "top_performers": [],
        "underperformers": [],
        "injured_players": [],
        "free_agent_recommendations": []
    }

    try:
        # Load latest fantasy data
        from fantasy.fantasy_sync import get_latest_fantasy_data
        fantasy_data = get_latest_fantasy_data(fantasy_data_dir)

        # Load box score data for the date
        boxscore_file = Path(boxscore_data_dir) / f"boxscores_{target_date}.csv"

        if not boxscore_file.exists():
            # Try to fetch boxscores on-demand
            print(f"Warning: No cached box score data found for {target_date}, fetching...")
            import boxscore_controller
            result = boxscore_controller.fetch_boxscores(target_date)
            if result['success'] and result['boxscores']:
                boxscores = pd.DataFrame(result['boxscores'])
            else:
                print(f"Warning: Could not fetch box score data for {target_date}")
                return report
        else:
            boxscores = pd.read_csv(boxscore_file)

        # Merge data
        merged = merge_fantasy_with_boxscores(
            fantasy_data['rosters'],
            boxscores,
            target_date
        )

        # Generate insights
        # Top performers (highest fantasy points)
        top = merged[merged['has_real_stats'] == True].nlargest(10, 'fantasy_pts_estimated')
        report['top_performers'] = top[['player_name', 'team_name', 'fantasy_pts_estimated', 'pts', 'reb', 'ast']].to_dict('records')

        # Underperformers (lowest variance)
        if 'pts_variance' in merged.columns:
            under = merged[merged['has_real_stats'] == True].nsmallest(10, 'pts_variance')
            report['underperformers'] = under[['player_name', 'team_name', 'pts_variance', 'total_points', 'fantasy_pts_estimated']].to_dict('records')

        # Injured players
        injured = merged[merged['injured'] == True]
        report['injured_players'] = injured[['player_name', 'team_name', 'injuryStatus']].to_dict('records')

        # Save report (optional - skip on read-only file systems)
        try:
            report_dir = Path("data/fantasy/reports")
            report_dir.mkdir(parents=True, exist_ok=True)
            report_file = report_dir / f"daily_report_{target_date}.json"

            import json
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)

            print(f"Success: Daily report generated: {report_file}")
        except Exception:
            print("Note: Could not save report to disk (read-only filesystem)")

    except Exception as e:
        print(f"Error generating report: {e}")
        report['error'] = str(e)

    return report


if __name__ == "__main__":
    # Test merge pipeline
    print("Testing merge pipeline...")
    report = generate_daily_fantasy_report()

    if 'error' not in report:
        print(f"\nDaily Report for {report['date']}")
        print(f"Top Performers: {len(report['top_performers'])}")
        print(f"Underperformers: {len(report['underperformers'])}")
        print(f"Injured: {len(report['injured_players'])}")
