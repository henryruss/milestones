import os
import time
import json
import requests
import random
import urllib.parse
import concurrent.futures

# --- CONFIGURATION ---
STAT_TYPE = 'goals'         
MILESTONE_STEP = 100        
WITHIN_RANGE = 15           
MIN_CAREER_STAT = 80        
OUTPUT_FILE = "nhl_milestones.json"
MAX_WORKERS = 5 # Reduced for GitHub stability
API_KEY = os.environ.get('SCRAPERAPI_KEY', '')

TEAM_ABBREVIATIONS = [
    "ANA", "BOS", "BUF", "CGY", "CAR", "CHI", "COL", "CBJ", "DAL", "DET",
    "EDM", "FLA", "LAK", "MIN", "MTL", "NSH", "NJD", "NYI", "NYR", "OTT",
    "PHI", "PIT", "SJS", "SEA", "STL", "TBL", "TOR", "UTA", "VAN", "VGK", 
    "WSH", "WPG"
]

def fetch_url(url):
    """
    Attempts to fetch data using Proxy first, then Direct connection as fallback.
    """
    # 1. Try Proxy
    if API_KEY:
        try:
            encoded_url = urllib.parse.quote(url, safe='')
            proxy_url = f"http://api.scraperapi.com?api_key={API_KEY}&url={encoded_url}&keep_headers=true"
            r = requests.get(proxy_url, timeout=15)
            if r.status_code == 200: return r.json()
            elif r.status_code == 403: print("    [!] Proxy Auth Failed. Retrying Direct...")
        except:
            pass

    # 2. Try Direct
    try:
        time.sleep(random.uniform(0.2, 0.5))
        r = requests.get(url, timeout=15)
        if r.status_code == 200: return r.json()
    except:
        pass
    
    return None

def process_player(player_tuple):
    pid, name = player_tuple
    
    url = f"https://api-web.nhle.com/v1/player/{pid}/landing"
    data = fetch_url(url)
    
    if not data: return None
        
    try:
        career_totals = data.get('careerTotals', {}).get('regularSeason', {})
        career_val = career_totals.get(STAT_TYPE, 0)
        
        if career_val < MIN_CAREER_STAT: return None

        next_m = ((int(career_val) // MILESTONE_STEP) + 1) * MILESTONE_STEP
        needed = next_m - career_val
        
        if needed <= WITHIN_RANGE:
            # IMAGE FIX: Try API first, then fallback
            img_url = data.get('headshot', '')
            if not img_url:
                img_url = f"https://cms.nhl.bamgrid.com/images/headshots/current/168x168/{pid}.jpg"
            
            return {
                "player_name": name,
                "player_id": pid,
                "team": data.get('currentTeamAbbrev', 'NHL'),
                "current_stat": int(career_val),
                "target_milestone": next_m,
                "needed": int(needed),
                "image_url": img_url,
                "stat_type": STAT_TYPE
            }
    except Exception:
        return None
        
    return None

def scan_nhl():
    print(f"--- NHL DUAL-MODE SCANNER ---")
    active_player_ids = set()
    candidates = []

    print("Fetching active rosters...")
    for team in TEAM_ABBREVIATIONS:
        # We use fetch_url here too to be safe
        url = f"https://api-web.nhle.com/v1/roster/{team}/current"
        data = fetch_url(url)
        if data:
            for group in ['forwards', 'defensemen', 'goalies']:
                for player in data.get(group, []):
                    full_name = f"{player['firstName']['default']} {player['lastName']['default']}"
                    active_player_ids.add((player['id'], full_name))
            
    player_list = list(active_player_ids)
    print(f"Scanning {len(player_list)} players...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_player = {executor.submit(process_player, p): p for p in player_list}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_player):
            completed += 1
            if completed % 25 == 0: print(f"  Progress: {completed}/{len(player_list)}...", end='\r')
            
            result = future.result()
            if result:
                print(f"\n    [!] ALERT: {result['player_name']} needs {result['needed']}")
                candidates.append(result)

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(candidates, f, indent=4)
    print(f"\nSaved {len(candidates)} NHL candidates.")

if __name__ == "__main__":
    scan_nhl()