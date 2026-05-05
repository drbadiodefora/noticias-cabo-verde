# news_collector.py (com coluna Fonte)
import os
import re
import feedparser
import requests
import html as html_escape
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from collections import defaultdict

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_TO = os.environ.get("EMAIL_TO", "drbadiodefora@gmail.com")
if not RESEND_API_KEY:
    print("❌ RESEND_API_KEY não configurada.")
    exit(1)

LAST_RUN_FILE = "last_news_run.txt"

# ============================================================
# LISTA DE FEEDS
# ============================================================
FEEDS = [
    {"url": "https://news.google.com/rss/search?q=Cabo+Verde+OR+Cape+Verde+OR+Cap-Vert&hl=pt&gl=CV&ceid=CV:pt", "nome": "Google News"},
    {"url": "https://www.inforpress.cv/rss", "nome": "Inforpress"},
    {"url": "https://www.expressodasilhas.cv/feed", "nome": "Expresso das Ilhas"},
    {"url": "https://www.rtc.cv/feed", "nome": "RTC"},
    {"url": "https://www.anacao.cv/feed", "nome": "A Nação"},
    {"url": "https://www.oceanpress.cv/feed", "nome": "Oceanpress"},
    {"url": "https://noticias.sapo.cv/rss", "nome": "Sapo Notícias CV"},
    {"url": "https://www.bbc.com/portuguese/africa/index.xml", "nome": "BBC África (português)"},
    {"url": "https://rss.dw.com/rdf/rss-por-africa", "nome": "DW África"},
    {"url": "https://www.voaportugues.com/api/zigbee_news", "nome": "VOA Português"},
    {"url": "https://www.france24.com/pt/africa/rss", "nome": "France 24 África"},
]

# ============================================================
# TEMAS
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
    for categoria, palavras in TEMAS.items():
        for palavra in palavras:
            if palavra in texto:
                return categoria
    return "Outros"

def limpar_html(texto):
    if not texto:
        return ""
    soup = BeautifulSoup(texto, "html.parser")
    return ' '.join(soup.get_text().split())

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
    todas = []
    links_vistos = set()
    maior_data = ultima

    for feed_info in FEEDS:
        url = feed_info["url"]
        nome_fonte = feed_info["nome"]
        print(f"📡 A processar {nome_fonte}...")
        try:
            feed = feedparser.parse(url, agent="Mozilla/5.0")
        except Exception as e:
            print(f"   ❌ Erro ao aceder: {e}")
            continue

        for entry in feed.entries:
            pub = extrair_data(entry)
            if pub is None:
                continue
            if pub <= ultima:
                continue
            if pub > maior_data:
                maior_data = pub

            titulo = entry.get('title', 'Sem título')
            link = entry.get('link', '')
            if link in links_vistos:
                continue
            links_vistos.add(link)

            resumo_raw = entry.get('summary', '')
            if resumo_raw:
                resumo_limpo = limpar_html(resumo_raw)[:300]
            else:
                resumo_limpo = titulo[:200]

            categoria = classificar_titulo(titulo, resumo_limpo)
            data_str = pub.strftime("%d/%m/%Y %H:%M")

            todas.append({
                "categoria": categoria,
                "data": pub,
                "data_str": data_str,
                "titulo": titulo,
                "link": link,
                "fonte": nome_fonte
            })
            print(f"   ✅ {pub.strftime('%d/%m %H:%M')} - {titulo[:60]}...")

    save_last_run(maior_data if maior_data > ultima else agora)
    return todas

def enviar_email(noticias):
    if not noticias:
        print("Nenhuma notícia nova.")
        return

    noticias_ordenadas = sorted(noticias, key=lambda x: x["data"], reverse=True)
    noticias_ordenadas = sorted(noticias_ordenadas, key=lambda x: x["categoria"])

    assunto = f"Notícias de Cabo Verde - {datetime.now().strftime('%d/%m/%Y')}"
    data_hoje = datetime.now().strftime("%d/%m/%Y")

    style = """
    <style>
        .news-table { border-collapse: collapse; width: 100%; }
        .news-table th, .news-table td { border: 1px solid #ddd; padding: 8px; vertical-align: top; }
        .news-table th { background-color: #f0f0f0; text-align: left; }
        .col-categoria { width: 15%; }
        .col-data { width: 12%; white-space: nowrap; min-width: 105px; }
        .col-fonte { width: 18%; }
        .col-titulo { width: 55%; word-wrap: break-word; white-space: normal; }
    </style>
    """

    introducao = """
    <p><strong>Notícias de Cabo Verde</strong> é um projeto IA da autoria de <strong>Rui Sanches (drbadiodefora)</strong> que consiste em recolher e ordenar notícias em todo o mundo sobre Cabo Verde e enviar por email ao destinatário por ordem de assunto e data.</p>
    """

    html_parts = [
        "<!DOCTYPE html>", "<html>", "<head><meta charset='UTF-8'>", style, "</head>", "<body>",
        f"<h2>🌍 Notícias de Cabo Verde</h2>", introducao,
        f"<p><strong>{len(noticias)}</strong> notícia(s) nova(s) – {data_hoje}</p>",
        '<table class="news-table">',
        '<tr><th class="col-categoria">Categoria</th><th class="col-data">Data</th><th class="col-fonte">Fonte</th><th class="col-titulo">Título</th></tr>'
    ]

    for n in noticias_ordenadas:
        cat_esc = html_escape.escape(n['categoria'])
        data_str = n['data_str']
        fonte_esc = html_escape.escape(n['fonte'])
        titulo_esc = html_escape.escape(n['titulo'])
        link_esc = html_escape.escape(n['link'])
        html_parts.append(f"<tr><td class='col-categoria'>{cat_esc}</td><td class='col-data'>{data_str}</td><td class='col-fonte'>{fonte_esc}</td><td class='col-titulo'><a href='{link_esc}'>{titulo_esc}</a></td></tr>")

    html_parts.append("</table><p>Rui Sanches &copy; 2026 - todos os direitos reservados.</p></body></html>")
    html_final = "\n".join(html_parts)

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json={"from": "onboarding@resend.dev", "to": [EMAIL_TO], "subject": assunto, "html": html_final}
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
