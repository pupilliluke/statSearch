# NBA Stat Tracker - Deployment Options for Vercel Timeout Issue

## Current Status
✅ **Scraper works correctly** - No bugs, properly structured for Vercel
❌ **Hitting Vercel Free tier 10-second timeout** - Scraper needs ~15-20 seconds to complete

## Root Cause
The scraper fetches box scores for multiple games with rate-limiting delays:
- `time.sleep(0.3)` per game in NBA API source
- `time.sleep(0.2)` per game in ESPN API source
- With 10+ games per day, this exceeds Vercel's 10s free tier limit

---

## Option 1: Upgrade to Vercel Pro ⭐ Recommended
**Cost:** $20/month
**Timeout:** 60 seconds (6x more time)
**Pros:**
- Simple - just upgrade your plan
- No code changes needed
- Better performance overall
- More generous resource limits (3GB memory vs 1GB)

**Cons:**
- Monthly cost
- Still has timeout (60s max)

**How to do it:**
1. Go to https://vercel.com/luke-pupillis-projects/settings/billing
2. Upgrade to Pro plan
3. Deploy automatically gets 60s timeout

---

## Option 2: Use Vercel Cron Jobs (Scheduled Pre-fetching)
**Cost:** Free
**Timeout:** 60-900 seconds (Pro/Enterprise)

**How it works:**
- Run scraper on a schedule (e.g., daily at 2 AM)
- Cache results in database or edge storage
- API endpoints serve cached data instantly

**Pros:**
- Free (with limitations)
- Fast API responses (serving cached data)
- More reliable - runs at low-traffic times

**Cons:**
- Requires database setup (Vercel KV, Postgres, etc.)
- Data is not real-time (cached from last run)
- Cron jobs on free tier still have 10s limit (need Pro for 60s)

**Implementation:**
```json
// vercel.json
{
  "crons": [
    {
      "path": "/api/scrape-daily",
      "schedule": "0 2 * * *"  // 2 AM daily
    }
  ]
}
```

---

## Option 3: Deploy to AWS Lambda ⭐ Best Free Option
**Cost:** Free (within AWS Free Tier - 1M requests/month)
**Timeout:** Up to 15 minutes

**Pros:**
- Much longer timeout (900 seconds max)
- Free tier is very generous
- Handles heavy scraping workloads
- Can use AWS DynamoDB for caching

**Cons:**
- More complex setup
- Need to learn AWS deployment
- Slightly higher latency vs Vercel Edge

**How to do it:**
1. Use AWS SAM or Serverless Framework
2. Deploy Flask app as Lambda function
3. Use API Gateway for endpoints
4. Tutorial: https://aws.amazon.com/blogs/compute/build-a-serverless-web-application-using-python/

---

## Option 4: Optimize Scraper Speed (Remove Sleep Delays)
**Cost:** Free
**Risk:** May get rate-limited/blocked by APIs

**Changes needed:**
```python
# In sources/nba_api_source.py
time.sleep(0.3)  # Remove this line

# In sources/espn_api_source.py
time.sleep(0.2)  # Remove this line

# Set MAX_GAMES_PER_REQUEST to limit scope
# In Vercel env vars: MAX_GAMES_PER_REQUEST=5
```

**Pros:**
- Free
- No infrastructure changes
- Might work within 10s limit

**Cons:**
- May violate API rate limits
- Risk of getting IP banned
- Only fetches partial data (5 games max)

---

## Option 5: Hybrid Approach (Vercel + External Scheduler)
**Cost:** Free
**Complexity:** Medium

**How it works:**
1. Use GitHub Actions or external cron service (cron-job.org)
2. Trigger scraper endpoint daily
3. Store results in Vercel KV or external DB
4. API serves cached results

**Pros:**
- Completely free
- Flexible scheduling
- No Vercel timeout issues

**Cons:**
- Requires database setup
- More moving parts
- Data not real-time

**Implementation:**
```yaml
# .github/workflows/daily-scrape.yml
name: Daily NBA Stats Scrape
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger scraper
        run: curl -X POST ${{ secrets.SCRAPER_URL }}/api/scrape-and-cache
```

---

## Option 6: Switch to Different Hosting Platform
**Cost:** Varies (many have free tiers)

**Alternative Platforms:**
- **Railway.app** - $5/month, 500 hours free, no timeout limits
- **Render.com** - Free tier, 15-minute timeout
- **Fly.io** - Free tier, better for long-running tasks
- **DigitalOcean App Platform** - $5/month, no timeout

**Pros:**
- More generous limits than Vercel free tier
- Some designed for backend/scraping workloads
- Often simpler than AWS

**Cons:**
- Need to migrate deployment
- Different deployment process
- May have less generous free tier than Vercel for other features

---

## Recommendation Matrix

| Use Case | Best Option |
|----------|-------------|
| **Need it working NOW** | Option 1 (Vercel Pro) or Option 4 (Remove sleeps) |
| **Budget: $0** | Option 3 (AWS Lambda) or Option 5 (GitHub Actions) |
| **Want simplest solution** | Option 1 (Vercel Pro) |
| **Best free long-term** | Option 3 (AWS Lambda) + DynamoDB |
| **Real-time data required** | Option 1 (Vercel Pro) or Option 3 (AWS Lambda) |
| **Scheduled daily updates OK** | Option 2 or 5 (Cron + Cache) |

---

## Quick Win: Test with Limited Games
Try this RIGHT NOW to see if it works:

1. Set Vercel environment variable: `MAX_GAMES_PER_REQUEST=3`
2. This limits scraper to first 3 games only
3. Should complete within 10 seconds
4. Test: `curl "https://your-app.vercel.app/api/stats?date=2024-10-28&pts=30"`

If this works, you can keep it as a "quick stats" endpoint and implement one of the above options for full scraping.

---

## Current Configuration
- **Platform:** Vercel Free Tier
- **Timeout Limit:** 10 seconds
- **Current Scrape Time:** ~15-20 seconds (11 games)
- **Bottleneck:** `time.sleep()` rate limiting in source files

## Files to Check
- `sources/nba_api_source.py` - Line 48 (sleep 0.3s)
- `sources/espn_api_source.py` - Line 82 (sleep 0.2s)
- `tracker.py` - Main orchestrator
- `vercel.json` - Deployment config
