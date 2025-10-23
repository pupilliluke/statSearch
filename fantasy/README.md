# ESPN Fantasy Basketball Integration

Complete ESPN Fantasy Basketball integration for Luke's NBA Stats Tracker.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install espn-api python-dotenv
```

### 2. Get ESPN Cookies

1. Log into [fantasy.espn.com](https://fantasy.espn.com)
2. Open Developer Tools (F12)
3. Go to **Application** → **Cookies** → `https://fantasy.espn.com`
4. Copy these two values:
   - `espn_s2` (long string)
   - `SWID` (format: `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}`)

### 3. Configure Environment

Create a `.env` file in the project root:

```env
ESPN_S2=your_espn_s2_cookie_value_here
SWID={your-swid-value-here-with-brackets}
LEAGUE_ID=123456
FANTASY_YEAR=2025
```

**IMPORTANT:** Never commit `.env` to git!

### 4. Test Connection

```bash
python -m fantasy.espn_client
```

You should see your league name and team count.

### 5. Sync Fantasy Data

```bash
python -m fantasy.fantasy_sync
```

This will fetch and save:
- Teams and standings
- Player rosters
- Current matchups
- Top free agents

Data is saved to `data/fantasy/YYYY-MM-DD/`

## API Endpoints

### Manual Sync
```
POST /api/fantasy/sync
```

### Get Teams
```
GET /api/fantasy/teams
```

### Get Rosters
```
GET /api/fantasy/rosters
```

### Get Matchups
```
GET /api/fantasy/matchups
```

### Get Daily Report (with real stats)
```
GET /api/fantasy/report?date=2025-10-22
```

## Features

✅ **League Standings** - Win/Loss records, points for/against
✅ **Live Matchups** - Current week scores
✅ **Roster Management** - View all team rosters
✅ **Injury Tracking** - Highlighted injured players
✅ **Real Stats Integration** - Merge with actual box scores
✅ **Fantasy Points Calculation** - Estimate based on real performance
✅ **Daily Reports** - Top performers, underperformers, recommendations

## File Structure

```
fantasy/
├── __init__.py
├── espn_client.py         # ESPN API wrapper
├── fantasy_sync.py        # Data sync service
├── merge_pipeline.py      # Merge with real box scores
└── README.md

data/fantasy/YYYY-MM-DD/
├── teams.csv
├── rosters.csv
├── matchups.csv
├── free_agents.csv
└── league_settings.json
```

## Automation

### Daily Sync (Cron)

Add to crontab:
```cron
0 8 * * * cd /path/to/NbaStatTracker && python -m fantasy.fantasy_sync
```

### Hourly During Live Games
```cron
0 19-23 * * * cd /path/to/NbaStatTracker && python -m fantasy.fantasy_sync
```

## Troubleshooting

**"ModuleNotFoundError: No module named 'espn_api'"**
- Run: `pip install espn-api`

**"Failed to connect to ESPN Fantasy"**
- Check your `espn_s2` and `SWID` cookies are correct
- Make sure cookies haven't expired (re-login to ESPN)
- Verify `LEAGUE_ID` is correct

**"No fantasy data available"**
- Run sync first: `python -m fantasy.fantasy_sync`
- Check `data/fantasy/` directory exists

## Legal Notes

- ESPN Fantasy API is unofficial and may change
- Use for personal/internal analytics only
- Do not resell or redistribute ESPN data
- Keep cookies private and secure
- Respect ESPN Terms of Use and rate limits

## Support

For issues or questions, check:
- [espn-api documentation](https://github.com/cwendt94/espn-api)
- Project issues on GitHub
