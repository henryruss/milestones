import requests
import pandas as pd
import time
import json  # Import JSON library

# --- CONFIGURATION ---
STAT_TYPE = 'goals'         # OPTIONS: 'goals', 'points', 'assists'
MILESTONE_STEP = 100        # Increment (e.g., 100 goals, 1000 points)
WITHIN_RANGE = 15           # Alert if within this range
MIN_CAREER_STAT = 80        # Filter out rookies
OUTPUT_FILE = "nhl_milestones.json" # Changing to JSON
# ---------------------

TEAM_ABBREVIATIONS = [
    "ANA", "BOS", "BUF", "CGY", "CAR", "CHI", "COL", "CBJ", "DAL", "DET",
    "EDM", "FLA", "LAK", "MIN", "MTL", "NSH", "NJD", "NYI", "NYR", "OTT",
    "PHI", "PIT", "SJS", "SEA", "STL", "TBL", "TOR", "UTA", "VAN", "VGK", 
    "WSH", "WPG"
]

def scan_nhl_active_players():
    print(f"--- NHL MILESTONE SCANNER (JSON MODE) ---")
    
    active_player_ids = set()
    candidates = []

    # 1. Build Roster List
    print("Fetching active rosters...")
    for team in TEAM_ABBREVIATIONS:
        try:
            url = f"https://api-web.nhle.com/v1/roster/{team}/current"
            r = requests.get(url)
            if r.status_code == 200:
                data = r.json()
                for group in ['forwards', 'defensemen', 'goalies']:
                    for player in data.get(group, []):
                        full_name = player['firstName']['default'] + " " + player['lastName']['default']
                        active_player_ids.add((player['id'], full_name))
        except Exception:
            pass
            
    print(f"Found {len(active_player_ids)} active players. Fetching career stats...")
    
    player_list = list(active_player_ids)
    
    for i, (pid, name) in enumerate(player_list):
        if i % 50 == 0:
            print(f"  Scanning... {i}/{len(player_list)}")
            
        try:
            url = f"https://api-web.nhle.com/v1/player/{pid}/landing"
            r = requests.get(url)
            
            if r.status_code == 200:
                data = r.json()
                
                # Use official Career Totals
                career_totals = data.get('careerTotals', {}).get('regularSeason', {})
                
                if career_totals and STAT_TYPE in career_totals:
                    career_val = career_totals.get(STAT_TYPE, 0)
                else:
                    season_totals = data.get('seasonTotals', [])
                    career_val = 0
                    for season in season_totals:
                        if season.get('leagueAbbrev') == 'NHL' and season.get('gameTypeId') == 2:
                            career_val += season.get(STAT_TYPE, 0)
                
                if career_val < MIN_CAREER_STAT:
                    continue

                next_milestone = ((int(career_val) // MILESTONE_STEP) + 1) * MILESTONE_STEP
                needed = next_milestone - career_val
                
                if needed <= WITHIN_RANGE:
                    print(f"  [!] MATCH: {name}")
                    
                    # We structure this dictionary specifically for the Javascript to read easily
                    candidates.append({
                        "player_name": name,
                        "team": data.get('currentTeamAbbrev', 'N/A'),
                        "current_stat": int(career_val),
                        "target_milestone": next_milestone,
                        "needed": int(needed),
                        "stat_type": STAT_TYPE
                    })
            
            time.sleep(0.05)
            
        except Exception:
            pass

    # Save to JSON
    if candidates:
        # Sort by needed
        candidates.sort(key=lambda x: x['needed'])
        
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(candidates, f, indent=4)
        print(f"\nSaved {len(candidates)} players to '{OUTPUT_FILE}'")
    else:
        print("No players found within range.")
        # Create empty list so JS doesn't crash
        with open(OUTPUT_FILE, 'w') as f:
            json.dump([], f)

if __name__ == "__main__":
    scan_nhl_active_players()
