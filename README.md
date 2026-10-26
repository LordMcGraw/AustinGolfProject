# Austin Golf Booker

One page of open tee times at the Austin-area courses Jack plays, with email alerts when a time
matching his search opens up.

## What it does

Every 15 minutes a GitHub Actions job (`.github/workflows/check-tee-times.yml`):

1. Reads open tee times for the next 8 days from each course's booking site.
2. Adds the National Weather Service forecast for each tee time.
3. Publishes the dashboard (`site/`) to GitHub Pages.
4. Emails any newly opened tee times that match `config/settings.yaml`.

## Course coverage

| Courses | Source | Status |
| --- | --- | --- |
| Teravista, Falconhead, Avery Ranch, ShadowGlen, Star Ranch, Crystal Falls, Forest Creek, Riverside | GolfNow | Checked automatically |
| Lions, Morris Williams, Jimmy Clay, Roy Kizer, Hancock | City WebTrac tee sheet | Booking link only. The city site blocks automated checks |
| Cimarron Hills | Private club | Booking link only |
| Sun City (Cowan Creek, Legacy Hills, White Wing, Kurth-Landrum) | Unknown | Booking link only |

Some courses keep part of their inventory on their own tee sheet (Forest Creek and Teravista on
Chronogolf, Star Ranch on EZLinks), so GolfNow can show fewer times than the course's own site.

## Settings

- `config/settings.yaml`: days ahead, players, days of week and time windows for alerts.
- `config/courses.yaml`: courses, booking platform, booking links and notes.

The dashboard starts from the alert settings and lets you change the filters in the page.

## Setup

Repository secrets (Settings > Secrets and variables > Actions):

- `ALERT_TO`: address to send alerts to.
- `SMTP_USER`: Gmail address that sends the alerts.
- `SMTP_PASSWORD`: a Gmail [app password](https://myaccount.google.com/apppasswords) for that account.

Optional repository variable `DASHBOARD_URL` adds a dashboard link to alert emails.

Turn on Pages with Settings > Pages > Source: GitHub Actions.

The first run remembers what's already open without emailing; later runs email only new times.

## Run locally

```sh
pip install -r requirements.txt pytest
python -m golfbooker.run --no-email   # prints the alert email instead of sending
python -m http.server -d site 8000    # dashboard at http://localhost:8000
python -m pytest
```
