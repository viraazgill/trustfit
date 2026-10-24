import datetime as dt

from app.settings import Settings


def test_empty_scoring_as_of_means_today(monkeypatch):
    # .env.example ships `SCORING_AS_OF=`; an empty value must not break startup.
    monkeypatch.setenv("SCORING_AS_OF", "")
    assert Settings(_env_file=None).SCORING_AS_OF is None


def test_scoring_as_of_parses_a_date(monkeypatch):
    monkeypatch.setenv("SCORING_AS_OF", "2026-10-24")
    assert Settings(_env_file=None).SCORING_AS_OF == dt.date(2026, 10, 24)
