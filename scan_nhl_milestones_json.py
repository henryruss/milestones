import os
import time
import json
import requests
import random

# --- CONFIGURATION ---
STAT_TYPE = 'goals'         
MILESTONE_STEP = 100        
WITHIN_RANGE = 15           
MIN_CAREER_STAT = 80        
OUTPUT_FILE = "nhl_milestones.json"
API_KEY = os.environ.get('SCRAPERAPI_KEY', '')

TEAM_ABBREVIATIONS = [
    "ANA", "BOS", "BUF", "CGY", "CAR", "CHI", "COL", "CBJ", "DAL", "DET",
    "EDM", "FLA", "LAK", "MIN", "MTL", "NSH", "NJD", "NYI", "NYR", "OTT",
    "PHI", "PIT", "SJS", "SEA", "STL", "TBL", "TOR", "UTA", "VAN", "VGK", 
    "WSH", "WPG"
]

def get_proxy_url(url):
    """Wraps the URL with ScraperAPI to bypass IP blocks."""
    if not API_KEY:
        return url
    return f"http://api.scraperapi.com?api_key={API_KEY}&url={url}"

def scan_nhl():
    print(f"--- NHL PROXY SCANNER ---")
    active_player_ids = set()
    candidates = []

    # 1. Build Roster List (Using Proxy)
    print("Fetching active rosters...")
    for team in TEAM_ABBREVIATIONS:
        try:
            url = f"https://api-web.nhle.com/v1/roster/{team}/current"
            r = requests.get(get_proxy_url(url), timeout=30)
            if r.status_code == 200:
                data = r.json()
                for group in ['forwards', 'defensemen', 'goalies']:
                    for player in data.get(group, []):
                        full_name = f"{player['firstName']['default']} {player['lastName']['default']}"
                        active_player_ids.add((player['id'], full_name))
            time.sleep(0.1) # Small gap to be polite to the proxy
        except Exception as e:
            print(f"Error fetching roster for {team}: {e}")
            
    player_list = list(active_player_ids)
    print(f"Scanning {len(player_list)} players...")

    # 2. Scan Individual Players
    for i, (pid, name) in enumerate(player_list):
        if i % 25 == 0: print(f"Checked {i}/{len(player_list)} players...")
            
        try:
            url = f"https://api-web.nhle.com/v1/player/{pid}/landing"
            r = requests.get(get_proxy_url(url), timeout=30)
            
            if r.status_code == 200:
                data = r.json()
                career_totals = data.get('careerTotals', {}).get('regularSeason', {})
                career_val = career_totals.get(STAT_TYPE, 0)
                
                if career_val < MIN_CAREER_STAT:
                    continue

                next_m = ((int(career_val) // MILESTONE_STEP) + 1) * MILESTONE_STEP
                needed = next_m - career_val
                
                if needed <= WITHIN_RANGE:
                    print(f"!!! Milestone Alert: {name} needs {int(needed)}")
                    
                    # NHL Headshot CDN URL (Direct and Free)
                    img_url = f"https://img.nhl.com/images/headshots/current/168x168/{pid}.png"
                    
                    candidates.append({
                        "player_name": name,
                        "player_id": pid,
                        "team": data.get('currentTeamAbbrev', 'NHL'),
                        "current_stat": int(career_val),
                        "target_milestone": next_m,
                        "needed": int(needed),
                        "image_url": img_url,
                        "stat_type": STAT_TYPE
                    })
            
            time.sleep(0.1)
            
        except Exception:
            continue

    # Save to JSON for the website
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(candidates, f, indent=4)
    print(f"Saved {len(candidates)} NHL candidates.")

if __name__ == "__main__":
    scan_nhl()
