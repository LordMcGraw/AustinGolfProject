"""Instant email alerts for newly opened tee times that match the search settings."""
from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from .models import AUSTIN, Course, TeeTime


class AlertLog:
    """Remembers which slots were already emailed so each one alerts once."""

    def __init__(self, path: Path):
        self.path = path
        self.sent: dict[str, str] = json.loads(path.read_text()) if path.exists() else {}

    def new(self, tee_times: list[TeeTime]) -> list[TeeTime]:
        return [tt for tt in tee_times if tt.key not in self.sent]

    def record(self, tee_times: list[TeeTime], now: datetime) -> None:
        for tt in tee_times:
            self.sent[tt.key] = tt.start.isoformat()
        # Forget slots that have already passed.
        self.sent = {k: v for k, v in self.sent.items() if datetime.fromisoformat(v) >= now}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.sent, indent=1, sort_keys=True) + "\n")


def format_line(tt: TeeTime, course: Course) -> str:
    when = tt.start.strftime("%a %b %-d, %-I:%M %p")
    players = f"{tt.min_players}" if tt.min_players == tt.max_players else f"{tt.min_players}-{tt.max_players}"
    price = f"${tt.price:.2f}" if tt.price is not None else "price n/a"
    w = tt.weather
    weather = f" | {w['temp_f']}°F, {w['summary']}, {w['precip_pct']}% rain" if w else ""
    return f"{when} - {course.name} - {tt.holes} holes, {players} players, {price}{weather}\n  Book: {tt.booking_url}"


def build_email(new: list[TeeTime], courses: dict[str, Course], to: str, sender: str, dashboard_url: str = "") -> EmailMessage:
    new = sorted(new, key=lambda t: t.start)
    msg = EmailMessage()
    first = new[0]
    subject = f"{courses[first.course_id].name} {first.start.strftime('%a %-I:%M %p')}"
    if len(new) > 1:
        subject += f" + {len(new) - 1} more"
    msg["Subject"] = f"Tee times open: {subject}"
    msg["From"] = sender
    msg["To"] = to
    lines = [format_line(tt, courses[tt.course_id]) for tt in new]
    footer = f"\n\nDashboard: {dashboard_url}" if dashboard_url else ""
    msg.set_content("New tee times matching your search:\n\n" + "\n\n".join(lines) + footer)
    return msg


def send(msg: EmailMessage, settings: dict) -> None:
    user, password = os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"]
    with smtplib.SMTP_SSL(settings["smtp_host"], settings["smtp_port"], timeout=30) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)


def now_local() -> datetime:
    return datetime.now(AUSTIN)
