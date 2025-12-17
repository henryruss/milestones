import os
import time
import json
import requests
import random
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats

# --- CONFIG ---
MILESTONE_STEP = 1000
WITHIN_POINTS = 50 
OUTPUT_FILE = "nba_milestones.json"
API_KEY = os.environ.get('SCRAPERAPI_KEY', '')

def get_proxy_url(url):
    if not API_KEY: return url
    return f"http://api.scraperapi.com?api_key={API_KEY}&url={url}"

def scan_nba():
    print("Starting NBA Smart Scan with Proxy...")
    all_active = players.get_active_players()
    candidates = []

    for i, p in enumerate(all_active):
        pid = p['id']
        name = p['full_name']
        
        if i % 25 == 0: print(f"Checked {i}/{len(all_active)} players...")

        try:
            url = f"https://stats.nba.com/stats/playercareerstats?LeagueID=00&PerMode=Totals&PlayerID={pid}"
            response = requests.get(get_proxy_url(url), timeout=30)
            data = response.json()
            
            rows = data['resultSets'][0]['rowSet']
            total_pts = sum(row[26] for row in rows)

            next_m = ((int(total_pts) // MILESTONE_STEP) + 1) * MILESTONE_STEP
            needed = next_m - total_pts

            if needed <= WITHIN_POINTS:
                print(f"!!! Milestone Alert: {name} needs {int(needed)}")
                
                # UPDATED: More reliable high-res CDN path
                img_url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{pid}.png"
                
                candidates.append({
                    "player_name": name,
                    "player_id": pid,
                    "current_stat": int(total_pts),
                    "target_milestone": next_m,
                    "needed": int(needed),
                    "image_url": img_url,
                    "team": "NBA"
                })
            
            time.sleep(0.2) 

        except Exception:
            continue

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(candidates, f, indent=4)
    print(f"Scan complete. {len(candidates)} found.")

if __name__ == "__main__":
    scan_nba()
