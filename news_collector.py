# news_collector.py (com categorização por tema)
import os, re, feedparser, requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict

# ============================================================
# CONFIGURAÇÕES
# ============================================================
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_TO = os.environ.get("EMAIL_TO", "drbadiodefora@gmail.com")
if not RESEND_API_KEY:
    print("❌ RESEND_API_KEY não configurada.")
    exit(1)

GOOGLE_NEWS_URL = "https://news.google.com/rss/search?q=Cabo+Verde+OR+Cape+Verde+OR+Cap-Vert&hl=pt&gl=CV&ceid=CV:pt"
LAST_RUN_FILE = "last_news_run.txt"

# ============================================================
# DEFINIÇÃO DE TEMAS E PALAVRAS‑CHAVE
# ============================================================
TEMAS = {
    "Política": [
        "eleição", "eleições", "governo", "parlamento", "presidente", "primeiro-ministro",
        "partido", "deputado", "assembleia", "voto", "campanha", "mpd", "paicv", "ucid"
    ],
    "Economia": [
        "economia", "finanças", "empresa", "negócio", "turismo", "investimento",
        "crescimento", "pib", "inflação", "desemprego", "salário", "comércio", "banco"
    ],
    "Saúde": [
        "saúde", "hospital", "médico", "doença", "covid", "vacina", "tratamento",
        "síndrome", "hantavírus", "surto", "doente", "sns"
    ],
    "Desporto": [
        "desporto", "futebol", "selecção", "seleção", "jogo", "campeonato", "copa",
        "mundial", "atleta", "treinador", "clube"
    ],
    "Internacional": [
        "internacional", "mundo", "global", "onu", "unidos", "exterior", "embaixada",
        "acordo internacional"
    ],
    "Sociedade & Cultura": [
        "cultura", "arte", "música", "educação", "ensino", "universidade", "escola",
        "religião", "igreja", "tradição", "comunidade", "juventude", "mulher"
    ],
    "Justiça & Segurança": [
        "justiça", "tribunal", "polícia", "crime", "segurança", "prisão", "advogado",
        "investigação", "corrupção", "violência"
    ],
    "Ambiente & Clima": [
        "ambiente", "clima", "energia", "água", "resíduos", "proteção", "sustentabilidade"
    ]
}

def classificar_titulo(titulo, resumo):
    """Classifica uma notícia num tema com base no título e resumo."""
    texto = f"{titulo} {resumo}".lower()
    for tema, palavras in TEMAS.items():
        for palavra in palavras:
            if palavra in texto:
                return tema
    return "Outros"

# ============================================================
# FUNÇÕES DE COLETA
# ============================================================
def load_last_run():
    try:
        with open(LAST_RUN_FILE, "r") as f:
            return datetime.fromisoformat(f.read().strip())
    except:
        return (datetime.now(ZoneInfo("Atlantic/Cape_Verde")) - timedelta(days=3)).replace(hour=0, minute=0, second=0)

def save_last_run(dt):
    with open(LAST_RUN_FILE, "w") as f:
        f.write(dt.isoformat())

def extrair_data(entry):
    if 'published_parsed' in entry and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Atlantic/Cape_Verde"))
    return None

def coletar_noticias():
    ultima = load_last_run()
    agora = datetime.now(ZoneInfo("Atlantic/Cape_Verde"))
    novas = []
    maior_data = ultima

    feed = feedparser.parse(GOOGLE_NEWS_URL, agent="Mozilla/5.0")
    for entry in feed.entries:
        pub = extrair_data(entry)
        if not pub or pub <= ultima:
            continue
        if pub > maior_data:
            maior_data = pub

        titulo = entry.get('title', 'Sem título')
        resumo = entry.get('summary', '')[:200]
        fonte = entry.get('source', {}).get('title', 'Google News')
        link = entry.get('link', '')
        data_str = pub.strftime("%d/%m/%Y %H:%M")

        tema = classificar_titulo(titulo, resumo)

        novas.append({
            "fonte": fonte,
            "data": pub,               # datetime object para ordenação
            "data_str": data_str,
            "titulo": titulo,
            "link": link,
            "resumo": resumo or titulo[:200],
            "tema": tema
        })

    save_last_run(maior_data if maior_data > ultima else agora)
    return novas

# ============================================================
# ENVIO DE E‑MAIL COM CATEGORIAS
# ============================================================
def enviar_email(noticias):
    if not noticias:
        print("Nenhuma notícia nova. E‑mail não enviado.")
        return

    # Agrupar por tema
    grupos = defaultdict(list)
    for n in noticias:
        grupos[n["tema"]].append(n)

    # Ordenar cada grupo por data (mais recente primeiro)
    for tema in grupos:
        grupos[tema].sort(key=lambda x: x["data"], reverse=True)

    assunto = f"📰 {len(noticias)} notícias sobre Cabo Verde – {datetime.now().strftime('%d/%m/%Y')}"

    # Construir HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body>
        <h2>🌍 Notícias sobre Cabo Verde (por tema)</h2>
        <p><strong>{len(noticias)}</strong> notícia(s) nova(s) desde a última verificação.</p>
    """
    # Ordem desejada dos temas (personalizável)
    ordem_temas = ["Política", "Economia", "Saúde", "Desporto", "Internacional", "Sociedade & Cultura", "Justiça & Segurança", "Ambiente & Clima", "Outros"]
    for tema in ordem_temas:
        if tema not in grupos:
            continue
        noticias_tema = grupos[tema]
        html += f"<h3>{tema} ({len(noticias_tema)})</h3>"
        html += '<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width:100%">'
        html += '<thead style="background-color: #f0f0f0;"><tr><th>Fonte</th><th>Data</th><th>Título</th><th>Resumo</th></tr></thead><tbody>'
        for n in noticias_tema:
            html += f"""
            <tr>
                <td>{n['fonte']}</td>
                <td>{n['data_str']}</td>
                <td><a href="{n['link']}">{n['titulo']}</a></td>
                <td>{n['resumo']}</td>
            </tr>
            """
        html += "</tbody></table><br>"
    html += """
        <p><small>📌 Relatório diário gerado automaticamente. As notícias são agrupadas por tema e ordenadas por data/hora (mais recentes primeiro dentro de cada tema).</small></p>
    </body>
    </html>
    """

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json={
                "from": "onboarding@resend.dev",  # domínio sandbox do Resend
                "to": [EMAIL_TO],
                "subject": assunto,
                "html": html
            }
        )
        if resp.status_code == 200:
            print("✅ E‑mail enviado via Resend!")
        else:
            print(f"❌ Erro: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Exceção: {e}")

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("🔍 Coletor de notícias iniciado...")
    noticias = coletar_noticias()
    enviar_email(noticias)
    print("🏁 Fim.")
