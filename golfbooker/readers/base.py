from __future__ import annotations

from datetime import date

import requests

from ..models import Course, TeeTime

USER_AGENT = "AustinGolfBooker/0.1 (personal tee time checker)"


class ReaderUnavailable(Exception):
    """The course can't be read right now; the dashboard shows the reason."""


class Reader:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

    def read(self, course: Course, days: list[date], players: int) -> list[TeeTime]:
        raise NotImplementedError
