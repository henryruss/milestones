import os
import time
import json
import requests
import random
import urllib.parse 
import concurrent.futures
from nba_api.stats.static import players 

# --- LOAD ENVIRONMENT VARIABLES ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- CONFIG ---
MILESTONE_STEP = 1000
WITHIN_POINTS = 250 
OUTPUT_FILE = "nba_milestones.json"
MAX_WORKERS = 5  
API_KEY = os.environ.get('SCRAPERAPI_KEY', '')

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
            # Added render=true as it sometimes helps with NBA's strict checks
            proxy_url = f"http://api.scraperapi.com?api_key={API_KEY}&url={encoded_url}&keep_headers=true"
            
            # Increased timeout to 30s because proxies can be slow
            response = requests.get(proxy_url, headers=HEADERS, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                print(f"    [!] Proxy Auth Failed (Check Key/Quota). Status: {response.status_code}")
            else:
                print(f"    [!] Proxy Warning: Received status {response.status_code}")
                
        except Exception as e:
            # Print the actual error so we know WHY the proxy failed
            print(f"    [!] Proxy Connection Failed: {str(e)}")

    # 2. Direct Connection Fallback
    # Only runs if proxy failed or no key provided
    if API_KEY:
        print("    [i] Falling back to Direct Connection...")

    try:
        # Add a longer delay for direct requests to avoid "Connection Reset"
        time.sleep(random.uniform(1.0, 2.0)) 
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"    [X] Direct Failed: Status {response.status_code}")
    except Exception as e:
        print(f"    [X] Direct Connection Error: {e}")
    
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
    
    # DEBUG: Check if API Key is loaded
    if API_KEY:
        print(f"[OK] API Key detected: {API_KEY[:4]}...{API_KEY[-4:]}")
    else:
        print("[WARNING] No API Key detected. Using Direct Connection (High risk of blocking).")
        print("          Make sure you have a .env file with SCRAPERAPI_KEY=...")

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
            if completed_count % 5 == 0:
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