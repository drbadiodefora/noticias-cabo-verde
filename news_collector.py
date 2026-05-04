# news_collector.py (corrigido - sem conflito de nomes)
import os, re, feedparser, requests, html as html_escape
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_TO = os.environ.get("EMAIL_TO", "drbadiodefora@gmail.com")
if not RESEND_API_KEY:
    print("❌ RESEND_API_KEY não configurada.")
    exit(1)

GOOGLE_NEWS_URL = "https://news.google.com/rss/search?q=Cabo+Verde+OR+Cape+Verde+OR+Cap-Vert&hl=pt&gl=CV&ceid=CV:pt"
LAST_RUN_FILE = "last_news_run.txt"

# ============================================================
# DEFINIÇÃO DE TEMAS
# ============================================================
TEMAS = {
    "Política": ["eleição", "eleições", "governo", "parlamento", "presidente", "primeiro-ministro", "partido", "deputado", "assembleia", "voto", "campanha", "mpd", "paicv", "ucid"],
    "Economia": ["economia", "finanças", "empresa", "negócio", "turismo", "investimento", "crescimento", "pib", "inflação", "desemprego", "salário", "comércio", "banco"],
    "Saúde": ["saúde", "hospital", "médico", "doença", "covid", "vacina", "tratamento", "síndrome", "hantavírus", "surto", "doente", "sns"],
    "Desporto": ["desporto", "futebol", "selecção", "seleção", "jogo", "campeonato", "copa", "mundial", "atleta", "treinador", "clube"],
    "Internacional": ["internacional", "mundo", "global", "onu", "unidos", "exterior", "embaixada", "acordo internacional"],
    "Sociedade & Cultura": ["cultura", "arte", "música", "educação", "ensino", "universidade", "escola", "religião", "igreja", "tradição", "comunidade", "juventude", "mulher"],
    "Justiça & Segurança": ["justiça", "tribunal", "polícia", "crime", "segurança", "prisão", "advogado", "investigação", "corrupção", "violência"],
    "Ambiente & Clima": ["ambiente", "clima", "energia", "água", "resíduos", "proteção", "sustentabilidade"]
}

def classificar_titulo(titulo, resumo):
    texto = f"{titulo} {resumo}".lower()
    for tema, palavras in TEMAS.items():
        for palavra in palavras:
            if palavra in texto:
                return tema
    return "Outros"

# ============================================================
# COLETA DE NOTÍCIAS
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
        resumo = entry.get('summary', '')[:300]
        fonte = entry.get('source', {}).get('title', 'Google News')
        link = entry.get('link', '')
        data_str = pub.strftime("%d/%m/%Y %H:%M")
        tema = classificar_titulo(titulo, resumo)

        novas.append({
            "fonte": fonte,
            "data": pub,
            "data_str": data_str,
            "titulo": titulo,
            "link": link,
            "resumo": resumo or titulo[:200],
            "tema": tema
        })
    save_last_run(maior_data if maior_data > ultima else agora)
    return novas

# ============================================================
# ENVIO DE E-MAIL (CORRIGIDO)
# ============================================================
def enviar_email(noticias):
    if not noticias:
        print("Nenhuma notícia nova.")
        return

    grupos = defaultdict(list)
    for n in noticias:
        grupos[n["tema"]].append(n)

    # Ordenar cada grupo por data (mais recente primeiro = reverse)
    for tema in grupos:
        grupos[tema].sort(key=lambda x: x["data"], reverse=True)

    temas_ordenados = sorted(grupos.keys())  # A-Z

    assunto = f"📰 {len(noticias)} notícias sobre Cabo Verde – {datetime.now().strftime('%d/%m/%Y')}"

    # Construir HTML (variável chamada 'conteudo_html' para não conflitar)
    conteudo_html = []
    conteudo_html.append("<!DOCTYPE html>")
    conteudo_html.append("<html>")
    conteudo_html.append("<head><meta charset='UTF-8'></head>")
    conteudo_html.append("<body>")
    conteudo_html.append(f"<h2>🌍 Notícias sobre Cabo Verde (por tema)</h2>")
    conteudo_html.append(f"<p><strong>{len(noticias)}</strong> notícia(s) nova(s).</p>")

    for tema in temas_ordenados:
        noticias_tema = grupos[tema]
        conteudo_html.append(f"<h3>{tema} ({len(noticias_tema)})</h3>")
        conteudo_html.append('<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width:100%">')
        conteudo_html.append('<tr style="background-color:#f0f0f0"><th>Fonte</th><th>Data</th><th>Título</th><th>Resumo</th></tr>')
        for n in noticias_tema:
            fonte_esc = html_escape.escape(n['fonte'])
            titulo_esc = html_escape.escape(n['titulo'])
            resumo_esc = html_escape.escape(n['resumo'])
            link_esc = html_escape.escape(n['link'])
            conteudo_html.append(f"<tr>\n<td>{fonte_esc}</td>\n<td>{n['data_str']}</td>\n<td><a href='{link_esc}'>{titulo_esc}</a></td>\n<td>{resumo_esc}</td>\n</tr>")
        conteudo_html.append("</table><br>")

    conteudo_html.append("<p><small>📌 Relatório diário automático. Notícias agrupadas por tema (A-Z) e ordenadas da mais recente para a mais antiga.</small></p>")
    conteudo_html.append("</body></html>")
    html_final = "\n".join(conteudo_html)

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json={
                "from": "onboarding@resend.dev",
                "to": [EMAIL_TO],
                "subject": assunto,
                "html": html_final
            }
        )
        if resp.status_code == 200:
            print(f"✅ E‑mail enviado com {len(noticias)} notícias!")
        else:
            print(f"❌ Erro: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Exceção: {e}")

if __name__ == "__main__":
    print("🔍 Coletor iniciado...")
    noticias = coletar_noticias()
    enviar_email(noticias)
    print("🏁 Fim.")
