import json
import os
import requests
import sys
from datetime import datetime

# Optional: Import PRAW for Reddit if installed
try:
    import praw
except ImportError:
    praw = None

# --- CONFIG ---
SITE_URL = "https://statwatch.live" 
DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK_URL')
REDDIT_CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID')
REDDIT_SECRET = os.environ.get('REDDIT_SECRET')
REDDIT_USER = os.environ.get('REDDIT_USER')
REDDIT_PASS = os.environ.get('REDDIT_PASS')
TARGET_SUBREDDIT = "u_" + REDDIT_USER if REDDIT_USER else "test" 

def load_data(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, 'r') as f:
        return json.load(f)

def generate_report():
    nba = load_data('nba_milestones.json')
    nhl = load_data('nhl_milestones.json')

    # Sort by urgency (lowest 'needed' first)
    nba.sort(key=lambda x: x['needed'])
    nhl.sort(key=lambda x: x['needed'])

    # Filter: Only show very close milestones to avoid noise
    nba_urgent = [p for p in nba if p['needed'] < 150][:5]
    nhl_urgent = [p for p in nhl if p['needed'] < 10][:5]

    if not nba_urgent and not nhl_urgent:
        return None

    # Construct Message (Newsletter Style)
    date_str = datetime.now().strftime("%A, %B %d")
    
    lines = [
        f"# 🏆 Daily Milestone Tracker - {date_str}",
        "> *Your daily dose of sports history in the making.*",
        "",
        "---",
        ""
    ]

    if nba_urgent:
        lines.append("## 🏀 NBA Watch")
        for p in nba_urgent:
            pts_label = "point" if p['needed'] == 1 else "points"
            lines.append(f"* **{p['player_name']}** ({p['team']}) is approaching **{p['target_milestone']:,} PTS**")
            lines.append(f"  * Needs {p['needed']} more {pts_label}")
        lines.append("")

    if nhl_urgent:
        lines.append("## 🏒 NHL Watch")
        for p in nhl_urgent:
            goals_label = "goal" if p['needed'] == 1 else "goals"
            lines.append(f"* **{p['player_name']}** ({p['team']}) is approaching **{p['target_milestone']:,} GOALS**")
            lines.append(f"  * Needs {p['needed']} more {goals_label}")
        lines.append("")

    lines.append("---")
    lines.append(f"📊 **View Live Charts & Betting Lines:** {SITE_URL}")
    lines.append(f"👀 *Updates daily at 8:00 AM EST*")
    
    return "\n".join(lines)

def save_to_file(content):
    filename = "daily_digest.txt"
    
    # Clean up the Markdown syntax for the local text file
    # This makes the text file look pretty for humans (stripping **, ##, etc)
    clean_content = content \
        .replace("**", "") \
        .replace("## ", "") \
        .replace("# ", "") \
        .replace("> *", "") \
        .replace("*", "") \
        .replace("  * ", "\t- ") \
        .replace("* ", "• ") 
        
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(clean_content)
        print(f"[Success] Newsletter preview saved to {filename}")
    except Exception as e:
        print(f"[Error] Could not save text file: {e}")

def post_to_discord(content):
    if not DISCORD_WEBHOOK:
        print("[Skipping] No Discord Webhook URL found.")
        return

    # Discord format tweaks (Markdown header conversion)
    discord_content = content.replace("# ", "**").replace("## ", "__**").replace("**", "**__")
    
    data = {
        "content": discord_content,
        "username": "StatWatch Bot",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2583/2583344.png"
    }
    
    try:
        r = requests.post(DISCORD_WEBHOOK, json=data)
        if r.status_code == 204:
            print("[Success] Posted to Discord.")
        else:
            print(f"[Error] Discord returned {r.status_code}")
    except Exception as e:
        print(f"[Error] Discord post failed: {e}")

def post_to_reddit(title, content):
    if not (REDDIT_CLIENT_ID and REDDIT_SECRET and REDDIT_USER and REDDIT_PASS and praw):
        print("[Skipping] Reddit credentials missing or PRAW not installed.")
        return

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_SECRET,
            user_agent="MilestoneBot/1.0",
            username=REDDIT_USER,
            password=REDDIT_PASS
        )
        
        # Post to specific subreddit
        subreddit = reddit.subreddit(TARGET_SUBREDDIT)
        subreddit.submit(title, selftext=content)
        print(f"[Success] Posted to r/{TARGET_SUBREDDIT}")
        
    except Exception as e:
        print(f"[Error] Reddit post failed: {e}")

if __name__ == "__main__":
    print("--- GENERATING MARKETING REPORT ---")
    report = generate_report()
    
    if report:
        # Generate the clean local file
        save_to_file(report)
        
        # Only attempt remote posting if keys exist
        if DISCORD_WEBHOOK:
            print("Sending to Discord...")
            post_to_discord(report)
            
        if REDDIT_CLIENT_ID:
            print("Sending to Reddit...")
            post_to_reddit("Daily Sports Milestone Update", report)
    else:
        print("No urgent milestones today. Skipping posts.")