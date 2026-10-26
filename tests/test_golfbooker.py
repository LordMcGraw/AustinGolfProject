import json
from datetime import datetime
from pathlib import Path

from golfbooker.alerts import AlertLog, build_email
from golfbooker.filters import matches
from golfbooker.models import AUSTIN, Course, TeeTime
from golfbooker.readers.golfnow import GolfNowReader, parse_player_rule

FIXTURES = Path(__file__).parent / "fixtures"
COURSE = Course(id="crystal-falls", name="Crystal Falls", platform="golfnow", lat=30.6, lon=-97.9,
                booking_url="https://example.com", golfnow_facility=5741)


def tee_time(start, lo=1, hi=4, holes=18):
    return TeeTime(course_id="crystal-falls", start=start, min_players=lo, max_players=hi, holes=holes,
                   price=58.86, booking_url="https://www.golfnow.com/x", source="golfnow")


def test_parse_player_rule():
    assert parse_player_rule("One") == (1, 1)
    assert parse_player_rule("TwoThreeFour") == (2, 4)
    assert parse_player_rule("OneTwo") == (1, 2)
    assert parse_player_rule("Any") == (1, 4)


def test_golfnow_parse_uses_wall_clock_time():
    raw = json.loads((FIXTURES / "golfnow_teetimes.json").read_text())["ttResults"]["teeTimes"]
    tts = [tt for r in raw for tt in GolfNowReader.parse(COURSE, r)]
    first = tts[0]
    # GolfNow sends "14:00+00:00" for a 2:00 PM local tee time.
    assert first.start == datetime(2026, 10, 31, 14, 0, tzinfo=AUSTIN)
    assert (first.min_players, first.max_players) == (1, 1)
    assert first.price == 58.86
    assert first.booking_url.startswith("https://www.golfnow.com/tee-times/facility/5741/")
    assert (tts[1].min_players, tts[1].max_players) == (2, 4)


def test_matches_days_players_and_window():
    search = {"days": ["sat"], "players": 2, "time_windows": [["07:00", "10:00"]]}
    sat_8am = datetime(2026, 10, 31, 8, 0, tzinfo=AUSTIN)
    assert matches(tee_time(sat_8am), search)
    assert not matches(tee_time(sat_8am, lo=1, hi=1), search)  # singles only
    assert not matches(tee_time(datetime(2026, 10, 31, 11, 0, tzinfo=AUSTIN)), search)  # too late
    assert not matches(tee_time(datetime(2026, 11, 1, 8, 0, tzinfo=AUSTIN)), search)  # Sunday


def test_alert_log_alerts_once_and_forgets_past(tmp_path):
    log = AlertLog(tmp_path / "alerted.json")
    tt = tee_time(datetime(2026, 10, 31, 8, 0, tzinfo=AUSTIN))
    assert log.new([tt]) == [tt]
    log.record([tt], now=datetime(2026, 10, 30, tzinfo=AUSTIN))
    log.save()
    assert AlertLog(tmp_path / "alerted.json").new([tt]) == []
    log.record([], now=datetime(2026, 11, 1, tzinfo=AUSTIN))
    assert log.sent == {}


def test_email_lists_times_with_booking_links():
    tts = [tee_time(datetime(2026, 10, 31, 9, 0, tzinfo=AUSTIN)), tee_time(datetime(2026, 10, 31, 8, 0, tzinfo=AUSTIN))]
    msg = build_email(tts, {"crystal-falls": COURSE}, "me@example.com", "me@example.com")
    assert msg["Subject"] == "Tee times open: Crystal Falls Sat 8:00 AM + 1 more"
    body = msg.get_content()
    assert body.index("8:00 AM") < body.index("9:00 AM")
    assert "Book on GolfNow: https://www.golfnow.com/x" in body


def test_conditions_summary_counts_recent_mentions():
    from golfbooker.conditions import summarize

    collection = {
        "subratings": [{"label": "Course Conditions", "value": 3.975}],
        "reviews": [
            {"reviewDate": "2026-10-20T10:00:00", "dateOfPlay": "2026-10-19T00:00:00", "rating": 3,
             "reviewTitle": "Greens punched", "reviewText": "Greens were just aerated and sanded."},
            {"reviewDate": "2026-05-01T10:00:00", "rating": 5, "reviewText": "Greens perfect."},  # too old
        ],
    }
    snap = summarize(collection, today=datetime(2026, 10, 26))
    assert snap["conditions_rating"] == 4.0
    assert snap["recent_count"] == 1
    assert snap["mentions"] == {"greens": 1, "aeration": 1}
    assert snap["reviews"][0]["played"] == "2026-10-19"
