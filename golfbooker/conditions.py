"""Course-conditions snapshot from recent GolfNow player reviews."""
from __future__ import annotations

import re
from datetime import datetime, timedelta

import requests

from .models import Course
from .readers.base import USER_AGENT

REVIEWS_URL = "https://www.golfnow.com/api/courses/reviews"
RECENT_DAYS = 60

# Words players use when describing course condition, grouped under one label.
TOPICS = {
    "greens": r"\bgreens?\b",
    "aeration": r"\baerat|\bpunched\b|\bsanded\b",
    "fairways": r"\bfairways?\b",
    "bunkers": r"\bbunkers?\b|\bsand traps?\b",
    "wet / cart path only": r"\bwet\b|\bsoggy\b|\bcart ?path only\b|\b90 ?degree",
    "dry / burnt": r"\bdry\b|\bburn(?:t|ed)\b|\bbrown\b|\bhard pan\b",
    "pace of play": r"\bpace\b|\bslow\b|\bwait(?:ed|ing)?\b",
}


def snapshot(course: Course, session: requests.Session | None = None, today: datetime | None = None) -> dict:
    if not course.golfnow_facility:
        return {}
    session = session or requests.Session()
    resp = session.post(
        REVIEWS_URL,
        json={"facilityId": course.golfnow_facility, "pageNumber": 1, "pageSize": 20},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return summarize(resp.json()["reviewCollection"], today or datetime.now())


def summarize(collection: dict, today: datetime) -> dict:
    sub = {s["label"]: round(s["value"], 1) for s in collection.get("subratings") or []}
    cutoff = today - timedelta(days=RECENT_DAYS)
    recent = [r for r in collection.get("reviews") or [] if datetime.fromisoformat(r["reviewDate"][:19]) >= cutoff]
    mentions: dict[str, int] = {}
    for r in recent:
        text = f'{r.get("reviewTitle") or ""} {r.get("reviewText") or ""}'.lower()
        for label, pattern in TOPICS.items():
            if re.search(pattern, text):
                mentions[label] = mentions.get(label, 0) + 1
    return {
        "conditions_rating": sub.get("Course Conditions"),
        "pace_rating": sub.get("Pace of Play"),
        "recent_count": len(recent),
        "recent_avg": round(sum(r["rating"] for r in recent) / len(recent), 1) if recent else None,
        "mentions": dict(sorted(mentions.items(), key=lambda kv: -kv[1])),
        "reviews": [
            {
                "played": (r.get("dateOfPlay") or r["reviewDate"])[:10],
                "rating": r["rating"],
                "title": r.get("reviewTitle") or "",
                "text": _clip(r.get("reviewText") or "", 280),
            }
            for r in recent[:3]
            if r.get("reviewText")
        ],
        "source": "GolfNow reviews",
    }


def _clip(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"
