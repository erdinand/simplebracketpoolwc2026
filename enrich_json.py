import json

# The exact team names as they appear in the football-data API
groups_api = {
    "GROUP_A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "GROUP_B": ["Canada", "Bosnia-Herzegovina", "Qatar", "Switzerland"],
    "GROUP_C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "GROUP_D": ["United States", "Paraguay", "Australia", "Turkey"],
    "GROUP_E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
    "GROUP_F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "GROUP_G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "GROUP_H": ["Spain", "Cape Verde Islands", "Saudi Arabia", "Uruguay"],
    "GROUP_I": ["France", "Senegal", "Iraq", "Norway"],
    "GROUP_J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "GROUP_K": ["Portugal", "Congo DR", "Uzbekistan", "Colombia"],
    "GROUP_L": ["England", "Croatia", "Ghana", "Panama"]
}

# The exact match indices logic from your HTML generation script
matches_indices = [(0, 1), (2, 3), (0, 2), (3, 1), (0, 3), (1, 2)]

pdf_matches_map = {}

# Generate the mapping dynamically
for group_api_name, teams in groups_api.items():
    group_pdf_prefix = group_api_name.replace("GROUP_", "Grupo_")
    
    for i, (idx1, idx2) in enumerate(matches_indices):
        match_num = i + 1
        t1 = teams[idx1]
        t2 = teams[idx2]
        match_id = f"{group_pdf_prefix}_m{match_num}"
        
        # Map both orientations to handle API Home/Away order
        pdf_matches_map[(t1, t2)] = {"pdf_id": match_id, "home_is": "t1", "away_is": "t2"}
        pdf_matches_map[(t2, t1)] = {"pdf_id": match_id, "home_is": "t2", "away_is": "t1"}

# Load your fixed matches.json
with open("matches.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Inject the mapping directly into the match objects
for match in data.get("matches", []):
    if match.get("stage") == "GROUP_STAGE":
        home_team = match.get("homeTeam", {}).get("name")
        away_team = match.get("awayTeam", {}).get("name")
        
        mapping = pdf_matches_map.get((home_team, away_team))
        
        if mapping:
            match["pdf_mapping"] = mapping
        else:
            print(f"⚠️ Warning: Could not map API match: {home_team} vs {away_team}. Check spelling!")

# Save the updated file
with open("matches.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("✅ matches.json successfully updated with PDF IDs!")
