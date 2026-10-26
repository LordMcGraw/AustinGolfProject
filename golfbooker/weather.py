"""Forecasts from the National Weather Service (api.weather.gov, free, no key)."""
from __future__ import annotations

from datetime import datetime

import requests

from .models import Course, TeeTime

HEADERS = {"User-Agent": "AustinGolfBooker/0.1 (personal tee time checker)", "Accept": "application/geo+json"}


class Forecasts:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.update(HEADERS)
        self._grid: dict[tuple[float, float], str] = {}
        self._periods: dict[str, tuple[list[dict], list[dict]]] = {}

    def _get(self, url: str) -> dict:
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _forecast_urls(self, lat: float, lon: float) -> str:
        key = (round(lat, 3), round(lon, 3))
        if key not in self._grid:
            self._grid[key] = self._get(f"https://api.weather.gov/points/{key[0]},{key[1]}")["properties"]["forecast"]
        return self._grid[key]

    def periods(self, course: Course) -> tuple[list[dict], list[dict]]:
        """(hourly periods, 12-hour periods) for the course's forecast grid."""
        url = self._forecast_urls(course.lat, course.lon)
        if url not in self._periods:
            hourly = self._get(url + "/hourly")["properties"]["periods"]
            daily = self._get(url)["properties"]["periods"]
            self._periods[url] = (hourly, daily)
        return self._periods[url]

    def for_time(self, course: Course, when: datetime) -> dict:
        hourly, daily = self.periods(course)
        for p in hourly:
            if datetime.fromisoformat(p["startTime"]) <= when < datetime.fromisoformat(p["endTime"]):
                return summarize(p, hourly=True)
        # Past the hourly range (~6 days out): fall back to the daytime forecast.
        for p in daily:
            start = datetime.fromisoformat(p["startTime"])
            if p["isDaytime"] and start.date() == when.date():
                return summarize(p, hourly=False)
        return {}

    def attach(self, course: Course, tee_times: list[TeeTime]) -> None:
        for tt in tee_times:
            tt.weather = self.for_time(course, tt.start)

    def daily_outlook(self, course: Course) -> list[dict]:
        """Daytime forecasts for the coming week, for the dashboard header."""
        _, daily = self.periods(course)
        return [
            {"date": p["startTime"][:10], **summarize(p, hourly=False)}
            for p in daily
            if p["isDaytime"]
        ]


def summarize(period: dict, hourly: bool) -> dict:
    return {
        "temp_f": period["temperature"],
        "precip_pct": (period.get("probabilityOfPrecipitation") or {}).get("value") or 0,
        "wind": f'{period.get("windSpeed", "")} {period.get("windDirection", "")}'.strip(),
        "summary": period["shortForecast"],
        "hourly": hourly,
    }
