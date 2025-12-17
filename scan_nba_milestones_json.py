import os
import time
import json
import requests
import random
import urllib.parse 
import concurrent.futures
from nba_api.stats.static import players 

# --- LOAD ENVIRONMENT VARIABLES ---
# This block allows you to use a .env file locally
# IF PIP FAILS: Try running "python3 -m pip install python-dotenv"
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- CONFIG ---
MILESTONE_STEP = 1000
WITHIN_POINTS = 250 
OUTPUT_FILE = "nba_milestones.json"
MAX_WORKERS = 10  # Number of simultaneous requests
API_KEY = os.environ.get('SCRAPERAPI_KEY', '')

# Headers are now global so the worker threads can access them
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Connection": "keep-alive"
}

def get_proxy_url(url):
    if not API_KEY: 
        return url
    encoded_url = urllib.parse.quote(url, safe='')
    return f"http://api.scraperapi.com?api_key={API_KEY}&url={encoded_url}&keep_headers=true"

def process_player(p):
    """
    Worker function to process a single player.
    Returns a candidate dictionary if a milestone is near, else None.
    """
    pid = p['id']
    name = p['full_name']
    
    try:
        # Stats endpoint
        url = f"https://stats.nba.com/stats/playercareerstats?LeagueID=00&PerMode=Totals&PlayerID={pid}"
        
        # We don't need a heavy sleep here anymore because the proxy rotates IPs,
        # but a tiny jitter prevents local network congestion.
        time.sleep(random.uniform(0.1, 0.3))

        response = requests.get(get_proxy_url(url), headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            return None # Fail silently to keep output clean, or log if needed
            
        try:
            stats_data = response.json()
        except Exception:
            return None

        # RowSet[0] is SeasonTotalsRegularSeason
        result_sets = stats_data.get('resultSets', [])
        if not result_sets:
            return None
            
        rows = result_sets[0]['rowSet']
        if not rows:
            return None
            
        total_pts = sum(row[26] for row in rows) # Index 26 is PTS

        if total_pts == 0: 
            return None

        next_m = ((int(total_pts) // MILESTONE_STEP) + 1) * MILESTONE_STEP
        needed = next_m - total_pts

        if needed <= WITHIN_POINTS:
            img_url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{pid}.png"
            return {
                "player_name": name,
                "player_id": pid,
                "current_stat": int(total_pts),
                "target_milestone": next_m,
                "needed": int(needed),
                "image_url": img_url,
                "team": "NBA" 
            }
            
    except Exception as e:
        # Connection errors are common with proxies, just skip
        return None
    
    return None

def scan_nba():
    print(f"--- NBA PROXY SCANNER (MULTI-THREADED) ---")
    
    if not API_KEY:
        print("FATAL: SCRAPERAPI_KEY not found.")
        print("TIP: Create a .env file with 'SCRAPERAPI_KEY=your_key' or set it in your terminal.")
        return
    else:
        print(f"API Key loaded: {API_KEY[:4]}...{API_KEY[-4:]}")

    # STEP 1: Get Player List LOCALLY
    print("Loading active player list from local database...")
    all_players = players.get_active_players()
    print(f"Found {len(all_players)} active players.")
    print(f"Starting scan with {MAX_WORKERS} concurrent threads...")

    candidates = []
    completed_count = 0

    # STEP 2: Scan for stats using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_player = {executor.submit(process_player, p): p for p in all_players}
        
        # Process as they complete
        for future in concurrent.futures.as_completed(future_to_player):
            player = future_to_player[future]
            completed_count += 1
            
            # Progress bar every 10 players
            if completed_count % 10 == 0:
                print(f"  Progress: {completed_count}/{len(all_players)} checked...")

            try:
                result = future.result()
                if result:
                    print(f"    [!] ALERT: {result['player_name']} needs {result['needed']} for {result['target_milestone']}")
                    candidates.append(result)
            except Exception as exc:
                print(f"    [!] Exception for {player['full_name']}: {exc}")

    # Save results
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(candidates, f, indent=4)
    print(f"SUCCESS: Saved {len(candidates)} players to {OUTPUT_FILE}")

if __name__ == "__main__":
    scan_nba()