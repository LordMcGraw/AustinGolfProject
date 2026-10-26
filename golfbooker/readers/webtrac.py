from __future__ import annotations

from datetime import date

from ..models import Course, TeeTime
from .base import Reader, ReaderUnavailable


class WebTracReader(Reader):
    """City of Austin munis, booked through the city's WebTrac tee sheet
    (txaustinweb.myvscloud.com, linked from austintexas.gov/golfatx).

    Not built: the site sits behind Cloudflare, which blocks automated requests
    from cloud servers. Courses on this platform show a direct booking link instead.
    """

    def read(self, course: Course, days: list[date], players: int) -> list[TeeTime]:
        raise ReaderUnavailable("City tee sheet blocks automated checks; use the booking link")
