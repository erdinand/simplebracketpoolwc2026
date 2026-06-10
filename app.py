# streamlit run app.py --server.headless true
import json
from datetime import datetime, timezone
import streamlit as st
import os
import pandas as pd
import requests
from pypdf import PdfReader

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
st.set_page_config(page_title="Bolão Copa 2026", page_icon="🏆", layout="centered")

SUBMISSIONS_DIR = "submissions"

# Translation map: (API Home Team, API Away Team) -> Your PDF match prefix
# Note: Ensure the team names match exactly what the API returns!
MATCH_MAP = {
    ("Mexico", "South Africa"): "Grupo_A_m1",
    ("South Korea", "Czech Republic"): "Grupo_A_m2",
    ("Mexico", "South Korea"): "Grupo_A_m3",
    # Add the rest of your matches...
}

# ==========================================
# 2. API FETCHING WITH CACHING
# ==========================================
@st.cache_data(ttl=300)  # Cache the data for 5 minutes (300 seconds)
def fetch_live_results():
    """
    Fetches live scores from Football-Data.org and translates them 
    into your OFFICIAL_RESULTS dictionary format.
    """
    official_results = {}
    
    # 1. Setup your API Request (Competition 2000 is the FIFA World Cup)
    url = "https://api.football-data.org/v4/competitions/2000/matches"
    
    # Football-Data.org uses 'X-Auth-Token' instead of the RapidAPI headers
    headers = {
        "X-Auth-Token": st.secrets["API_TOKEN"]
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        # Failsafe if the API rejects the token
        if response.status_code != 200:
            st.error("API Error: Please check your API token.")
            return {}
            
        data = response.json()

        # 2. Parse the games and map them
        for match in data.get("matches", []):
            home_team = match.get("homeTeam", {}).get("name")
            away_team = match.get("awayTeam", {}).get("name")
            status = match.get("status")
            
            # 3. Only grab scores if the game is live or finished
            # Football-Data.org statuses: SCHEDULED, TIMED, IN_PLAY, PAUSED, FINISHED
            if status in ["IN_PLAY", "PAUSED", "FINISHED"]:
                # The API stores the main score under 'fullTime' (even while live)
                home_score = match["score"]["fullTime"].get("home")
                away_score = match["score"]["fullTime"].get("away")
                
                # Create a tuple to look up in our map
                match_pair = (home_team, away_team)
                
                if match_pair in MATCH_MAP and home_score is not None:
                    match_prefix = MATCH_MAP[match_pair]
                    official_results[f"{match_prefix}_t1"] = home_score
                    official_results[f"{match_prefix}_t2"] = away_score
                    
        return official_results
        
    except Exception as e:
        st.error(f"Failed to fetch live API data: {e}")
        return {} # Return empty dict if API fails so the app doesn't crash

# ==========================================
# 3. PDF PARSING & SCORING LOGIC
# ==========================================
def parse_bolao_pdf(pdf_path):
    filename = os.path.basename(pdf_path)
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    
    if fields is None:
        return {"name": f"Invalid_PDF_{filename}", "contact": "Unknown", "guesses": {}}
    
    name = fields.get("participant_name", {}).get("/V", f"Unknown_{filename}")
    contact = fields.get("participant_contact", {}).get("/V", "No Contact")
    
    guesses = {}
    for field_name, field_data in fields.items():
        if field_data and "_m" in field_name and ("/V" in field_data):
            try:
                guesses[field_name] = int(field_data["/V"])
            except (ValueError, TypeError):
                guesses[field_name] = None
                
    return {"name": name, "contact": contact, "guesses": guesses}

def calculate_points(official_results, user_guesses):
    total_points = 0
    processed_matches = set()
    
    for key in official_results.keys():
        match_base = "_".join(key.split("_")[:-1]) 
        if match_base in processed_matches:
            continue
        
        processed_matches.add(match_base)
        act_t1, act_t2 = official_results.get(f"{match_base}_t1"), official_results.get(f"{match_base}_t2")
        g_t1, g_t2 = user_guesses.get(f"{match_base}_t1"), user_guesses.get(f"{match_base}_t2")
        
        if act_t1 is None or act_t2 is None or g_t1 is None or g_t2 is None:
            continue
            
        if act_t1 == g_t1 and act_t2 == g_t2:
            total_points += 3
        else:
            actual_outcome = (act_t1 > act_t2) - (act_t1 < act_t2)
            guess_outcome = (g_t1 > g_t2) - (g_t1 < g_t2)
            if actual_outcome == guess_outcome:
                total_points += 1
                
    return total_points

def generate_leaderboard(official_results):
    leaderboard_data = []
    
    # Failsafe: if the folder doesn't exist yet, return an empty dataframe
    if not os.path.exists(SUBMISSIONS_DIR):
        return pd.DataFrame()
        
    for file_name in os.listdir(SUBMISSIONS_DIR):
        if file_name.endswith(".pdf"):
            full_path = os.path.join(SUBMISSIONS_DIR, file_name)
            participant_data = parse_bolao_pdf(full_path)
            points = calculate_points(official_results, participant_data["guesses"])
            leaderboard_data.append({
                "Name": participant_data["name"],
                "Total Points": points
            })
            
    df = pd.DataFrame(leaderboard_data)
    if not df.empty:
        df = df.sort_values(by="Total Points", ascending=False).reset_index(drop=True)
        df.index += 1 
        df.index.name = "Rank"
    return df

def load_matches_from_json(filepath="matches.json"):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("matches", [])
    except FileNotFoundError:
        st.error(f"Could not find {filepath}. Make sure the file is in the same folder as app.py.")
        return []

# ==========================================
# 4. STREAMLIT USER INTERFACE
# ==========================================
st.title("🏆 Bolão da Copa do Mundo 2026")
st.write("Predictions are locked! Let the games begin. ⚽")

st.divider()

# Create two tabs
tab_leaderboard, tab_matches = st.tabs(["📊 Live Ranking", "🗓️ All Matches"])

# ------------------------------------------
# TAB 1: THE LEADERBOARD
# ------------------------------------------
with tab_leaderboard:
    st.subheader("Leaderboard")
    
    # 1. Fetch live results from the API (this data is cached for 5 mins)
    live_results = fetch_live_results()
    
    # 2. Calculate the leaderboard using the live data
    df_leaderboard = generate_leaderboard(live_results)
    
    if not df_leaderboard.empty:
        st.dataframe(df_leaderboard, width='stretch')
    else:
        st.info("No predictions found in the submissions folder, or no games have started yet!")

# ------------------------------------------
# TAB 2: THE MATCHES (With Time-Locked Guesses)
# ------------------------------------------
with tab_matches:
    st.subheader("🗓️ Group Stage Schedule & Player Guesses")
    
    # 1. Define the exact reveal deadline (June 11, 2026, 13:00 UTC-3 -> 16:00 UTC)
    REVEAL_DEADLINE = datetime(2026, 6, 11, 16, 0, 0, tzinfo=timezone.utc)
    #REVEAL_DEADLINE = datetime(2026, 6, 9, 16, 0, 0, tzinfo=timezone.utc)
    current_time = datetime.now(timezone.utc)
    guesses_are_visible = current_time >= REVEAL_DEADLINE

    # 2. Load all participant guesses into memory if the deadline has passed
    all_participant_guesses = []
    if guesses_are_visible and os.path.exists(SUBMISSIONS_DIR):
        for file_name in os.listdir(SUBMISSIONS_DIR):
            if file_name.endswith(".pdf"):
                full_path = os.path.join(SUBMISSIONS_DIR, file_name)
                all_participant_guesses.append(parse_bolao_pdf(full_path))

    # 3. Load and filter matches
    matches_data = load_matches_from_json("matches.json")
    
    # Filter out anything that isn't a group stage match
    group_stage_matches = [m for m in matches_data if m.get("stage") == "GROUP_STAGE"]

    if not group_stage_matches:
        st.info("No group stage matches found.")
    else:
        for match in group_stage_matches:
            group_raw = match.get("group", "Unknown Group")
            group = group_raw.replace("_", " ")
            status = match.get("status", "UNKNOWN")
            
            # Format Date
            raw_date = match.get("utcDate")
            if raw_date:
                dt = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M:%SZ")
                date_str = dt.strftime("%b %d, %Y - %H:%M UTC")
            else:
                date_str = "TBD"

            # Teams & Scores
            home_team = match.get("homeTeam", {}).get("name", "TBD")
            away_team = match.get("awayTeam", {}).get("name", "TBD")
            home_crest = match.get("homeTeam", {}).get("crest")
            away_crest = match.get("awayTeam", {}).get("crest")
            
            home_score = match.get("score", {}).get("fullTime", {}).get("home")
            away_score = match.get("score", {}).get("fullTime", {}).get("away")
            score_text = f"{home_score} x {away_score}" if home_score is not None else "vs"

            # Render Match Scoreboard Card
            st.markdown(f"**{group}** | {date_str} | Status: `{status}`")
            col1, col2, col3 = st.columns([2, 1, 2])
            
            with col1:
                if home_crest: st.image(home_crest, width=30)
                st.write(home_team)
            with col2:
                st.markdown(f"<h3 style='text-align: center; margin-top: 0;'>{score_text}</h3>", unsafe_allow_html=True)
            with col3:
                if away_crest: st.image(away_crest, width=30)
                st.write(away_team)

            # --- PARTICIPANT GUESSES SECTION ---
            match_pair = (home_team, away_team)
            match_prefix = MATCH_MAP.get(match_pair)

            if match_prefix:
                if guesses_are_visible:
                    # Collect everyone's guess for this specific match
                    match_guesses = []
                    for participant in all_participant_guesses:
                        g_t1 = participant["guesses"].get(f"{match_prefix}_t1")
                        g_t2 = participant["guesses"].get(f"{match_prefix}_t2")
                        
                        if g_t1 is not None and g_t2 is not None:
                            match_guesses.append({
                                "Participant": participant["name"],
                                "Prediction": f"{g_t1} x {g_t2}"
                            })
                    
                    # Display guesses inside a clean expander to save vertical space
                    with st.expander(f"👁️ View Participant Guesses ({len(match_guesses)})"):
                        if match_guesses:
                            guesses_df = pd.DataFrame(match_guesses)
                            st.dataframe(guesses_df, width='stretch', hide_index=True)
                        else:
                            st.caption("No guesses recorded for this match.")
                else:
                    st.caption("🔒 *Guesses for this match will unlock on June 11 at 1:00 PM (UTC-3)*")
            else:
                st.caption("⚠️ *Match mapping missing in MATCH_MAP dictionary.*")

            st.divider()