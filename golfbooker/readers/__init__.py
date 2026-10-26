from __future__ import annotations

from datetime import date

from ..models import Course, TeeTime
from .base import Reader, ReaderUnavailable
from .golfnow import GolfNowReader
from .webtrac import WebTracReader

READERS: dict[str, type[Reader]] = {
    "golfnow": GolfNowReader,
    "webtrac": WebTracReader,
}


def read_course(course: Course, days: list[date], players: int) -> list[TeeTime]:
    reader_cls = READERS.get(course.platform)
    if reader_cls is None:
        raise ReaderUnavailable("Not checked automatically yet; use the booking link")
    return reader_cls().read(course, days, players)


__all__ = ["READERS", "Reader", "ReaderUnavailable", "read_course"]
