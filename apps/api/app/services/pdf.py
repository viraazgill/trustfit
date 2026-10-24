"""PDF reports: Playwright prints the web app's own report page, so the PDF always matches the screen.

The printer signs in as the requesting user with a five-minute token, opens the page in their language,
waits for the page to mark itself ready ([data-print-ready]) and scales it to one A4 sheet.
"""
from __future__ import annotations

import datetime as dt

from app.auth import create_token
from app.errors import ApiError
from app.models import User
from app.settings import settings

A4_MM = (210, 297)
MARGIN_MM = 10
CSS_PX_PER_MM = 96 / 25.4
VIEWPORT_WIDTH = 1200
MIN_SCALE = 0.35  # Playwright accepts 0.1-2; below this a page is unreadable, so let it run to two pages
TOKEN_LIFETIME = dt.timedelta(minutes=5)
READY_TIMEOUT_MS = 30_000


def render_pdf(path: str, user: User, lang: str = "en") -> bytes:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ApiError(503, "PDF export needs Playwright on the API server: pip install -e 'apps/api[pdf]' "
                            "and playwright install chromium") from exc
    token = create_token(user, TOKEN_LIFETIME)
    width_px = (A4_MM[0] - 2 * MARGIN_MM) * CSS_PX_PER_MM
    height_px = (A4_MM[1] - 2 * MARGIN_MM) * CSS_PX_PER_MM
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": VIEWPORT_WIDTH, "height": 900})
                page.add_init_script(
                    f"localStorage.setItem('trustfit.token', {token!r});"
                    f"localStorage.setItem('trustfit.locale', {lang!r});")
                page.goto(f"{settings.WEB_URL}{path}")
                page.wait_for_selector("[data-print-ready]", timeout=READY_TIMEOUT_MS)
                page.emulate_media(media="print")
                content_height = page.evaluate("document.documentElement.scrollHeight")
                scale = max(MIN_SCALE, min(1.0, width_px / VIEWPORT_WIDTH, height_px / content_height))
                margin = {side: f"{MARGIN_MM}mm" for side in ("top", "right", "bottom", "left")}
                return page.pdf(format="A4", print_background=True, scale=scale, margin=margin)
            finally:
                browser.close()
    except PlaywrightError as exc:
        raise ApiError(502, f"Could not print the report page at {settings.WEB_URL}: {exc.message}") from exc
