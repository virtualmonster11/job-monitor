# 🔔 Job Monitor — Free Hourly Job Alerts

Monitors 100 company career pages every hour and sends Telegram alerts when new jobs are posted. Runs on **GitHub Actions — completely free, forever**.

---

## 📁 File Structure

```
job-monitor/
├── .github/
│   └── workflows/
│       └── monitor.yml       ← GitHub Actions schedule
├── companies.json            ← List of companies to watch
├── monitor.py                ← Main script
├── requirements.txt          ← Python dependencies
├── snapshots.json            ← Auto-generated, stores page hashes
└── monitor_log.txt           ← Auto-generated, run logs
```

---

## 🚀 Setup Steps

### STEP 1 — Create a GitHub Account
Go to https://github.com and sign up (free).

---

### STEP 2 — Create a New PUBLIC Repository
- Click **"New repository"**
- Name it: `job-monitor`
- Set visibility to **Public** ← Important! Public repos get free unlimited Actions minutes
- Click **Create repository**

---

### STEP 3 — Upload All Files
Upload these files to your repo (drag & drop on GitHub):
- `monitor.py`
- `companies.json`
- `requirements.txt`

Then create the folder path `.github/workflows/` and upload `monitor.yml` inside it.

**Or use Git:**
```bash
git clone https://github.com/YOUR_USERNAME/job-monitor
cd job-monitor
# copy all files here
git add .
git commit -m "Initial setup"
git push
```

---

### STEP 4 — Create a Telegram Bot (2 minutes)

1. Open Telegram and search for **@BotFather**
2. Send: `/newbot`
3. Give it a name (e.g. `My Job Alert Bot`)
4. Give it a username (e.g. `myjobalert_bot`)
5. BotFather gives you a **token** like:
   ```
   7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   Copy this — it's your `TG_TOKEN`

6. Now search for **@userinfobot** on Telegram
7. Send any message to it — it replies with your **Chat ID** (a number like `912345678`)
   That's your `TG_CHAT_ID`

8. **Start your bot**: Search your bot username and click **Start**

---

### STEP 5 — Add Secrets to GitHub

1. Go to your GitHub repo
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add:

| Name | Value |
|------|-------|
| `TG_TOKEN` | Your Telegram bot token |
| `TG_CHAT_ID` | Your Telegram chat ID |

---

### STEP 6 — Run it Manually First (Test)

1. Go to your repo → click **Actions** tab
2. Click **Job Monitor** in the left sidebar
3. Click **Run workflow** → **Run workflow**
4. Watch it run — takes ~2–3 minutes
5. If setup is correct, you'll get a Telegram message:
   > ✅ Job Monitor is now active! Tracking 20 companies.

---

### STEP 7 — It Runs Automatically Every Hour ✅

After the first run, GitHub Actions runs it every hour automatically.
You'll get Telegram alerts whenever any job page changes.

---

## ✏️ How to Add More Companies

Edit `companies.json` and add entries like:
```json
{"name": "YourCompany", "url": "https://company.com/careers"}
```

Always use the **direct job listing URL**, not the homepage.

---

## 💡 Tips

- **JS-heavy pages** (React/Angular career sites): The hash may change on every load due to dynamic content. If you get too many false alerts for a company, remove it from `companies.json`.
- **Rate limits**: The script waits 1 second between requests to avoid being blocked.
- **Logs**: Check `monitor_log.txt` in your repo to see full run history.
- **Manual trigger**: You can always trigger a run manually from the Actions tab.

---

## ✅ Cost Breakdown

| Service | Cost |
|---------|------|
| GitHub Actions (public repo) | Free (unlimited minutes) |
| Telegram Bot | Free |
| Python + libraries | Free |
| **Total** | **$0 forever** |
