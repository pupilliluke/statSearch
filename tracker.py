"""
nba_tracker.py — Multi-source NBA stat tracker (thresholds fixed)
Finds players meeting configurable thresholds (PTS/AST/REB) across sources:
  ESPN → NBA_API → BallDontLie → RapidAPI

Behavior:
- If you pass thresholds (e.g., --pts 40), ONLY those metrics are used.
- If you pass none, defaults to OR of 20 PTS, 5 AST, 7 REB.
- --logic any|all determines how multiple PROVIDED thresholds are combined.
"""

import argparse
import requests
import pandas as pd
from datetime import date, timedelta
from typing import List, Dict, Optional

# ------------------------------- Utilities -------------------------------

def _num(x):
    try:
        return float(x)
    except Exception:
        return 0.0

def qualifies(pts: float, ast: float, reb: float,
              pts_thr: Optional[int], ast_thr: Optional[int], reb_thr: Optional[int],
              logic: str) -> bool:
    """Return True if the stat line meets the provided thresholds.
       If no thresholds are provided, use defaults (20/5/7) with OR logic."""
    checks = []
    if pts_thr is not None:
        checks.append(pts >= pts_thr)
    if ast_thr is not None:
        checks.append(ast >= ast_thr)
    if reb_thr is not None:
        checks.append(reb >= reb_thr)

    if not checks:
        # No thresholds supplied → use defaults (OR)
        return (pts >= 20) or (ast >= 5) or (reb >= 7)

    return any(checks) if logic == "any" else all(checks)

# ------------------------------- ESPN -------------------------------

def fetch_from_espn(date_str: str, pts_thr, ast_thr, reb_thr, logic) -> List[Dict]:
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    try:
        games = requests.get(url, timeout=10).json().get("events", [])
    except Exception:
        return []
    players = []
    for g in games:
        gid = g.get("id")
        if not gid:
            continue
        for endpoint in ["summary", "boxscore"]:
            try:
                u = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/{endpoint}?event={gid}"
                box = requests.get(u, timeout=10).json().get("boxscore", {})
                if not box:
                    continue
                players += _parse_espn_box(box, pts_thr, ast_thr, reb_thr, logic)
            except Exception:
                continue
    return players

def _parse_espn_box(box, pts_thr, ast_thr, reb_thr, logic):
    out = []
    for container in box.get("teams", []) + box.get("players", []):
        team = container.get("team", {}).get("displayName", "")
        for group in container.get("statistics", []):
            for a in group.get("athletes", []):
                stats = {s.get("name"): s.get("displayValue") for s in a.get("stats", [])}
                pts = _num(stats.get("points") or stats.get("PTS"))
                ast = _num(stats.get("assists") or stats.get("AST"))
                reb = _num(stats.get("rebounds") or stats.get("REB"))
                if qualifies(pts, ast, reb, pts_thr, ast_thr, reb_thr, logic):
                    out.append({
                        "Player": a.get("athlete", {}).get("displayName"),
                        "Team": team,
                        "PTS": pts, "REB": reb, "AST": ast
                    })
    return out

# ------------------------------- NBA API -------------------------------

def fetch_from_nba_api(target_date: str, pts_thr, ast_thr, reb_thr, logic) -> List[Dict]:
    try:
        from nba_api.stats.endpoints import scoreboardv2, boxscoretraditionalv2
    except ImportError:
        return []
    try:
        sb = scoreboardv2.ScoreboardV2(game_date=target_date, day_offset=0)
        games = sb.get_data_frames()[0]
    except Exception:
        return []
    all_players = []
    for gid in games["GAME_ID"].unique():
        try:
            box = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=gid)
            df = box.get_data_frames()[0]
            df = df[["PLAYER_NAME", "TEAM_ABBREVIATION", "PTS", "REB", "AST"]]
            # Filter row-by-row using our qualifies() logic (because thresholds may be partially specified)
            for _, r in df.iterrows():
                pts, reb, ast = float(r["PTS"]), float(r["REB"]), float(r["AST"])
                if qualifies(pts, ast, reb, pts_thr, ast_thr, reb_thr, logic):
                    all_players.append({
                        "Player": r["PLAYER_NAME"],
                        "Team": r["TEAM_ABBREVIATION"],
                        "PTS": pts, "REB": reb, "AST": ast
                    })
        except Exception:
            continue
    return all_players

# ------------------------------- BallDontLie -------------------------------

def fetch_from_bdl(target_date: str, pts_thr, ast_thr, reb_thr, logic) -> List[Dict]:
    url = f"https://api.balldontlie.io/v1/stats?dates[]={target_date}&per_page=100"
    try:
        r = requests.get(url, timeout=10)
        data = r.json().get("data", [])
    except Exception:
        return []
    out = []
    for p in data:
        pts, ast, reb = float(p["pts"]), float(p["ast"]), float(p["reb"])
        if qualifies(pts, ast, reb, pts_thr, ast_thr, reb_thr, logic):
            out.append({
                "Player": f"{p['player']['first_name']} {p['player']['last_name']}",
                "Team": p["team"]["abbreviation"],
                "PTS": pts, "REB": reb, "AST": ast
            })
    return out

# ------------------------------- RapidAPI (stub) -------------------------------

def fetch_from_rapidapi(target_date: str, pts_thr, ast_thr, reb_thr, logic, api_key: str = None) -> List[Dict]:
    if not api_key:
        return []
    # Implement if you plan to use RapidAPI boxscore endpoints.
    return []

# ------------------------------- Orchestrator -------------------------------

def get_all_stats(target_date: str, pts_thr, ast_thr, reb_thr, logic):
    sources = [
        ("ESPN", lambda: fetch_from_espn(target_date.replace("-", ""), pts_thr, ast_thr, reb_thr, logic)),
        ("NBAAPI", lambda: fetch_from_nba_api(target_date, pts_thr, ast_thr, reb_thr, logic)),
        ("BALLDONTLIE", lambda: fetch_from_bdl(target_date, pts_thr, ast_thr, reb_thr, logic)),
        ("RAPIDAPI", lambda: fetch_from_rapidapi(target_date, pts_thr, ast_thr, reb_thr, logic))
    ]
    for name, func in sources:
        print(f"🔍 Trying {name} for {target_date} ...")
        data = func()
        if data:
            print(f"✅ {name} returned {len(data)} players")
            return data, name
        print(f"⚠️  No data from {name}")
    print("❌ No data from any source.")
    return [], None

# ------------------------------- Main -------------------------------

def main():
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser(description="Multi-source NBA stat tracker")
    parser.add_argument("--date", type=str, help="Date (YYYY-MM-DD), default today")
    parser.add_argument("--pts", type=int, default=None, help="Points threshold (omit to ignore)")
    parser.add_argument("--ast", type=int, default=None, help="Assists threshold (omit to ignore)")
    parser.add_argument("--reb", type=int, default=None, help="Rebounds threshold (omit to ignore)")
    parser.add_argument("--logic", choices=["any", "all"], default="any",
                        help="Combine PROVIDED thresholds with 'any' (default) or 'all'")
    args = parser.parse_args()

    # Build a readable summary of what’s applied
    applied = []
    if args.pts is not None: applied.append(f"{args.pts}+ PTS")
    if args.ast is not None: applied.append(f"{args.ast}+ AST")
    if args.reb is not None: applied.append(f"{args.reb}+ REB")
    if not applied:
        applied = ["20+ PTS", "5+ AST", "7+ REB (defaults, any)"]
    summary = ", ".join(applied)
    print(f"\n📊 Using thresholds ({args.logic} of provided): {summary}\n")

    today = date.today()
    target = args.date if args.date else today.strftime("%Y-%m-%d")

    players, source = get_all_stats(target, args.pts, args.ast, args.reb, args.logic)
    if not players and not args.date:
        # fallback to yesterday only if user didn't force a date
        yday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        print(f"🔁 Trying yesterday ({yday}) ...")
        players, source = get_all_stats(yday, args.pts, args.ast, args.reb, args.logic)
        target = yday

    if not players:
        print("\n⚠️  Still no qualifying players found.\n")
        return

    df = pd.DataFrame(players).drop_duplicates()
    # Sort primarily by provided metrics (pts > ast > reb). If you only provided pts, that dominates.
    sort_keys = []
    if args.pts is not None: sort_keys.append("PTS")
    if args.ast is not None: sort_keys.append("AST")
    if args.reb is not None: sort_keys.append("REB")
    if not sort_keys:
        sort_keys = ["PTS", "AST", "REB"]
    df = df.sort_values(by=sort_keys, ascending=False)

    print(f"\n✅ Qualified Players from {source}:\n")
    print(df.to_string(index=False))

    suffix = source or "UNKNOWN"
    csv_name = f"nba_thresholds_{target}_{suffix}.csv"
    df.to_csv(csv_name, index=False)
    print(f"\n💾 Saved results to {csv_name}\n")

if __name__ == "__main__":
    main()
