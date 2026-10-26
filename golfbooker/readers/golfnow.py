from __future__ import annotations

import time
from datetime import date, datetime

from ..models import AUSTIN, Course, TeeTime
from .base import Reader, ReaderUnavailable

SEARCH_URL = "https://www.golfnow.com/api/tee-times/tee-time-results"
PLAYER_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4}


def parse_player_rule(rule: str) -> tuple[int, int]:
    """GolfNow describes allowed group sizes as e.g. 'TwoThreeFour' or 'Any'."""
    counts = [n for word, n in PLAYER_WORDS.items() if word in rule]
    if not counts:
        return 1, 4
    return min(counts), max(counts)


class GolfNowReader(Reader):
    """Tee times listed on GolfNow (the same inventory TeeOff and TeeItUp show).

    Uses the JSON endpoint behind golfnow.com's facility search page.
    """

    def search(self, facility_id: int, day: date) -> list[dict]:
        body = {
            "SearchType": 1,  # single facility
            "FacilityId": facility_id,
            "Date": day.strftime("%b %d %Y"),
            "PageSize": 200,
            "PageNumber": 0,
            "SortBy": "Date",
            "SortDirection": 0,
            "SortByRollup": "Date.MinDate",
            "View": "Grouping",
            "Players": "0",
            "Holes": "3",  # any
            "PriceMin": "0",
            "PriceMax": "10000",
            "RateType": "all",
            "TimeMin": "10",  # half-hour steps: 10 = 5:00 am, 42 = 9:00 pm
            "TimeMax": "42",
            "FacilityType": 0,
            "ExcludeFeaturedFacilities": True,
            "TeeTimeCount": 15,
        }
        resp = self.session.post(SEARCH_URL, json=body, timeout=30)
        if resp.status_code != 200:
            raise ReaderUnavailable(f"GolfNow returned HTTP {resp.status_code}")
        return resp.json()["ttResults"]["teeTimes"]

    def read(self, course: Course, days: list[date], players: int) -> list[TeeTime]:
        if not course.golfnow_facility:
            raise ReaderUnavailable("No GolfNow facility id configured")
        out: list[TeeTime] = []
        for i, day in enumerate(days):
            if i:
                time.sleep(0.5)  # be gentle with the site
            for raw in self.search(course.golfnow_facility, day):
                out.extend(self.parse(course, raw))
        return out

    @staticmethod
    def parse(course: Course, raw: dict) -> list[TeeTime]:
        # GolfNow labels local course time as UTC; take the wall-clock part.
        wall = raw["time"]["date"][:19]
        start = datetime.fromisoformat(wall).replace(tzinfo=AUSTIN)
        by_holes: dict[int, TeeTime] = {}
        for rate in raw["teeTimeRates"]:
            holes = rate["holeCount"]
            lo, hi = parse_player_rule(rate.get("playerRule") or raw.get("playerRule", "Any"))
            price = (rate.get("singlePlayerPrice") or {}).get("greensFees", {}).get("value")
            current = by_holes.get(holes)
            # Several rates can share a slot (e.g. senior); keep the widest player range, then the lowest price.
            if current and (current.max_players - current.min_players, -(current.price or 1e9)) >= (hi - lo, -(price or 1e9)):
                continue
            by_holes[holes] = TeeTime(
                course_id=course.id,
                start=start,
                min_players=lo,
                max_players=hi,
                holes=holes,
                price=price,
                booking_url="https://www.golfnow.com" + rate.get("detailUrl", raw["detailUrl"]),
                source="golfnow",
            )
        return list(by_holes.values())
