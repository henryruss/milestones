# Milestones

A live website that tracks NBA and NHL players who are close to 
hitting a statistical milestone — points records, goal totals, 
career games played, and more.

Live at [henryruss.github.io/milestones](https://henryruss.github.io/milestones)

## How it works

Python scripts scrape current player stats for both NBA and NHL, 
compare them against milestone thresholds defined in JSON, and 
output a ranked list of players within striking distance of a 
notable achievement.

A GitHub Actions workflow runs the scripts automatically every day 
and commits the updated stats back to the repo. The site always 
reflects current data with zero manual intervention.

## Stack

| Layer | Tech |
|---|---|
| Data | Python (requests, BeautifulSoup) |
| Storage | JSON flat files |
| Frontend | Vanilla HTML/CSS |
| Automation | GitHub Actions (daily cron) |
| Hosting | GitHub Pages |

## Files

- `scan_nba_milestones_json.py` — scrapes and scores NBA players
- `scan_nhl_milestones_json.py` — scrapes and scores NHL players
- `nba_milestones.json` — NBA milestone definitions and thresholds
- `nhl_milestones.json` — NHL milestone definitions and thresholds
- `promote_updates.py` — surfaces the most newsworthy updates
- `index.html` — frontend display
- `.github/workflows/` — daily auto-update Action

## Why

I watch a lot of sports and kept manually checking when players 
were close to milestones. This automates that.
