# news_collector.py (Resend API - final)
import os, feedparser, requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_TO = os.environ.get("EMAIL_TO", "drbadiodefora@gmail.com")
if not RESEND_API_KEY:
    print("❌ RESEND_API_KEY não configurada.")
    exit(1)

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
    if 'published_parsed' in entry:
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

def enviar_email(noticias):
    if not noticias:
        print("Nenhuma notícia nova.")
        return
    assunto = f"📰 {len(noticias)} notícias sobre Cabo Verde – {datetime.now().strftime('%d/%m/%Y')}"
    html = f"<h2>🌍 Notícias sobre Cabo Verde</h2><p>{len(noticias)} notícia(s) nova(s).</p>"
    html += '<table border="1" cellpadding="8">'
    for n in noticias:
        html += f"<tr><td>{n['fonte']}</td><td>{n['data']}</td><td><a href='{n['link']}'>{n['titulo']}</a></td><td>{n['resumo']}</td></tr>"
    html += "</table>"
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

if __name__ == "__main__":
    print("🔍 Coletor iniciado...")
    noticias = coletar_noticias()
    enviar_email(noticias)
    print("🏁 Fim.")
