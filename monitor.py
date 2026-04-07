import requests
import json
import hashlib
import os
import time
from bs4 import BeautifulSoup
from datetime import datetime

SNAPSHOTS_FILE = "snapshots.json"
COMPANIES_FILE = "companies.json"
LOG_FILE       = "monitor_log.txt"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ─── LOGGING ──────────────────────────────────────────────
def log(msg):
    ts   = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ─── TELEGRAM ─────────────────────────────────────────────
def send_telegram(message: str):
    token   = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id:
        print("⚠️  Telegram creds missing.")
        return
    url    = f"https://api.telegram.org/bot{token}/sendMessage"
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    for chunk in chunks:
        try:
            r = requests.post(url, data={"chat_id": chat_id, "text": chunk,
                                          "parse_mode": "Markdown"}, timeout=10)
            if r.status_code != 200:
                print(f"Telegram error: {r.text}")
        except Exception as e:
            print(f"Telegram send failed: {e}")

# ─── GREENHOUSE API ────────────────────────────────────────
def get_greenhouse_jobs(slug: str) -> set:
    """Returns set of job titles from Greenhouse API - covers ALL pages."""
    url  = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        r    = requests.get(url, headers=HEADERS, timeout=20)
        data = r.json()
        jobs = data.get("jobs", [])
        return {f"{j['title']} | {j.get('location', {}).get('name', '')}" for j in jobs}
    except Exception as e:
        print(f"  ❌ Greenhouse API error for {slug}: {e}")
        return set()

# ─── LEVER API ────────────────────────────────────────────
def get_lever_jobs(slug: str) -> set:
    """Returns set of job titles from Lever API - covers ALL pages."""
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        r    = requests.get(url, headers=HEADERS, timeout=20)
        data = r.json()
        if isinstance(data, list):
            return {f"{j.get('text','')} | {j.get('categories', {}).get('location', '')}" for j in data}
        return set()
    except Exception as e:
        print(f"  ❌ Lever API error for {slug}: {e}")
        return set()

# ─── WORKDAY SCRAPE ───────────────────────────────────────
def get_workday_jobs(url: str) -> set:
    """
    Workday pages are JS-heavy so we hash the HTML.
    We try multiple pages by incrementing offset.
    """
    all_text = ""
    offsets  = [0, 20, 40, 60]          # Covers up to ~80 jobs
    for offset in offsets:
        try:
            page_url = f"{url}?q=&startIndex={offset}"
            r        = requests.get(page_url, headers=HEADERS, timeout=20)
            soup     = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "meta", "link"]):
                tag.decompose()
            all_text += soup.get_text(separator=" ", strip=True)
            time.sleep(0.5)
        except Exception as e:
            print(f"  ⚠️ Workday page error at offset {offset}: {e}")
    if all_text:
        return {hashlib.md5(all_text.encode("utf-8", errors="replace")).hexdigest()}
    return set()

# ─── HTML SCRAPE WITH PAGINATION ─────────────────────────
def get_html_jobs(url: str, max_pages: int = 5) -> set:
    """
    Scrapes HTML career page across multiple pagination patterns.
    Returns a hash-based set so any page change triggers an alert.
    """
    all_text     = ""
    seen_hashes  = set()

    # Common pagination URL patterns to try
    page_patterns = [
        lambda base, p: f"{base}?page={p}",
        lambda base, p: f"{base}?start={( p-1)*10}",
        lambda base, p: f"{base}/{p}",
        lambda base, p: f"{base}?pg={p}",
    ]

    for page in range(1, max_pages + 1):
        urls_to_try = [pat(url, page) for pat in page_patterns] if page > 1 else [url]

        for page_url in urls_to_try:
            try:
                r    = requests.get(page_url, headers=HEADERS, timeout=20)
                if r.status_code not in (200, 301, 302):
                    continue
                soup = BeautifulSoup(r.text, "html.parser")
                for tag in soup(["script", "style", "meta", "link", "noscript"]):
                    tag.decompose()
                page_text = soup.get_text(separator=" ", strip=True)
                page_hash = hashlib.md5(page_text.encode("utf-8", errors="replace")).hexdigest()

                # If we've seen this hash before, stop paginating
                if page_hash in seen_hashes:
                    return {hashlib.md5(all_text.encode()).hexdigest()} if all_text else set()

                seen_hashes.add(page_hash)
                all_text += page_text
                time.sleep(0.5)
                break  # Successfully fetched this page, move to next page number

            except Exception:
                continue

    if all_text:
        return {hashlib.md5(all_text.encode("utf-8", errors="replace")).hexdigest()}
    return set()

# ─── DISPATCH ─────────────────────────────────────────────
def get_jobs(company: dict) -> set:
    ctype = company.get("type", "html")
    if ctype == "greenhouse":
        return get_greenhouse_jobs(company["slug"])
    elif ctype == "lever":
        return get_lever_jobs(company["slug"])
    elif ctype == "workday":
        return get_workday_jobs(company["url"])
    else:
        return get_html_jobs(company["url"])

# ─── SNAPSHOTS ────────────────────────────────────────────
def load_snapshots() -> dict:
    if os.path.exists(SNAPSHOTS_FILE):
        with open(SNAPSHOTS_FILE) as f:
            return json.load(f)
    return {}

def save_snapshots(data: dict):
    with open(SNAPSHOTS_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ─── MAIN ─────────────────────────────────────────────────
def main():
    log("=" * 60)
    log("Job Monitor started")

    with open(COMPANIES_FILE) as f:
        companies = json.load(f)

    snapshots   = load_snapshots()
    is_first    = len(snapshots) == 0
    changes     = []
    errors      = []

    for i, company in enumerate(companies, 1):
        name  = company["name"]
        ctype = company.get("type", "html")
        url   = company.get("url") or f"https://boards-api.greenhouse.io/v1/boards/{company.get('slug')}/jobs"
        print(f"  [{i}/{len(companies)}] {name} ({ctype})")

        current = get_jobs(company)

        if not current:
            errors.append(name)
            continue

        # For API-based: compare job title sets → show exactly what's new
        # For HTML/Workday: compare hashes → show "page changed"
        old_raw = snapshots.get(name)

        if old_raw is None:
            log(f"  📌 First snapshot: {name} ({len(current)} entries)")
        else:
            old = set(old_raw) if isinstance(old_raw, list) else {old_raw}
            added = current - old

            if ctype in ("greenhouse", "lever"):
                if added:
                    log(f"  🚨 NEW JOBS at {name}: {added}")
                    changes.append({
                        "name": name, "url": url,
                        "type": "api",
                        "new_jobs": list(added)
                    })
            else:
                if added:          # hash changed
                    log(f"  🚨 PAGE CHANGED: {name}")
                    changes.append({
                        "name": name, "url": url,
                        "type": "html",
                        "new_jobs": []
                    })

        # Store as list for API types, single string for hash-based
        if ctype in ("greenhouse", "lever"):
            snapshots[name] = list(current)
        else:
            snapshots[name] = list(current)[0] if current else ""

        time.sleep(1)

    save_snapshots(snapshots)
    log(f"Done. Checked {len(companies)} | Changes: {len(changes)} | Errors: {len(errors)}")

    # ── Notifications ──────────────────────────────────────
    if is_first:
        msg = (
            "✅ *Job Monitor Active!*\n\n"
            f"Tracking *{len(companies)} companies* paying 15+ LPA.\n"
            "You'll be notified whenever new jobs appear.\n\n"
            f"📊 Greenhouse API: fast & exact\n"
            f"📊 Lever API: fast & exact\n"
            f"📊 Workday/HTML: page-change detection\n\n"
            "⏰ Runs every hour automatically."
        )
        send_telegram(msg)

    elif changes:
        lines = ["🚨 *New Job Activity Detected!*\n"]
        for c in changes:
            if c["type"] == "api" and c["new_jobs"]:
                jobs_str = "\n  • ".join(c["new_jobs"][:5])  # Cap at 5 titles
                lines.append(f"🔔 *{c['name']}* — New Roles:\n  • {jobs_str}\n🔗 {c['url']}")
            else:
                lines.append(f"🔔 *{c['name']}* — Career page updated\n🔗 {c['url']}")
        if errors:
            lines.append(f"\n⚠️ Could not check: {', '.join(errors[:10])}")
        send_telegram("\n\n".join(lines))

    log("=" * 60)


if __name__ == "__main__":
    main()
