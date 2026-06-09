import streamlit as st
import os
import pandas as pd
from pypdf import PdfReader
from datetime import datetime, timezone

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
st.set_page_config(page_title="Bolão Copa 2026", page_icon="🏆", layout="centered")

# Directory to store uploaded PDFs
SUBMISSIONS_DIR = "submissions"
os.makedirs(SUBMISSIONS_DIR, exist_ok=True)

# Tournament Deadline: June 11, 2026, 12:00 PM UTC
DEADLINE = datetime(2026, 6, 11, 12, 0, 0, tzinfo=timezone.utc)

# Official results dictionary - You will update this and push to GitHub as games finish!
OFFICIAL_RESULTS = {
    # Example format: 
    # "Grupo_A_m1_t1": 2, "Grupo_A_m1_t2": 1,
}

# ==========================================
# 2. LOGIC FUNCTIONS
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

def generate_leaderboard():
    leaderboard_data = []
    for file_name in os.listdir(SUBMISSIONS_DIR):
        if file_name.endswith(".pdf"):
            full_path = os.path.join(SUBMISSIONS_DIR, file_name)
            participant_data = parse_bolao_pdf(full_path)
            points = calculate_points(OFFICIAL_RESULTS, participant_data["guesses"])
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

# ==========================================
# 3. STREAMLIT USER INTERFACE
# ==========================================
st.title("🏆 Bolão da Copa do Mundo 2026")

current_time = datetime.now(timezone.utc)

# Upload Zone Logic
if current_time < DEADLINE:
    st.info("⏳ **Uploads close on:** June 11, 2026 at 12:00 PM UTC.")
    uploaded_file = st.file_uploader("Upload your filled PDF here:", type="pdf")
    
    if uploaded_file is not None:
        # Save file temporarily to parse the user's name
        temp_path = os.path.join(SUBMISSIONS_DIR, "temp.pdf")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        data = parse_bolao_pdf(temp_path)
        safe_name = str(data["name"]).replace(" ", "_").replace("/", "").strip()
        
        # Rename file to the participant's name to prevent duplicates
        final_path = os.path.join(SUBMISSIONS_DIR, f"{safe_name}.pdf")
        os.replace(temp_path, final_path)
        
        st.success(f"✅ PDF received for **{data['name']}**! Your guesses are saved.")
else:
    st.error("🔒 **Submissions are now closed!** Enjoy the tournament!")

st.divider()

# Leaderboard Zone
st.subheader("📊 Live Ranking")
df_leaderboard = generate_leaderboard()

if not df_leaderboard.empty:
    st.dataframe(df_leaderboard, use_container_width=True)
else:
    st.write("No predictions have been submitted yet. Be the first!")
