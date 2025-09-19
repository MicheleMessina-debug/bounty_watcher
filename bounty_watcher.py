import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SEEN_FILE = "/mnt/data/seen.json"
USER_AGENT = "bounty-watcher/1.0 (+https://github.com/MicheleMessina-debug)"
HEADERS = {"User-Agent": USER_AGENT}

SITES = [
    {"name": "YesWeHack", "url": "https://yeswehack.com/programs", "parser": "yeswehack"}
]

def load_seen():
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"[{datetime.utcnow().isoformat()}] WARNING: File {SEEN_FILE} corrotto. Reset.")
            return {"seen": []}
    else:
        with open(SEEN_FILE, "w") as f:
            json.dump({"seen": []}, f, indent=2)
        return {"seen": []}

def save_seen(data):
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    with open(SEEN_FILE, "w") as f:
        json.dump(data, f, indent=2)

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[{datetime.utcnow().isoformat()}] Telegram token / chat id mancanti.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=15)
        if not r.ok:
            print(f"[{datetime.utcnow().isoformat()}] Errore invio telegram: {r.status_code} {r.text}")
    except Exception as e:
        print(f"[{datetime.utcnow().isoformat()}] Eccezione invio telegram:", e)

def fetch(url, retries=3, delay=5):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r.text
            else:
                print(f"[{datetime.utcnow().isoformat()}] Fetch {url} -> {r.status_code}")
        except Exception as e:
            print(f"[{datetime.utcnow().isoformat()}] Fetch error attempt {attempt+1}: {e}")
        time.sleep(delay)
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

def run_once():
    old_data = load_seen()
    seen = set(old_data.get("seen", []))
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

    if set(old_data.get("seen", [])) != seen:
        save_seen({"seen": list(seen)})

    for site_name, it in new_found:
        text = f"📢 Nuovo programma su {site_name}\n{it['title']}\n{it['url']}"
        send_telegram(text)
        print(f"[{datetime.utcnow().isoformat()}] Notify: {it['title']}")

    if not new_found:
        print(f"[{datetime.utcnow().isoformat()}] Nessun nuovo programma trovato.")
    return new_found

if __name__ == "__main__":
    run_once()


  



