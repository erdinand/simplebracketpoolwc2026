import pandas as pd
from weasyprint import HTML

groups = {
    "Grupo A": ["México", "África do Sul", "Coreia do Sul", "Rep. Tcheca"],
    "Grupo B": ["Canadá", "Bósnia e Herzegovina", "Catar", "Suíça"],
    "Grupo C": ["Brasil", "Marrocos", "Haiti", "Escócia"],
    "Grupo D": ["Estados Unidos", "Paraguai", "Austrália", "Turquia"],
    "Grupo E": ["Alemanha", "Curaçao", "Costa do Marfim", "Equador"],
    "Grupo F": ["Holanda", "Japão", "Suécia", "Tunísia"],
    "Grupo G": ["Bélgica", "Egito", "Irã", "Nova Zelândia"],
    "Grupo H": ["Espanha", "Cabo Verde", "Arábia Saudita", "Uruguai"],
    "Grupo I": ["França", "Senegal", "Iraque", "Noruega"],
    "Grupo J": ["Argentina", "Argélia", "Áustria", "Jordânia"],
    "Grupo K": ["Portugal", "RD Congo", "Uzbequistão", "Colômbia"],
    "Grupo L": ["Inglaterra", "Croácia", "Gana", "Panamá"]
}

matches_indices = [(0, 1), (2, 3), (0, 2), (3, 1), (0, 3), (1, 2)]

html_content = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@page {
    size: A4 portrait;
    margin: 15mm 12mm;
    background-color: #f4f7f6;
}
* {
    box-sizing: border-box;
}
body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    color: #222;
    margin: 0;
    padding: 0;
    background-color: #f4f7f6;
}
.header {
    text-align: center;
    background-color: #005541;
    color: white;
    padding: 20px 10px;
    margin: -15mm -12mm 20px -12mm;
    border-bottom: 6px solid #ffcc00;
}
.header h1 {
    margin: 0;
    font-size: 26pt;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.header p {
    margin: 5px 0 0 0;
    font-size: 13pt;
    font-weight: 300;
}
.participant-info {
    width: 100%;
    margin-bottom: 20px;
    background: white;
    border: 1px solid #dcdcdc;
    padding: 15px;
    border-radius: 8px;
    border-collapse: collapse;
}
.participant-info td {
    font-size: 12pt;
    vertical-align: middle;
}
.name-input, .contact-input {
    border: none;
    border-bottom: 1px solid #666;
    font-size: 12pt;
    background: transparent;
    padding: 2px 5px;
}
.groups-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 15px;
    margin-left: -7.5px;
    margin-right: -7.5px;
}
.groups-table td.card-cell {
    width: 50%;
    vertical-align: top;
    padding: 0;
}
.group-card {
    background: white;
    border-radius: 10px;
    border: 1px solid #ddd;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    overflow: hidden;
}
.group-title {
    background: #005541;
    color: #ffcc00;
    text-align: center;
    padding: 8px;
    font-size: 15pt;
    font-weight: bold;
    border-bottom: 1px solid #004030;
}
.matches-table {
    width: 100%;
    font-size: 11pt;
    border-collapse: collapse;
    margin: 10px 0;
}
.matches-table td {
    padding: 7px 5px;
    vertical-align: middle;
}
.team-left {
    text-align: right;
    width: 38%;
    font-weight: bold;
    color: #333;
}
.team-right {
    text-align: left;
    width: 38%;
    font-weight: bold;
    color: #333;
}
.score-cell {
    text-align: center;
    width: 8%;
}
.score-input {
    width: 30px;
    height: 30px;
    border: 2px solid #ccc;
    background: #fafafa;
    border-radius: 4px;
    text-align: center;
    font-size: 13pt;
    font-weight: bold;
    color: #000;
}
.vs {
    text-align: center;
    width: 8%;
    color: #888;
    font-size: 10pt;
}
</style>
</head>
<body>

<div class="header">
    <h1>Bolão da Copa do Mundo 2026</h1>
    <p>Fase de Grupos - Palpites</p>
</div>

<form>  
<table class="participant-info">
    <tr>
        <td style="width: 60%;"><b>Nome:</b> <input type="text" class="name-input" style="width: 75%;" name="participant_name"></td>
        <td style="width: 40%;"><b>Contato:</b> <input type="text" class="contact-input" style="width: 60%;" name="participant_contact"></td>
    </tr>
</table>

<table class="groups-table">
"""

group_names = list(groups.keys())
for i in range(0, len(group_names), 2):
    html_content += '<tr style="page-break-inside: avoid;">\n'
    for j in range(2):
        if i + j < len(group_names):
            g_name = group_names[i+j]
            teams = groups[g_name]
            g_code = g_name.replace(" ", "_")
            html_content += '<td class="card-cell">\n<div class="group-card">\n'
            html_content += f'<div class="group-title">{g_name}</div>\n'
            html_content += '<table class="matches-table">\n'
            match_num = 1
            for idx1, idx2 in matches_indices:
                t1, t2 = teams[idx1], teams[idx2]
                html_content += f"""
                <tr>
                    <td class="team-left">{t1}</td>
                    <td class="score-cell"><input type="text" class="score-input" name="{g_code}_m{match_num}_t1" maxlength="2"></td>
                    <td class="vs">x</td>
                    <td class="score-cell"><input type="text" class="score-input" name="{g_code}_m{match_num}_t2" maxlength="2"></td>
                    <td class="team-right">{t2}</td>
                </tr>
                """
                match_num += 1
            html_content += '</table>\n</div>\n</td>\n'
        else:
            html_content += '<td></td>\n'
    html_content += '</tr>\n'

html_content += """
</table>
</form>
</body>
</html>
"""

with open("bolao_copa_2026.html", "w", encoding="utf-8") as f:
    f.write(html_content)

HTML(filename="bolao_copa_2026.html").write_pdf("bolao_copa_2026.pdf", pdf_forms=True)
print("[file-tag: bolao_copa_2026.pdf]")

