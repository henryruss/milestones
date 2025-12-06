import time
import pandas as pd
import json
import random # Added for randomized sleep intervals
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats, commonplayerinfo
# Import custom NBAStatsHTTP wrapper for headers
from nba_api.stats.library.http import NBAStatsHTTP

# --- CONFIGURATION ---
MILESTONE_STEP = 1000       # Look for 1k, 5k, 10k, 25k etc.
WITHIN_POINTS = 250         # Alert if they are this close
MIN_CAREER_PTS = 3000       # Skip rookies/bench players to speed up scan
OUTPUT_FILE = "nba_milestones.json"

# --- CRITICAL FIX: INCREASE DELAY & RANDOMIZE ---
# Baseline sleep time to ensure stability (slightly higher than NHL)
SLEEP_TIME = 1.25 
# ---------------------

# Trick the API into thinking we are a browser (Necessary for GitHub Actions)
NBAStatsHTTP.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

def get_team_abbrev(player_id):
    """Fetches the current team for a player (only called for candidates)."""
    try:
        # Note: Added a micro-sleep here to break up rapid commonplayerinfo calls
        time.sleep(random.uniform(0.1, 0.3)) 
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        df = info.get_data_frames()[0]
        return df['TEAM_ABBREVIATION'].iloc[0]
    except:
        return "N/A"

def scan_nba_active_players():
    print(f"--- NBA MILESTONE SCANNER (JSON MODE) ---")
    print(f"Target: Players within {WITHIN_POINTS} pts of a {MILESTONE_STEP} pt mark.")
    
    # 1. Get all active players
    print("Fetching active player list...")
    active_players = players.get_active_players()
    print(f"Found {len(active_players)} active players. Starting scan...")
    
    player_list = active_players
    
    # Expected runtime will increase slightly with the longer sleep time
    expected_time = len(player_list) * SLEEP_TIME / 60
    print(f"Expected scan time: Approx. {expected_time:.1f} minutes.")

    candidates = []
    
    # 2. Loop through players
    for i, p in enumerate(player_list):
        pid = p['id']
        name = p['full_name']
        
        # Progress indicator every 20 players
        if i % 20 == 0:
            print(f"  Scanning... {i}/{len(player_list)} ({name})")

        try:
            # Fetch Career Stats
            career = playercareerstats.PlayerCareerStats(player_id=pid)
            df = career.get_data_frames()[0]
            
            total_points = df['PTS'].sum()
            
            if total_points < MIN_CAREER_PTS:
                # Add jitter for low-stat players too
                time.sleep(SLEEP_TIME + random.uniform(0.1, 0.5))
                continue

            # 3. Check Math
            next_milestone = ((int(total_points) // MILESTONE_STEP) + 1) * MILESTONE_STEP
            needed = next_milestone - total_points
            
            if needed <= WITHIN_POINTS:
                print(f"  [!] MATCH: {name} (Needs {int(needed)})")
                
                # Fetch team only for matches to save API calls
                team = get_team_abbrev(pid)
                
                candidates.append({
                    "player_name": name,
                    "team": team,
                    "current_stat": int(total_points),
                    "target_milestone": next_milestone,
                    "needed": int(needed),
                    "stat_type": "points"
                })

            # Polite Rate Limiting with Jitter
            time.sleep(SLEEP_TIME + random.uniform(0.1, 0.5))

        except Exception as e:
            # If any specific player fails, take a long nap
            print(f"CRITICAL API FAILURE for {name}. Taking a 30 second nap...")
            time.sleep(30)
            continue


    # 4. Save to JSON
    if candidates:
        # Sort by proximity
        candidates.sort(key=lambda x: x['needed'])
        
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(candidates, f, indent=4)
        print(f"\n[SUCCESS] Saved {len(candidates)} players to '{OUTPUT_FILE}'")
    else:
        print("No players found within range.")
        with open(OUTPUT_FILE, 'w') as f:
            json.dump([], f)

if __name__ == "__main__":
    scan_nba_active_players()
