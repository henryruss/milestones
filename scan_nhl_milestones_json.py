import os
import time
import json
import requests
import random
import urllib.parse
import concurrent.futures

# --- LOAD ENVIRONMENT VARIABLES ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- CONFIGURATION ---
STAT_TYPE = 'goals'         
MILESTONE_STEP = 100        
WITHIN_RANGE = 15           
MIN_CAREER_STAT = 80        
OUTPUT_FILE = "nhl_milestones.json"
MAX_WORKERS = 10  # Number of concurrent threads
API_KEY = os.environ.get('SCRAPERAPI_KEY', '')

TEAM_ABBREVIATIONS = [
    "ANA", "BOS", "BUF", "CGY", "CAR", "CHI", "COL", "CBJ", "DAL", "DET",
    "EDM", "FLA", "LAK", "MIN", "MTL", "NSH", "NJD", "NYI", "NYR", "OTT",
    "PHI", "PIT", "SJS", "SEA", "STL", "TBL", "TOR", "UTA", "VAN", "VGK", 
    "WSH", "WPG"
]

def get_proxy_url(url):
    if not API_KEY: 
        return url
    encoded_url = urllib.parse.quote(url, safe='')
    return f"http://api.scraperapi.com?api_key={API_KEY}&url={encoded_url}&keep_headers=true"

def process_player(player_tuple):
    """
    Worker function to check a single player's milestones.
    """
    pid, name = player_tuple
    
    try:
        url = f"https://api-web.nhle.com/v1/player/{pid}/landing"
        
        # Tiny random jitter to avoid perfect sync
        time.sleep(random.uniform(0.1, 0.3))
        
        r = requests.get(get_proxy_url(url), timeout=30)
        
        if r.status_code == 200:
            data = r.json()
            career_totals = data.get('careerTotals', {}).get('regularSeason', {})
            career_val = career_totals.get(STAT_TYPE, 0)
            
            # Skip if they aren't close to any major numbers yet
            if career_val < MIN_CAREER_STAT:
                return None

            next_m = ((int(career_val) // MILESTONE_STEP) + 1) * MILESTONE_STEP
            needed = next_m - career_val
            
            if needed <= WITHIN_RANGE:
                # --- IMAGE URL FIX ---
                # 1. Try to get the official URL directly from the API response
                img_url = data.get('headshot', '')
                
                # 2. If missing, fallback to the legacy BAMGrid server (Most reliable fallback)
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
        # Silently fail on connection errors to keep threaded output clean
        return None
        
    return None

def scan_nhl():
    print(f"--- NHL PROXY SCANNER (MULTI-THREADED) ---")
    if not API_KEY:
        print("FATAL: SCRAPERAPI_KEY not found.")
        print("TIP: Create a .env file with 'SCRAPERAPI_KEY=your_key'.")
        return
    else:
         print(f"API Key loaded: {API_KEY[:4]}...{API_KEY[-4:]}")

    active_player_ids = set()
    candidates = []

    print("Fetching active rosters (Synchronous)...")
    # We keep roster fetching synchronous as it's only 32 requests and fast enough
    for i, team in enumerate(TEAM_ABBREVIATIONS):
        try:
            print(f"  Fetching {team} ({i+1}/{len(TEAM_ABBREVIATIONS)})...", end='\r')
            url = f"https://api-web.nhle.com/v1/roster/{team}/current"
            r = requests.get(get_proxy_url(url), timeout=30)
            if r.status_code == 200:
                data = r.json()
                for group in ['forwards', 'defensemen', 'goalies']:
                    for player in data.get(group, []):
                        full_name = f"{player['firstName']['default']} {player['lastName']['default']}"
                        active_player_ids.add((player['id'], full_name))
            time.sleep(0.2)
        except Exception:
            continue
    print(f"\nFound {len(active_player_ids)} active players.")

    player_list = list(active_player_ids)
    print(f"Starting detailed scan with {MAX_WORKERS} concurrent threads...")

    completed_count = 0

    # Threaded Scanning
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_player = {executor.submit(process_player, p): p for p in player_list}
        
        for future in concurrent.futures.as_completed(future_to_player):
            player_tuple = future_to_player[future]
            completed_count += 1
            
            if completed_count % 25 == 0: 
                print(f"  Progress: {completed_count}/{len(player_list)} checked...")

            try:
                result = future.result()
                if result:
                    print(f"    [!] ALERT: {result['player_name']} needs {result['needed']} {STAT_TYPE}")
                    candidates.append(result)
            except Exception as exc:
                pass

    # Save Results
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(candidates, f, indent=4)
    print(f"SUCCESS: Saved {len(candidates)} NHL candidates to {OUTPUT_FILE}")

if __name__ == "__main__":
    scan_nhl()