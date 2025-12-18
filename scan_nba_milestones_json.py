import os
import time
import json
import requests
import random
import urllib.parse 
import concurrent.futures
from nba_api.stats.static import players 

# --- CONFIG ---
MILESTONE_STEP = 1000
WITHIN_POINTS = 250 
OUTPUT_FILE = "nba_milestones.json"
MAX_WORKERS = 5  # Reduced to 5 for GitHub Actions stability
API_KEY = os.environ.get('SCRAPERAPI_KEY', '')

# Headers are critical for direct connections
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Connection": "keep-alive"
}

def fetch_url(url):
    """
    Attempts to fetch data using Proxy first, then Direct connection as fallback.
    """
    # 1. Try with Proxy (if Key exists)
    if API_KEY:
        try:
            encoded_url = urllib.parse.quote(url, safe='')
            proxy_url = f"http://api.scraperapi.com?api_key={API_KEY}&url={encoded_url}&keep_headers=true"
            response = requests.get(proxy_url, headers=HEADERS, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                print(f"    [!] Proxy Auth Failed (Check Key/Quota). Switching to Direct...")
        except Exception as e:
            # Proxy failed, just proceed to direct
            pass

    # 2. Direct Connection Fallback
    try:
        # Add a small delay for direct requests to be polite
        time.sleep(random.uniform(0.5, 1.5)) 
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"    [X] Direct Failed: {response.status_code}")
    except Exception as e:
        print(f"    [X] Connection Error: {e}")
    
    return None

def process_player(p):
    pid = p['id']
    name = p['full_name']
    
    # Stats endpoint
    url = f"https://stats.nba.com/stats/playercareerstats?LeagueID=00&PerMode=Totals&PlayerID={pid}"
    
    data = fetch_url(url)
    
    if not data:
        return None

    try:
        # RowSet[0] is SeasonTotalsRegularSeason
        result_sets = data.get('resultSets', [])
        if not result_sets: return None
            
        rows = result_sets[0]['rowSet']
        if not rows: return None
            
        total_pts = sum(row[26] for row in rows) # Index 26 is PTS

        if total_pts == 0: return None

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
    except Exception:
        return None
    
    return None

def scan_nba():
    print(f"--- NBA DUAL-MODE SCANNER ---")
    
    # STEP 1: Get Player List
    print("Loading active player list...")
    try:
        all_players = players.get_active_players()
        print(f"Found {len(all_players)} active players.")
    except Exception as e:
        print(f"FATAL: Could not load player list. {e}")
        return

    candidates = []
    completed_count = 0

    # STEP 2: Scan
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_player = {executor.submit(process_player, p): p for p in all_players}
        
        for future in concurrent.futures.as_completed(future_to_player):
            completed_count += 1
            if completed_count % 10 == 0:
                print(f"  Progress: {completed_count}/{len(all_players)} checked...", end='\r')

            try:
                result = future.result()
                if result:
                    print(f"\n    [!] ALERT: {result['player_name']} needs {result['needed']}")
                    candidates.append(result)
            except Exception:
                pass

    # Save results
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(candidates, f, indent=4)
    print(f"\nSUCCESS: Saved {len(candidates)} players to {OUTPUT_FILE}")

if __name__ == "__main__":
    scan_nba()