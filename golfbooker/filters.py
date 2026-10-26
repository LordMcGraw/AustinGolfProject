from __future__ import annotations

from datetime import time

from .models import TeeTime

DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _parse(hhmm: str) -> time:
    h, m = hhmm.split(":")
    return time(int(h), int(m))


def matches(tt: TeeTime, search: dict) -> bool:
    """True if a tee time fits the day, player and time-window settings."""
    days = search.get("days") or DAY_NAMES
    if DAY_NAMES[tt.start.weekday()] not in days:
        return False
    players = search.get("players", 1)
    if not (tt.min_players <= players <= tt.max_players):
        return False
    windows = search.get("time_windows") or [["00:00", "23:59"]]
    t = tt.start.time()
    return any(_parse(a) <= t <= _parse(b) for a, b in windows)
