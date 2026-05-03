# news_collector.py (Gmail TLS - porta 587)
import os, re, feedparser, smtplib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL_FROM = os.environ.get("EMAIL_FROM")
EMAIL_TO = os.environ.get("EMAIL_TO")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
if not all([EMAIL_FROM, EMAIL_TO, EMAIL_PASSWORD]):
    print("❌ Credenciais de e-mail não configuradas."); exit(1)

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
        if not pub or pub <= ultima: continue
        if pub > maior_data: maior_data = pub
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
    if not noticias: return
    assunto = f"📰 {len(noticias)} notícias sobre Cabo Verde – {datetime.now().strftime('%d/%m/%Y')}"
    html = f"<h2>🌍 Notícias sobre Cabo Verde</h2><table border='1' cellpadding='8'>"
    for n in noticias:
        html += f"</table><td>{n['fonte']}</td><td>{n['data']}</td><td><a href='{n['link']}'>{n['titulo']}</a></td><td>{n['resumo']}</td></tr>"
    html += "</table>"
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = assunto, EMAIL_FROM, EMAIL_TO
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

if __name__ == "__main__":
    print("🔍 Coletor iniciado...")
    enviar_email(coletar_noticias())
    print("🏁 Fim.")
