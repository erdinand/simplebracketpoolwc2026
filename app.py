# streamlit run app.py --server.headless true
import json
from datetime import datetime, timezone, timedelta
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

# ==========================================
# 2. API FETCHING WITH CACHING
# ==========================================
def sync_api_to_json():
    """
    Reads matches.json. If a match has started but is not FINISHED, 
    it fetches the specific match ID from the API and updates the local JSON file.
    """
    API_KEY = st.secrets["API_TOKEN"]
    headers = {"X-Auth-Token": API_KEY}
    
    try:
        with open("matches.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        st.error(f"Error loading matches.json: {e}")
        return

    current_time = datetime.now(timezone.utc)
    json_was_updated = False

    for match in data.get("matches", []):
        if match.get("stage") != "GROUP_STAGE":
            continue
            
        status = match.get("status")
        
        # If the match is already completely finished, we don't need to ask the API anymore!
        if status == "FINISHED":
            continue 

        raw_date = match.get("utcDate")
        if raw_date:
            match_time = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            
            # If the current time has passed the match start time
            if current_time >= match_time:
                match_id = match.get("id")
                if not match_id:
                    continue
                    
                try:
                    # Call the API ONLY for this specific match ID
                    url = f"https://api.football-data.org/v4/matches/{match_id}"
                    response = requests.get(url, headers=headers)
                    
                    if response.status_code == 200:
                        live_data = response.json()
                        
                        # Update the specific match properties in our local dictionary
                        match["status"] = live_data.get("status")
                        match["score"] = live_data.get("score")
                        json_was_updated = True
                except Exception as e:
                    print(f"Failed to fetch match {match_id}: {e}")

    # If any live scores were updated, save them back to the JSON file
    if json_was_updated:
        with open("matches.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

def fetch_live_results():
    official_results = {}
    DYNAMIC_MATCH_MAP = get_dynamic_match_map()
    
    # We load it fresh (it might have just been updated by sync_api_to_json)
    matches_data = load_matches_from_json("matches.json") 
    
    for match in matches_data:
        status = match.get("status")
        
        # Extract scores for ongoing or finished matches
        if status in ["IN_PLAY", "PAUSED", "FINISHED"]:
            home_team = match.get("homeTeam", {}).get("name")
            away_team = match.get("awayTeam", {}).get("name")
            
            home_score = match.get("score", {}).get("fullTime", {}).get("home")
            away_score = match.get("score", {}).get("fullTime", {}).get("away")
            
            mapping = DYNAMIC_MATCH_MAP.get((home_team, away_team))
            
            if mapping and home_score is not None:
                match_prefix = mapping["pdf_id"]
                
                if mapping["home_is"] == "t1":
                    official_results[f"{match_prefix}_t1"] = home_score
                    official_results[f"{match_prefix}_t2"] = away_score
                else:
                    official_results[f"{match_prefix}_t1"] = away_score
                    official_results[f"{match_prefix}_t2"] = home_score
                    
    return official_results

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
    exact_scores = 0
    correct_outcomes = 0
    processed_matches = set()
    
    for key in official_results.keys():
        match_base = "_".join(key.split("_")[:-1]) 
        if match_base in processed_matches:
            continue
        
        processed_matches.add(match_base)
        act_t1, act_t2 = official_results.get(f"{match_base}_t1"), official_results.get(f"{match_base}_t2")
        g_t1, g_t2 = user_guesses.get(f"{match_base}_t1"), user_guesses.get(f"{match_base}_t2")
        
        # Skip if the match hasn't happened or the user left it blank
        if act_t1 is None or act_t2 is None or g_t1 is None or g_t2 is None:
            continue
            
        # 3 Points: Exact Score
        if act_t1 == g_t1 and act_t2 == g_t2:
            total_points += 3
            exact_scores += 1
        else:
            # 1 Point: Correct Outcome
            actual_outcome = (act_t1 > act_t2) - (act_t1 < act_t2)
            guess_outcome = (g_t1 > g_t2) - (g_t1 < g_t2)
            if actual_outcome == guess_outcome:
                total_points += 1
                correct_outcomes += 1
                
    return {
        "total": total_points,
        "exact": exact_scores,
        "correct": correct_outcomes
    }

def generate_leaderboard(official_results):
    leaderboard_data = []
    
    if not os.path.exists(SUBMISSIONS_DIR):
        return pd.DataFrame()
        
    for file_name in os.listdir(SUBMISSIONS_DIR):
        if file_name.endswith(".pdf"):
            full_path = os.path.join(SUBMISSIONS_DIR, file_name)
            participant_data = parse_bolao_pdf(full_path)
            
            # Now we receive a dictionary of stats instead of just an integer
            pts_data = calculate_points(official_results, participant_data["guesses"])
            
            leaderboard_data.append({
                "Nome": get_first_name(participant_data["name"]),
                "Pontuação Total": pts_data["total"],
                "Placares Exatos (3 pts)": pts_data["exact"],
                "Resultados Corretos (1 pt)": pts_data["correct"]
            })
            
    df = pd.DataFrame(leaderboard_data)
    if not df.empty:
        # Sort by Total Points first. If tied, sort by Exact Scores (Tiebreaker!)
        df = df.sort_values(
            by=["Pontuação Total", "Placares Exatos (3 pts)", "Nome"], 
            ascending=[False, False, True]
        ).reset_index(drop=True)
        
        df.index += 1 
        df.index.name = "Posição"
        
    return df

def load_matches_from_json(filepath="matches.json"):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("matches", [])
    except FileNotFoundError:
        st.error(f"Could not find {filepath}. Make sure the file is in the same folder as app.py.")
        return []

def get_dynamic_match_map():
    """Extracts the embedded PDF mappings from the local JSON file"""
    matches_data = load_matches_from_json("matches.json")
    mapping = {}
    for match in matches_data:
        if "pdf_mapping" in match:
            home = match.get("homeTeam", {}).get("name")
            away = match.get("awayTeam", {}).get("name")
            mapping[(home, away)] = match["pdf_mapping"]
    return mapping

def get_first_name(full_name):
    return full_name.split()[0].capitalize()

# ==========================================
# 4. STREAMLIT USER INTERFACE
# ==========================================
st.title("🏆 Bolão da Copa do Mundo 2026")
st.write("Os palpites estão encerrados! Que comecem os jogos. ⚽")

# Synchronize missing/live scores with the API before rendering the UI
sync_api_to_json()

st.divider()

# Create three tabs
tab_leaderboard, tab_matches, tab_pdfs = st.tabs(["📊 Classificação ao Vivo", "🗓️ Jogos e Palpites", "📄 PDFs Originais"])

# ------------------------------------------
# TAB 1: THE LEADERBOARD
# ------------------------------------------
with tab_leaderboard:
    st.subheader("Tabela de Classificação")
    
    live_results = fetch_live_results()
    df_leaderboard = generate_leaderboard(live_results)
    
    if not df_leaderboard.empty:
        #st.dataframe(df_leaderboard, width="stretch")
        st.dataframe(df_leaderboard)
        #st.table(df_leaderboard)
    else:
        st.info("Nenhum palpite encontrado na pasta de submissões, ou nenhum jogo começou ainda!")

# ------------------------------------------
# TAB 2: THE MATCHES (With Filters & Time-Locked Guesses)
# ------------------------------------------
with tab_matches:
    st.subheader("🗓️ Tabela da Fase de Grupos")
    
    # --- CONFIGURAÇÃO DO BLOQUEIO DE TEMPO ---
    br_timezone = timezone(timedelta(hours=-3))
    REVEAL_DEADLINE = datetime(2026, 6, 11, 16, 0, 0, tzinfo=br_timezone)
    current_time = datetime.now(br_timezone)
    guesses_are_visible = current_time >= REVEAL_DEADLINE

    all_participant_guesses = []
    if guesses_are_visible and os.path.exists(SUBMISSIONS_DIR):
        for file_name in os.listdir(SUBMISSIONS_DIR):
            if file_name.endswith(".pdf"):
                full_path = os.path.join(SUBMISSIONS_DIR, file_name)
                all_participant_guesses.append(parse_bolao_pdf(full_path))

    # Carrega todos os jogos da fase de grupos
    matches_data = load_matches_from_json("matches.json")
    group_stage_matches = [m for m in matches_data if m.get("stage") == "GROUP_STAGE"]

    # --- PROCESSAMENTO DOS FILTROS DISPONÍVEIS ---
    # Coleta dinamicamente todos os grupos, times e datas que existem no JSON
    lista_grupos = sorted(list(set(m.get("group", "").replace("GROUP_", "GRUPO ") for m in group_stage_matches if m.get("group"))))
    
    lista_times = set()
    lista_datas = set()

    for m in group_stage_matches:
        # Times (PT-BR se disponível, senão nome original)
        lista_times.add(m.get("homeTeam", {}).get("name_pt", m.get("homeTeam", {}).get("name", "A Definir")))
        lista_times.add(m.get("awayTeam", {}).get("name_pt", m.get("awayTeam", {}).get("name", "A Definir")))
        # Datas (Apenas o dia formatado em UTC-3)
        raw_date = m.get("utcDate")
        if raw_date:
            dt_utc = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            lista_datas.add(dt_utc.astimezone(br_timezone).strftime("%d/%m/%Y"))

    lista_times = sorted(list(lista_times - {"A Definir"}))
    lista_datas = sorted(list(lista_datas), key=lambda x: datetime.strptime(x, "%d/%m/%Y"))

    # --- RENDERIZAÇÃO DOS FILTROS NA INDERFACE ---
    st.markdown("#### 🔍 Filtrar Jogos")
    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        filtro_grupo = st.selectbox("Por Grupo", ["Todos"] + lista_grupos)
    with f_col2:
        filtro_time = st.selectbox("Por Seleção", ["Todos"] + lista_times)
    with f_col3:
        filtro_data = st.selectbox("Por Data", ["Todas"] + lista_datas)

    # --- APLICAÇÃO DOS FILTROS NA LISTA DE JOGOS ---
    filtered_matches = []
    for match in group_stage_matches:
        # Prepara as variáveis para validação
        g_raw = match.get("group", "Grupo Desconhecido").replace("GROUP_", "GRUPO ")
        h_team = match.get("homeTeam", {}).get("name_pt", match.get("homeTeam", {}).get("name", "A Definir"))
        a_team = match.get("awayTeam", {}).get("name_pt", match.get("awayTeam", {}).get("name", "A Definir"))
        
        m_date = "A Definir"
        raw_date = match.get("utcDate")
        if raw_date:
            dt_utc = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            m_date = dt_utc.astimezone(br_timezone).strftime("%d/%m/%Y")
            date_str_completo = dt_utc.astimezone(br_timezone).strftime("%d/%m/%Y - %H:%M")
        else:
            date_str_completo = "A Definir"

        # Checa se o jogo passa em todos os filtros selecionados
        if filtro_grupo != "Todos" and g_raw != filtro_grupo:
            continue
        if filtro_time != "Todos" and h_team != filtro_time and a_team != filtro_time:
            continue
        if filtro_data != "Todas" and m_date != filtro_data:
            continue
            
        # Se passou, adiciona um dicionário auxiliar com os dados já mastigados
        match["_custom_date_str"] = date_str_completo
        match["_custom_group_str"] = g_raw
        match["_custom_home"] = h_team
        match["_custom_away"] = a_team
        filtered_matches.append(match)

    # --- EXIBIÇÃO DOS JOGOS FILTRADOS ---
    if not filtered_matches:
        st.warning("Nenhum jogo corresponde aos filtros selecionados.")
    else:
        for match in filtered_matches:
            group = match["_custom_group_str"]
            date_str = match["_custom_date_str"]
            home_team = match["_custom_home"]
            away_team = match["_custom_away"]
            
            status = match.get("status", "DESCONHECIDO")

            # Unified map for translation and color
            status_config = {
                "TIMED": {"text": "Agendado", "color": "#1f77b4"},
                "SCHEDULED": {"text": "Agendado", "color": "#1f77b4"},
                "IN_PLAY": {"text": "Ao Vivo", "color": "#28a745"},
                "PAUSED": {"text": "Intervalo", "color": "#ffc107"},
                "FINISHED": {"text": "Encerrado", "color": "#6c757d"}
            }
            
            # Fetch the config safely (fallback to black and original text if unknown)
            current_config = status_config.get(status, {"text": status, "color": "#000000"})
            status_pt = current_config["text"]
            cor_hex = current_config["color"]
            
            home_crest = match.get("homeTeam", {}).get("crest")
            away_crest = match.get("awayTeam", {}).get("crest")
            
            home_score = match.get("score", {}).get("fullTime", {}).get("home")
            away_score = match.get("score", {}).get("fullTime", {}).get("away")

            score_text = f"{home_score} x {away_score}" if home_score is not None else "x"

            # Render the match score
            st.markdown(
                f"**{group}** | {date_str} | Status: <span style='color: {cor_hex}; font-weight: bold;'>{status_pt}</span>",
                unsafe_allow_html=True
            )

            col1, col2, col3 = st.columns([2, 1, 2])
            
            with col1:
                if home_crest: st.image(home_crest, width=30)
                st.write(home_team)
            with col2:
                st.markdown(f"<h3 style='text-align: center; margin-top: 0;'>{score_text}</h3>", unsafe_allow_html=True)
            with col3:
                if away_crest: st.image(away_crest, width=30)
                st.write(away_team)

            # --- PALPITES DOS PARTICIPANTES ---
            mapping = match.get("pdf_mapping")

            if mapping:
                if guesses_are_visible:
                    match_guesses = []
                    match_prefix = mapping["pdf_id"]
                    
                    for participant in all_participant_guesses:
                        g_t1 = participant["guesses"].get(f"{match_prefix}_t1")
                        g_t2 = participant["guesses"].get(f"{match_prefix}_t2")
                        
                        if g_t1 is not None and g_t2 is not None:
                            if mapping["home_is"] == "t1":
                                guess_home = g_t1
                                guess_away = g_t2
                            else:
                                guess_home = g_t2
                                guess_away = g_t1
                                
                            score_display = f"{guess_home} x {guess_away}"
                            
                            pts_indicator = "⏳"
                            if home_score is not None and away_score is not None:
                                if guess_home == home_score and guess_away == away_score:
                                    pts_indicator = "🟢 3 pts"
                                else:
                                    actual_outcome = (home_score > away_score) - (home_score < away_score)
                                    guess_outcome = (guess_home > guess_away) - (guess_home < guess_away)
                                    if actual_outcome == guess_outcome:
                                        pts_indicator = "🟡 1 pt"
                                    else:
                                        pts_indicator = "🔴 0 pts"
                                
                            match_guesses.append({
                                "Participante": get_first_name(participant["name"]),
                                "Palpite": score_display,
                                "Pontos": pts_indicator
                            })
                    
                    with st.expander(f"👁️ Ver Palpites dos Participantes ({len(match_guesses)})"):
                        if match_guesses:
                            guesses_df = pd.DataFrame(match_guesses)
                            st.dataframe(guesses_df, width="stretch", hide_index=True)
                        else:
                            st.caption("Nenhum palpite registrado para este jogo.")
                else:
                    st.caption("🔒 *Os palpites para este jogo serão liberados no dia 11 de Junho às 13:00*")
            else:
                st.caption("⚠️ *Aguardando dados de mapeamento para este jogo.*")

            st.divider()

# ------------------------------------------
# TAB 3: ORIGINAL SUBMISSION PDFS (Safe Native Download)
# ------------------------------------------
with tab_pdfs:
    st.subheader("📄 PDFs Originais Submetidos por cada participante")
    
    # 1. Check if the time lock has been released
    if not guesses_are_visible:
        st.warning("🔒 **Acesso Bloqueado:** Os PDFs originais com os palpites estarão disponíveis para conferência apenas após o dia **11 de Junho às 13:00 (UTC-3)**.")
    else:
        st.write("Clique nos botões abaixo para baixar e abrir a folha de palpites original e oficial de cada participante.")

        st.caption("💡 *Dica: Se os nomes ou títulos mostrarem caracteres estranhos ao abrir o arquivo diretamente no seu navegador de internet, por favor, abra o arquivo baixado usando um leitor de PDF dedicado (como o Adobe Acrobat ou o aplicativo nativo de PDF do seu celular) para visualizá-lo perfeitamente.*")
        st.divider()

        if not os.path.exists(SUBMISSIONS_DIR):
            st.info("Nenhuma pasta de submissões encontrada.")
        else:
            # List all .pdf files in the folder
            pdf_files = sorted([f for f in os.listdir(SUBMISSIONS_DIR) if f.endswith(".pdf")])

            if not pdf_files:
                st.warning("Nenhum arquivo PDF de palpite foi encontrado na pasta.")
            else:
                # Organize the buttons into two columns for a clean layout
                col1, col2 = st.columns(2)
                
                for index, pdf_file in enumerate(pdf_files):
                    nome_limpo = pdf_file.replace(".pdf", "").replace("_", " ")
                    caminho_completo = os.path.join(SUBMISSIONS_DIR, pdf_file)

                    # Read the raw binary file from your computer (without converting to base64)
                    with open(caminho_completo, "rb") as f:
                        pdf_bytes = f.read()

                    # Distribute the buttons between the two columns
                    col_alvo = col1 if index % 2 == 0 else col2
                    
                    with col_alvo:
                        st.download_button(
                            label=f"📄 {nome_limpo}",
                            data=pdf_bytes,
                            file_name=pdf_file,
                            mime="application/pdf",
                            key=f"btn_{pdf_file}", # Unique key essential for loops
                            use_container_width=True # Makes the buttons full-width and elegant
                        )
