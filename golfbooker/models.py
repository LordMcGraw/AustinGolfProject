from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

AUSTIN = ZoneInfo("America/Chicago")


@dataclass
class Course:
    id: str
    name: str
    platform: str
    lat: float
    lon: float
    booking_url: str
    notes: str = ""
    golfnow_facility: int | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "Course":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class TeeTime:
    course_id: str
    start: datetime  # local Austin time
    min_players: int
    max_players: int
    holes: int
    price: float | None  # per player, USD
    booking_url: str
    source: str
    weather: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        """Stable id used to avoid alerting on the same slot twice."""
        return f"{self.course_id}|{self.start.isoformat()}|{self.holes}"

    def to_json(self) -> dict:
        d = asdict(self)
        d["start"] = self.start.isoformat()
        d["key"] = self.key
        return d
