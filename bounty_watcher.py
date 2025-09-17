#!/usr/bin/env python3
"""
bounty_watcher.py
Monitora le pagine pubbliche di HackerOne / Bugcrowd / Intigriti / YesWeHack
e invia notifiche Telegram per nuovi programmi.
Config via env vars:
  TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
Uso: python3 bounty_watcher.py
Mantiene 'seen.json' con gli id/url già notificati.
"""
import os
import time
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SEEN_FILE = "seen.json"
USER_AGENT = "bounty-watcher/1.0 (+https://github.com/MicheleMessina-debug)"

SITES = [
    {
        "name": "HackerOne",
        "url": "https://hackerone.com/bug-bounty-programs",
        "parser": "hackerone"
    },
    {
        "name": "Bugcrowd",
        "url": "https://www.bugcrowd.com/programs/",
        "parser": "bugcrowd"
    },
    {
        "name": "Intigriti",
        "url": "https://www.intigriti.com/researchers/bug-bounty-programs",
        "parser": "intigriti"
    },
    {
        "name": "YesWeHack",
        "url": "https://yeswehack.com/programs",
        "parser": "yeswehack"
    }
]

HEADERS = {"User-Agent": USER_AGENT}

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    return {"seen": []}

def save_seen(data):
    with open(SEEN_FILE, "w") as f:
        json.dump(data, f, indent=2)

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram token / chat id mancanti.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": False}
    try:
        r = requests.post(url, json=payload, timeout=15)
        if not r.ok:
            print("Errore invio telegram:", r.status_code, r.text)
    except Exception as e:
        print("Eccezione invio telegram:", e)

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.text
        else:
            print(f"Fetch {url} -> {r.status_code}")
            return ""
    except Exception as e:
        print("Fetch error:", e)
        return ""

def parse_hackerone(html):
    # Semplice estrazione: titoli e link delle card di programmi
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("a.program-listing-card__link") or soup.select("a.d-block")
    results = []
    for c in cards:
        title = c.get_text(strip=True)
        href = c.get("href")
        if href and title:
            if href.startswith("/"):
                href = "https://hackerone.com" + href
            results.append({"id": href, "title": title, "url": href})
    return results

def parse_intigriti(html):
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("a.program-card") or soup.select("a.card")
    results = []
    for it in items:
        title = it.select_one(".title") or it.get_text(strip=True)
        href = it.get("href")
        if href and title:
            if href.startswith("/"):
                href = "https://www.intigriti.com" + href
            results.append({"id": href, "title": title.get_text(strip=True) if hasattr(title, 'get_text') else title, "url": href})
    return results

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

def parse_bugcrowd(html):
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("a.program-item") or soup.select("a[href*='/programs/']")
    results = []
    for it in items:
        title = it.get_text(strip=True)
        href = it.get("href")
        if href and title:
            if href.startswith("/"):
                href = "https://www.bugcrowd.com" + href
            results.append({"id": href, "title": title, "url": href})
    return results

PARSERS = {
    "hackerone": parse_hackerone,
    "intigriti": parse_intigriti,
    "yeswehack": parse_yeswehack,
    "bugcrowd": parse_bugcrowd
}

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
    # Salva lo stato
    save_seen({"seen": list(seen)})
    # Notifica i nuovi
    for site_name, it in new_found:
        text = f"📢 *Nuovo programma* su {site_name}\n\n*{it['title']}*\n{it['url']}"
        # Telegram accepts MarkdownV2 or simple text; here we use simple text
        send_telegram(text)
        print("Notify:", it['title'])
    if not new_found:
        print("Nessun nuovo programma trovato.")
    return new_found

if __name__ == "__main__":
    send_telegram("📢 Test rapido: nuovo programma simulato\nhttps://example.com")
    run_once()


