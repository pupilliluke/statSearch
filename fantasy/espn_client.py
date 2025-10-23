"""
ESPN Fantasy Basketball Client
Authenticated connector to ESPN Fantasy API endpoints
"""

from typing import List, Dict, Optional
import os


class ESPNClient:
    """
    Wrapper around espn-api library for Fantasy Basketball

    Requires:
        - ESPN_S2 cookie
        - SWID cookie
        - League ID
        - Year
    """

    def __init__(self, league_id: int, year: int, espn_s2: str, swid: str):
        """
        Initialize ESPN Fantasy client

        Args:
            league_id: ESPN Fantasy league ID
            year: Fantasy season year (e.g., 2025)
            espn_s2: ESPN authentication cookie
            swid: ESPN SWID cookie (include {} brackets)
        """
        try:
            from espn_api.basketball import League
            self.league = League(
                league_id=league_id,
                year=year,
                espn_s2=espn_s2,
                swid=swid
            )
            self.league_id = league_id
            self.year = year
        except ImportError:
            raise ImportError("espn-api not installed. Run: pip install espn-api")
        except Exception as e:
            raise Exception(f"Failed to connect to ESPN Fantasy: {str(e)}")

    def get_teams(self) -> List[Dict]:
        """
        Get all teams in the league

        Returns:
            List of team dictionaries with id, name, wins, losses
        """
        teams = []
        for team in self.league.teams:
            teams.append({
                "team_id": team.team_id,
                "team_name": team.team_name,
                "owner": getattr(team, 'owner', 'Unknown'),
                "wins": team.wins,
                "losses": team.losses,
                "points_for": getattr(team, 'points_for', 0),
                "points_against": getattr(team, 'points_against', 0)
            })
        return teams

    def get_rosters(self) -> List[Dict]:
        """
        Get all player rosters across all teams

        Returns:
            List of roster entries with team, player, position, stats
        """
        rosters = []
        for team in self.league.teams:
            for player in team.roster:
                rosters.append({
                    "team_id": team.team_id,
                    "team_name": team.team_name,
                    "player_name": player.name,
                    "position": getattr(player, 'position', 'N/A'),
                    "pro_team": getattr(player, 'proTeam', 'N/A'),
                    "total_points": getattr(player, 'total_points', 0),
                    "avg_points": getattr(player, 'avg_points', 0),
                    "injured": getattr(player, 'injured', False),
                    "injuryStatus": getattr(player, 'injuryStatus', None)
                })
        return rosters

    def get_matchups(self, week: Optional[int] = None) -> List[Dict]:
        """
        Get current week's matchups

        Args:
            week: Specific week number (defaults to current week)

        Returns:
            List of matchup dictionaries
        """
        matchups = []
        try:
            scoreboard = self.league.scoreboard(matchup_period=week) if week else self.league.scoreboard()

            for matchup in scoreboard:
                matchups.append({
                    "home_team": matchup.home_team.team_name,
                    "home_team_id": matchup.home_team.team_id,
                    "away_team": matchup.away_team.team_name,
                    "away_team_id": matchup.away_team.team_id,
                    "home_score": matchup.home_score,
                    "away_score": matchup.away_score,
                    "week": week or self.league.current_week
                })
        except Exception as e:
            print(f"Warning: Could not fetch matchups: {e}")

        return matchups

    def get_league_settings(self) -> Dict:
        """
        Get league settings and configuration

        Returns:
            Dictionary of league settings
        """
        return {
            "league_id": self.league_id,
            "name": self.league.settings.name,
            "year": self.year,
            "team_count": self.league.settings.team_count,
            "reg_season_count": getattr(self.league.settings, 'reg_season_count', None),
            "playoff_team_count": getattr(self.league.settings, 'playoff_team_count', None),
            "current_week": self.league.current_week
        }

    def get_free_agents(self, size: int = 50) -> List[Dict]:
        """
        Get top free agents available

        Args:
            size: Number of free agents to return

        Returns:
            List of available players
        """
        free_agents = []
        try:
            fa_list = self.league.free_agents(size=size)
            for player in fa_list:
                free_agents.append({
                    "player_name": player.name,
                    "position": getattr(player, 'position', 'N/A'),
                    "pro_team": getattr(player, 'proTeam', 'N/A'),
                    "total_points": getattr(player, 'total_points', 0),
                    "avg_points": getattr(player, 'avg_points', 0),
                    "percent_owned": getattr(player, 'percent_owned', 0)
                })
        except Exception as e:
            print(f"Warning: Could not fetch free agents: {e}")

        return free_agents


def create_client_from_env() -> ESPNClient:
    """
    Create ESPN client from environment variables

    Required env vars:
        - ESPN_S2
        - SWID
        - LEAGUE_ID
        - FANTASY_YEAR

    Returns:
        Configured ESPNClient instance
    """
    from dotenv import load_dotenv
    load_dotenv()

    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")
    league_id = os.getenv("LEAGUE_ID")
    year = os.getenv("FANTASY_YEAR")

    if not all([espn_s2, swid, league_id, year]):
        raise ValueError(
            "Missing required environment variables. "
            "Please set ESPN_S2, SWID, LEAGUE_ID, and FANTASY_YEAR in .env file"
        )

    return ESPNClient(
        league_id=int(league_id),
        year=int(year),
        espn_s2=espn_s2,
        swid=swid
    )


if __name__ == "__main__":
    # Test client
    try:
        client = create_client_from_env()
        settings = client.get_league_settings()
        print(f"Connected to league: {settings['name']}")
        print(f"Teams: {settings['team_count']}")
        print(f"Current week: {settings['current_week']}")

        teams = client.get_teams()
        print(f"\nFetched {len(teams)} teams")

        rosters = client.get_rosters()
        print(f"Fetched {len(rosters)} roster entries")

    except Exception as e:
        print(f"Error: {e}")
