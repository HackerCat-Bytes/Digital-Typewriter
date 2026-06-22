# Shailly's Daily Typewriter — Setup Guide

Everything runs free and in your own accounts.  
Total setup time: ~25 minutes (one-time).

---

## Architecture

```
Google Calendar API ──┐
                       ├──► GitHub Actions (runs 7 AM daily)
Notion API ────────────┘         │
                                  ▼
                           update_html.py
                                  │
                                  ▼
                           index.html (committed & pushed)
                                  │
                                  ▼
                           GitHub Pages (your live website)
```

---

## Step 1 — Google Cloud Console (15 min)

1. Go to https://console.cloud.google.com and sign in with your Google account.
2. Click **"Select a project" → "New Project"**. Name it anything (e.g. *typewriter*).
3. In the left sidebar: **APIs & Services → Library**.  
   Search for **"Google Calendar API"** and click **Enable**.
4. Go to **APIs & Services → OAuth consent screen**.
   - User type: **External**
   - Fill in App name (anything), your email for support and developer contact.
   - Click **Save and Continue** through all steps.
   - On the **Test users** step, add your own Gmail address. Click **Save**.
5. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
   - Application type: **Desktop app**
   - Name: anything
   - Click **Create**, then **Download JSON**.
   - Rename the downloaded file to **`client_secret.json`**.

---

## Step 2 — Get your Google Refresh Token (one-time, run locally)

In VS Code terminal (in the same folder as `client_secret.json`):

```bash
pip install google-auth-oauthlib
python get_refresh_token.py
```

Your browser will open → sign into your Google account → click Allow.  
The terminal will print three values. **Copy all three** — you'll need them in Step 4.

You can now delete `client_secret.json` (don't commit it to GitHub).

---

## Step 3 — Notion Integration Token

1. Go to https://www.notion.so/my-integrations → **"New integration"**.
2. Name it *Typewriter*, select your workspace, click **Submit**.
3. Copy the **Internal Integration Token** (starts with `secret_...`).
4. Open your to-do Notion database page in Notion.
5. Click **"..." (top right) → Add connections → Typewriter** (your integration).
6. Copy the **database ID** from the URL:  
   `https://notion.so/your-workspace/**DATABASE_ID**?v=...`  
   It's the 32-character string before the `?`.

**Note:** The script expects your Notion database to have:
- A **title column** named one of: `Name`, `Task`, `Title`, `Todo`, `Item`
- A **checkbox column** named `Done` (for filtering incomplete tasks)
- *(Optional)* A **select column** named `Category` / `Type` / `Tag` — if a task's value contains "work", it gets the work icon; otherwise personal.

If your columns have different names, open `update_html.py` and adjust lines ~80-100.

---

## Step 4 — GitHub Secrets

In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**.

Add these secrets one by one:

| Secret name | Value |
|---|---|
| `GOOGLE_CLIENT_ID` | from Step 2 output |
| `GOOGLE_CLIENT_SECRET` | from Step 2 output |
| `GOOGLE_REFRESH_TOKEN` | from Step 2 output |
| `NOTION_TOKEN` | from Step 3 |
| `NOTION_DATABASE_ID` | from Step 3 (32-char ID) |
| `WORK_CALENDAR_IDS` | comma-separated Google Calendar IDs for work calendars |
| `PERSONAL_CALENDAR_IDS` | comma-separated Google Calendar IDs for personal calendars |

**Finding your Calendar IDs:**  
Go to Google Calendar → click the three dots next to a calendar → Settings.  
Scroll down to find **"Calendar ID"**. For your main calendar it's usually your Gmail address.  
Example: `WORK_CALENDAR_IDS = my-work-email@company.com`  
Example: `PERSONAL_CALENDAR_IDS = myemail@gmail.com,family-calendar@group.calendar.google.com`

---

## Step 5 — Add files to your repo

Copy these files into your repo root:
```
update_html.py
.github/
  workflows/
    daily-update.yml
```

Commit and push:
```bash
git add update_html.py .github/
git commit -m "add: daily typewriter automation"
git push
```

---

## Step 6 — Test it immediately

In your GitHub repo: **Actions tab → "Daily Typewriter Update" → Run workflow → Run workflow**.

Watch the logs. If it succeeds, it will commit an updated `index.html`.  
Then in VS Code:
```bash
git pull
# open index.html in your browser to verify
```

---

## Step 7 — Enable GitHub Pages

In your GitHub repo: **Settings → Pages**.
- Source: **Deploy from a branch**
- Branch: **main**, folder: **/ (root)**
- Click **Save**

Your site will be live at:  
`https://YOUR-USERNAME.github.io/YOUR-REPO-NAME/`

Every morning at 7 AM, GitHub Actions updates `index.html` and GitHub Pages automatically serves the new version. No other hosting needed.

---

## Timezone note

The workflow is set to `0 11 * * *` (11:00 UTC = 7:00 AM EDT).  
In winter (EST, UTC-5), change it to `0 12 * * *`.  
You can also just leave it at 11 UTC — it'll fire at 7 AM in summer and 6 AM in winter, which is fine.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `invalid_grant` error | Re-run `get_refresh_token.py` locally to get a fresh refresh token |
| Notion 401 error | Make sure you added the integration to your database (Step 3, item 5) |
| Events not showing | Double-check calendar IDs in GitHub Secrets — they're case-sensitive |
| Script finds 0 todos | Adjust the column name in `update_html.py` line ~85 to match your Notion property names |
| GitHub Pages not updating | Make sure the workflow has `permissions: contents: write` (already set) |
