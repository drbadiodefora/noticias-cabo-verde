# news_collector.py (tabela única com 5 colunas)
import os, re, feedparser, requests, html as html_escape
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup  # para limpar HTML do resumo

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

def limpar_html(texto):
    """Remove tags HTML e normaliza espaços."""
    if not texto:
        return ""
    soup = BeautifulSoup(texto, "html.parser")
    return ' '.join(soup.get_text().split())

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
        resumo_raw = entry.get('summary', '')
        if resumo_raw:
            resumo_limpo = limpar_html(resumo_raw)[:300]
        else:
            resumo_limpo = titulo[:200]

        fonte = entry.get('source', {}).get('title', 'Google News')
        link = entry.get('link', '')
        data_str = pub.strftime("%d/%m/%Y %H:%M")
        tema = classificar_titulo(titulo, resumo_limpo)

        novas.append({
            "tema": tema,
            "fonte": fonte,
            "data": pub,
            "data_str": data_str,
            "titulo": titulo,
            "link": link,
            "resumo": resumo_limpo
        })
    save_last_run(maior_data if maior_data > ultima else agora)
    return novas

# ============================================================
# ENVIO DE E-MAIL (TABELA ÚNICA, 5 COLUNAS)
# ============================================================
def enviar_email(noticias):
    if not noticias:
        print("Nenhuma notícia nova.")
        return

    # Ordenar: primeiro por tema (A-Z), depois por data (mais recente primeiro)
    noticias_ordenadas = sorted(noticias, key=lambda x: (x["tema"], x["data"]), reverse=False)
    # O reverse=False para tema, mas a data fica crescente? Queremos data mais recente primeiro.
    # Como o sort é por (tema, data) ascendente, para inverter a data podemos fazer (tema, -timestamp) mas é mais simples ordenar duas vezes.
    # Vamos ordenar primeiro por data (mais recente primeiro) e depois estabilizar por tema, mas Python mantém ordem relativa para chaves iguais.
    # Melhor: ordenar por data decrescente e depois por tema.
    noticias_ordenadas = sorted(noticias, key=lambda x: x["data"], reverse=True)
    noticias_ordenadas = sorted(noticias_ordenadas, key=lambda x: x["tema"])

    assunto = f"📰 {len(noticias)} notícias sobre Cabo Verde – {datetime.now().strftime('%d/%m/%Y')}"

    # Construir tabela única
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head><meta charset='UTF-8'></head>",
        "<body>",
        f"<h2>🌍 Notícias sobre Cabo Verde (por tema)</h2>",
        f"<p><strong>{len(noticias)}</strong> notícia(s) nova(s).</p>",
        '<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width:100%">',
        '<tr style="background-color:#f0f0f0">',
        '<th>Categoria/Tema</th>',
        '<th>Fonte</th>',
        '<th>Data</th>',
        '<th>Título</th>',
        '<th>Resumo</th>',
        '</tr>'
    ]

    for n in noticias_ordenadas:
        tema_esc = html_escape.escape(n['tema'])
        fonte_esc = html_escape.escape(n['fonte'])
        data_str = n['data_str']
        titulo_esc = html_escape.escape(n['titulo'])
        link_esc = html_escape.escape(n['link'])
        resumo_esc = html_escape.escape(n['resumo'])

        html_parts.append(f"<tr>\n")
        html_parts.append(f"<td>{tema_esc}</td>\n")
        html_parts.append(f"<td>{fonte_esc}</td>\n")
        html_parts.append(f"<td>{data_str}</td>\n")
        html_parts.append(f"<td><a href='{link_esc}'>{titulo_esc}</a></td>\n")
        html_parts.append(f"<td>{resumo_esc}</td>\n")
        html_parts.append(f"</tr>\n")

    html_parts.append("</table>")
    html_parts.append("<p><small>📌 Relatório diário automático. Notícias ordenadas por tema (A-Z) e, dentro do mesmo tema, da mais recente para a mais antiga.</small></p>")
    html_parts.append("</body></html>")

    html_final = "\n".join(html_parts)

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
    import sys
    # Instala BeautifulSoup se necessário (no GitHub Actions já está)
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("📦 Instalando BeautifulSoup...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
        from bs4 import BeautifulSoup

    noticias = coletar_noticias()
    enviar_email(noticias)
    print("🏁 Fim.")
