import datetime as dt

from conftest import AS_OF, SEED_DIR

from trustfit_engine.seed_io import load_companies, resolve_date


def test_resolve_date():
    assert resolve_date("today-4d", AS_OF) == dt.date(2026, 10, 20)
    assert resolve_date("2026-03-27", AS_OF) == dt.date(2026, 3, 27)
    assert resolve_date(None, AS_OF) is None


def test_subros_full_format(subros):
    assert (subros.id, subros.fictional, subros.name) == ("subros", False, "Subros Ltd")
    b6 = subros.evidence["B6"]
    assert (b6.level, b6.verified, b6.source_date) == (100, True, dt.date(2026, 3, 27))
    assert b6.source_url.startswith("https://www.icra.in/")
    assert b6.checked_at == AS_OF  # defaults to the seed's as_of
    assert "A1" not in subros.evidence  # pending checks stay missing
    assert {f.code for f in subros.flags} == {"strategic_shareholder_10", "customer_concentration_70"}
    assert subros.flags[0].source_url.startswith("https://www.screener.in/")
    assert subros.trends["operating_margin"].direction == "worsening"


def test_demo_compact_format(cfg):
    companies = load_companies(SEED_DIR / "demo_companies.json", cfg, AS_OF)
    assert len(companies) == 9
    assert all(c.fictional and c.name.endswith("(Demo)") for c in companies)
    deccan = next(c for c in companies if c.id == "deccan-instrumentation")
    assert "D1" not in deccan.evidence  # null = no verified evidence
    a1 = deccan.evidence["A1"]
    assert a1.source_url == "https://example.com/demo/deccan-instrumentation/A1"
    assert (a1.source_date, a1.checked_at) == (AS_OF - dt.timedelta(days=120), AS_OF - dt.timedelta(days=4))
    assert deccan.trends["revenue_growth"].direction == "improving"


def test_relative_dates_follow_the_scoring_date(cfg):
    later = AS_OF + dt.timedelta(days=365)
    (first, *_) = load_companies(SEED_DIR / "demo_companies.json", cfg, later)
    assert first.evidence["A1"].checked_at == later - dt.timedelta(days=4)
