"""Check every course, write the dashboard data, and email any new matches.

    python -m golfbooker.run [--no-email]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import timedelta

from .alerts import AlertLog, build_email, now_local, send
from .conditions import snapshot
from .config import ROOT, load_courses, load_settings
from .filters import matches
from .readers import ReaderUnavailable, read_course
from .weather import Forecasts

log = logging.getLogger("golfbooker")
DATA_FILE = ROOT / "site" / "data" / "teetimes.json"
ALERT_LOG = ROOT / "state" / "alerted.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-email", action="store_true", help="print alerts instead of sending them")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    settings = load_settings()
    search = settings["search"]
    courses = load_courses()
    now = now_local()
    days = [now.date() + timedelta(days=i) for i in range(search.get("days_ahead", 7))]
    forecasts = Forecasts()

    tee_times, course_rows = [], []
    for course in courses:
        row = {
            "id": course.id,
            "name": course.name,
            "platform": course.platform,
            "booking_url": course.booking_url,
            "notes": course.notes,
            "status": "ok",
            "message": "",
            "outlook": [],
            "conditions": {},
        }
        try:
            found = [tt for tt in read_course(course, days, search.get("players", 1)) if tt.start >= now]
            row["count"] = len(found)
            tee_times.extend(found)
        except ReaderUnavailable as e:
            row.update(status="unavailable", message=str(e))
            found = []
        except Exception as e:  # one broken site shouldn't stop the rest
            log.exception("%s failed", course.name)
            row.update(status="error", message=f"Check failed: {e.__class__.__name__}")
            found = []
        try:
            forecasts.attach(course, found)
            row["outlook"] = forecasts.daily_outlook(course)
        except Exception:
            log.exception("weather failed for %s", course.name)
        try:
            row["conditions"] = snapshot(course)
        except Exception:
            log.exception("reviews failed for %s", course.name)
        log.info("%-28s %-12s %s", course.name, row["status"], row.get("count", row["message"]))
        course_rows.append(row)

    tee_times.sort(key=lambda t: (t.start, t.course_id))
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps({
        "generated_at": now.isoformat(),
        "search": search,
        "courses": course_rows,
        "tee_times": [tt.to_json() for tt in tee_times],
    }, separators=(",", ":")))

    first_run = not ALERT_LOG.exists()
    alert_log = AlertLog(ALERT_LOG)
    new = alert_log.new([tt for tt in tee_times if matches(tt, search)])
    log.info("%d tee times, %d new matches", len(tee_times), len(new))
    if first_run:
        # Don't flood the inbox with everything already open; alert on changes from here on.
        log.info("First run: remembering current matches without emailing")
    elif new:
        by_id = {c.id: c for c in courses}
        to = os.environ.get("ALERT_TO", "")
        msg = build_email(new, by_id, to, os.environ.get("SMTP_USER", to), os.environ.get("DASHBOARD_URL", ""))
        if args.no_email or not os.environ.get("SMTP_PASSWORD"):
            print(msg)
            return  # not sent, so don't mark as alerted
        send(msg, settings["alerts"])
    alert_log.record(new, now)
    alert_log.save()

if __name__ == "__main__":
    main()
