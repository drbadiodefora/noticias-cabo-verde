# news_collector.py
import os, feedparser, json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

GOOGLE_NEWS_URL = "https://news.google.com/rss/search?q=Cabo+Verde+OR+Cape+Verde+OR+Cap-Vert&hl=pt&gl=CV&ceid=CV:pt"
LAST_RUN_FILE = "last_news_run.txt"

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
        novas.append({
            "fonte": entry.get('source', {}).get('title', 'Google News'),
            "data": pub.strftime("%d/%m/%Y %H:%M"),
            "titulo": entry.get('title', 'Sem título'),
            "link": entry.get('link', ''),
            "resumo": entry.get('title', '')[:200]
        })
    save_last_run(maior_data if maior_data > ultima else agora)
    return novas

def gerar_html(noticias):
    if not noticias:
        return "<p>Nenhuma notícia nova.</p>"
    html = f"<h2>🌍 Notícias sobre Cabo Verde</h2><p>{len(noticias)} notícia(s) desde a última verificação.</p>"
    html += '<table border="1" cellpadding="8">'
    for n in noticias:
        html += f"<tr><td>{n['fonte']}</td><td>{n['data']}</td><td><a href='{n['link']}'>{n['titulo']}</a></td><td>{n['resumo']}</td></tr>"
    html += "</table>"
    return html

if __name__ == "__main__":
    noticias = coletar_noticias()
    html_content = gerar_html(noticias)
    # Guarda o conteúdo em ficheiro para a Action ler
    with open("email_content.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    # Também guarda o assunto e o número de notícias
    with open("email_subject.txt", "w", encoding="utf-8") as f:
        f.write(f"📰 {len(noticias)} notícias sobre Cabo Verde – {datetime.now().strftime('%d/%m/%Y')}")
    print("✅ Conteúdo preparado.")
