# news_collector.py
import os
import re
import feedparser
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ============================================================
# CONFIGURAÇÕES (via variáveis de ambiente)
# ============================================================
EMAIL_FROM = os.environ.get("EMAIL_FROM")
EMAIL_TO = os.environ.get("EMAIL_TO")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

# Pesquisa combinada no Google News
GOOGLE_NEWS_URL = "https://news.google.com/rss/search?q=Cabo+Verde+OR+Cape+Verde+OR+Cap-Vert&hl=pt&gl=CV&ceid=CV:pt"
LAST_RUN_FILE = "last_news_run.txt"

# ============================================================
# FUNÇÕES
# ============================================================
def load_last_run():
    try:
        with open(LAST_RUN_FILE, "r") as f:
            return datetime.fromisoformat(f.read().strip())
    except:
        # Primeira execução: recolhe dos últimos 3 dias para não perder nada
        return (datetime.now(ZoneInfo("Atlantic/Cape_Verde")) - timedelta(days=3)).replace(hour=0, minute=0, second=0)

def save_last_run(dt):
    with open(LAST_RUN_FILE, "w") as f:
        f.write(dt.isoformat())

def extrair_data(entry):
    if 'published_parsed' in entry and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Atlantic/Cape_Verde"))
    if 'updated_parsed' in entry and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Atlantic/Cape_Verde"))
    return None

def coletar_noticias():
    ultima = load_last_run()
    agora = datetime.now(ZoneInfo("Atlantic/Cape_Verde"))
    novas = []
    maior_data = ultima

    print(f"🔍 Última verificação: {ultima.strftime('%d/%m/%Y %H:%M')}")
    feed = feedparser.parse(GOOGLE_NEWS_URL, agent="Mozilla/5.0")
    print(f"📡 Total de entradas no feed: {len(feed.entries)}")

    for entry in feed.entries:
        pub = extrair_data(entry)
        if pub is None:
            continue
        if pub <= ultima:
            continue
        if pub > maior_data:
            maior_data = pub

        fonte = entry.get('source', {}).get('title', 'Google News')
        titulo = entry.get('title', 'Sem título')
        link = entry.get('link', '')
        data_str = pub.strftime("%d/%m/%Y %H:%M")
        resumo = titulo[:200]

        novas.append({
            "fonte": fonte,
            "data": data_str,
            "titulo": titulo,
            "link": link,
            "resumo": resumo
        })

        print(f"   ✅ {data_str} - {titulo[:60]}...")

    save_last_run(maior_data if maior_data > ultima else agora)
    return novas

def enviar_email(noticias):
    if not noticias:
        print("Nenhuma notícia nova. E‑mail não enviado.")
        return

    assunto = f"📰 {len(noticias)} notícia(s) sobre Cabo Verde – {datetime.now().strftime('%d/%m/%Y')}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body>
        <h2>🌍 Notícias sobre Cabo Verde (fontes globais)</h2>
        <p><strong>{len(noticias)}</strong> notícia(s) desde a última verificação.</p>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width:100%">
            <thead style="background-color: #f0f0f0;">
                <tr>
                    <th>Fonte</th>
                    <th>Data</th>
                    <th>Título</th>
                    <th>Resumo</th>
                </tr>
            </thead>
            <tbody>
    """
    for n in noticias:
        html += f"""
            <tr>
                <td>{n['fonte']}</td>
                <td>{n['data']}</td>
                <td><a href="{n['link']}">{n['titulo']}</a></td>
                <td>{n['resumo']}</td>
            </tr>
        """
    html += """
            </tbody>
        </table>
        <p><small>📌 Gerado automaticamente por GitHub Actions.</small></p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        print("✅ E‑mail enviado.")
    except Exception as e:
        print(f"❌ Erro ao enviar e‑mail: {e}")

# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================
if __name__ == "__main__":
    print("🔍 Coletor global de notícias iniciado...")
    noticias = coletar_noticias()
    enviar_email(noticias)
    print("🏁 Fim.")
