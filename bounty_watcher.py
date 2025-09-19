import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Variabili d'ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SEEN_FILE = "/mnt/data/seen.json"
USER_AGENT = "bounty-watcher/1.0 (+https://github.com/MicheleMessina-debug)"

# Lista siti bug bounty
SITES = [
    
    {"name": "YesWeHack", "url": "https://yeswehack.com/programs", "parser": "yeswehack"}
]

HEADERS = {"User-Agent": USER_AGENT}

# Load / Save programmi già visti
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    return {"seen": []}

def save_seen(data):
    with open(SEEN_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Funzione per inviare Telegram
def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram token / chat id mancanti.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=15)
        if not r.ok:
            print("Errore invio telegram:", r.status_code, r.text)
    except Exception as e:
        print("Eccezione invio telegram:", e)

# Funzione per fetch delle pagine
def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.text
        print(f"Fetch {url} -> {r.status_code}")
        return ""
    except Exception as e:
        print("Fetch error:", e)
        return ""

def parse_yeswehack(html):
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("a.program-card") or soup.select("a[href*='/programs/']")
    results = []
    for it in items:
        title = it.get_text(strip=True)
        href = it.get("href")
        if href and title:
            if href.startswith("/"):
                href = "https://yeswehack.com" + href
            results.append({"id": href, "title": title, "url": href})
    return results

PARSERS = {
    "yeswehack": parse_yeswehack,
}

# Funzione principale
def run_once():
    data = load_seen()
    seen = set(data.get("seen", []))
    new_found = []

    for s in SITES:
        print(f"[{datetime.utcnow().isoformat()}] Controllo {s['name']} ...")
        html = fetch(s["url"])
        if not html:
            continue
        parser = PARSERS.get(s["parser"])
        if not parser:
            continue
        items = parser(html)
        for it in items:
            uid = it["id"]
            if uid not in seen:
                seen.add(uid)
                new_found.append((s["name"], it))

    save_seen({"seen": list(seen)})

    for site_name, it in new_found:
        text = f"📢 Nuovo programma su {site_name}\n{it['title']}\n{it['url']}"
        send_telegram(text)
        print("Notify:", it['title'])

    if not new_found:
        print("Nessun nuovo programma trovato.")
    return new_found

if __name__ == "__main__":
    # Test rapido Telegram
    run_once()


    
  



