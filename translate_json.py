import json

# The translation map based on your HTML file
translation_map = {
    "Mexico": "México", "South Africa": "África do Sul", "South Korea": "Coreia do Sul", "Czechia": "Rep. Tcheca",
    "Canada": "Canadá", "Bosnia-Herzegovina": "Bósnia e Herzegovina", "Qatar": "Catar", "Switzerland": "Suíça",
    "Brazil": "Brasil", "Morocco": "Marrocos", "Haiti": "Haiti", "Scotland": "Escócia",
    "United States": "Estados Unidos", "Paraguay": "Paraguai", "Australia": "Austrália", "Turkey": "Turquia",
    "Germany": "Alemanha", "Curaçao": "Curaçao", "Ivory Coast": "Costa do Marfim", "Ecuador": "Equador",
    "Netherlands": "Holanda", "Japan": "Japão", "Sweden": "Suécia", "Tunisia": "Tunísia",
    "Belgium": "Bélgica", "Egypt": "Egito", "Iran": "Irã", "New Zealand": "Nova Zelândia",
    "Spain": "Espanha", "Cape Verde Islands": "Cabo Verde", "Cape Verde": "Cabo Verde", "Saudi Arabia": "Arábia Saudita", "Uruguay": "Uruguai",
    "France": "França", "Senegal": "Senegal", "Iraq": "Iraque", "Norway": "Noruega",
    "Argentina": "Argentina", "Algeria": "Argélia", "Austria": "Áustria", "Jordan": "Jordânia",
    "Portugal": "Portugal", "DR Congo": "RD Congo", "Congo DR": "RD Congo", "Uzbekistan": "Uzbequistão", "Colombia": "Colômbia",
    "England": "Inglaterra", "Croatia": "Croácia", "Ghana": "Gana", "Panama": "Panamá"
}

with open("matches.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for match in data.get("matches", []):
    # Add name_pt to Home Team
    home_name = match.get("homeTeam", {}).get("name")
    if home_name:
        match["homeTeam"]["name_pt"] = translation_map.get(home_name, home_name)
        
    # Add name_pt to Away Team
    away_name = match.get("awayTeam", {}).get("name")
    if away_name:
        match["awayTeam"]["name_pt"] = translation_map.get(away_name, away_name)

with open("matches.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("✅ matches.json updated successfully with PT-BR names!")
