"""
update_html.py
--------------
Fetches today's Google Calendar events and Notion to-dos,
then rewrites the <ul class="events"> and <ul class="todos"> lists in index.html.

Environment variables required (set as GitHub Actions secrets):
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
  GOOGLE_REFRESH_TOKEN
  NOTION_TOKEN
  NOTION_DATABASE_ID      – the 32-char ID of your Notion to-do database
  WORK_CALENDAR_IDS       – comma-separated calendar IDs to treat as "work"
  PERSONAL_CALENDAR_IDS   – comma-separated calendar IDs to treat as "personal"
  TIMEZONE_OFFSET         – hours offset from UTC, e.g. "-4" for EDT, "-5" for EST
"""

import os
import re
from datetime import datetime, timezone, timedelta

import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from bs4 import BeautifulSoup

# ── Timezone ──────────────────────────────────────────────────────────────────
tz_offset = int(os.environ.get("TIMEZONE_OFFSET", "-4"))  # default: EDT
LOCAL_TZ = timezone(timedelta(hours=tz_offset))

# ── Google Calendar ───────────────────────────────────────────────────────────

def get_calendar_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )
    return build("calendar", "v3", credentials=creds)


def fetch_events(service, calendar_id, category):
    now = datetime.now(LOCAL_TZ)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end   = now.replace(hour=23, minute=59, second=59, microsecond=0)

    result = service.events().list(
        calendarId=calendar_id,
        timeMin=day_start.isoformat(),
        timeMax=day_end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = []
    for item in result.get("items", []):
        if item.get("status") == "cancelled":
            continue

        raw_start = item["start"].get("dateTime", item["start"].get("date", ""))
        raw_end   = item["end"].get("dateTime",   item["end"].get("date", ""))

        if "T" in raw_start:
            # Parse with timezone awareness
            def parse_dt(s):
                # Handle offset like +00:00 or Z
                s = s.replace("Z", "+00:00")
                return datetime.fromisoformat(s).astimezone(LOCAL_TZ)
            fmt_start = parse_dt(raw_start).strftime("%H:%M")
            fmt_end   = parse_dt(raw_end).strftime("%H:%M")
        else:
            fmt_start = "All day"
            fmt_end   = ""

        # Look for a meeting link (Google Meet, Zoom, Teams)
        link = item.get("hangoutLink")
        if not link:
            conf = item.get("conferenceData", {})
            for ep in conf.get("entryPoints", []):
                if ep.get("entryPointType") == "video":
                    link = ep.get("uri")
                    break
        if not link:
            loc = item.get("location", "")
            if loc.startswith("https://"):
                link = loc

        events.append({
            "title":    item.get("summary", "Untitled"),
            "start":    fmt_start,
            "end":      fmt_end,
            "category": category,
            "link":     link,
        })

    return events


# ── Notion ────────────────────────────────────────────────────────────────────

def fetch_todos():
    token  = os.environ["NOTION_TOKEN"]
    db_id  = os.environ["NOTION_DATABASE_ID"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
        "Notion-Version": "2022-06-28",
    }

    # Fetch incomplete items only
    payload = {
        "filter": {
            "property": "Done",          # ← adjust if your checkbox column has a different name
            "checkbox": {"equals": False},
        }
    }

    resp = requests.post(
        f"https://api.notion.com/v1/databases/{db_id}/query",
        headers=headers,
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()

    todos = []
    for page in resp.json().get("results", []):
        props = page.get("properties", {})

        # Find the title (tries common column names)
        title = None
        for key in ["Name", "Task", "Title", "Todo", "To-do", "Item"]:
            if key in props:
                parts = props[key].get("title", [])
                if parts:
                    title = parts[0].get("plain_text", "").strip()
                    break

        if not title:
            continue

        # Determine work vs personal
        category = "personal"
        for key in ["Category", "Type", "Tag", "Label"]:
            if key in props:
                sel = props[key].get("select") or {}
                name = sel.get("name", "").lower()
                if "uni" in name.lower():
                    category = "work"
                break

        todos.append({"title": title, "category": category})

    return todos


# ── HTML building ─────────────────────────────────────────────────────────────

def event_li(ev):
    cat   = ev["category"]
    time_ = f"{ev['start']}–{ev['end']}" if ev["end"] else ev["start"]
    link  = f'<a href="{ev["link"]}">link</a>' if ev.get("link") else ""
    return (
        f'<li>'
        f'<span class="event-icon event-{cat}">{cat}</span>'
        f'<span class="label">{ev["title"]}</span>'
        f'<span class="time">{time_}</span>'
        f'{link}'
        f'</li>'
    )


def todo_li(todo):
    cat = todo["category"]
    return (
        f'<li class="todo">'
        f'<span class="todo-icon todo-{cat}">{cat}</span>'
        f'<span class="label">{todo["title"]}</span>'
        f'</li>'
    )


def no_event_li():
    return (
        '<li>'
        '<span class="event-icon event-personal">personal</span>'
        '<span class="label">No event YAYY</span>'
        '</li>'
    )


def no_todo_li():
    return (
        '<li class="todo">'
        '<span class="todo-icon todo-personal">personal</span>'
        '<span class="label">Nothing to do YAYYY</span>'
        '</li>'
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # --- Collect events ---
    service = get_calendar_service()
    all_events = []

    work_ids     = [x.strip() for x in os.environ.get("WORK_CALENDAR_IDS", "").split(",") if x.strip()]
    personal_ids = [x.strip() for x in os.environ.get("PERSONAL_CALENDAR_IDS", "primary").split(",") if x.strip()]

    for cal_id in work_ids:
        all_events.extend(fetch_events(service, cal_id, "work"))
    for cal_id in personal_ids:
        all_events.extend(fetch_events(service, cal_id, "personal"))

    # Sort by start time (all-day events go last)
    all_events.sort(key=lambda e: ("1" if e["start"] == "All day" else "0") + e["start"])

    # --- Collect todos ---
    todos = fetch_todos()

    # --- Build HTML snippets ---
    events_inner = "\n          ".join(event_li(e) for e in all_events) if all_events else no_event_li()
    todos_inner  = "\n          ".join(todo_li(t) for t in todos)       if todos       else no_todo_li()

    # --- Parse and patch index.html ---
    with open("index.html", "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    events_ul = soup.find("ul", class_="events")
    todos_ul  = soup.find("ul", class_="todos")

    events_ul.clear()
    for tag in BeautifulSoup(events_inner, "html.parser").contents:
        events_ul.append(tag)

    todos_ul.clear()
    for tag in BeautifulSoup(todos_inner, "html.parser").contents:
        todos_ul.append(tag)

    # Update the date stamp
    date_span = soup.find("span", id="receiptDate")
    if date_span:
        today = datetime.now(LOCAL_TZ)
        date_span.string = f"{today.month}/{today.day}/{today.year}"

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"✅  Updated index.html — {len(all_events)} event(s), {len(todos)} to-do(s)")


if __name__ == "__main__":
    main()
