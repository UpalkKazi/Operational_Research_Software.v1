"""Playwright fixtures for OR Studio browser tests.

Start the app first (no AI keys needed):
    streamlit run app.py --server.port 8501 --server.headless true
then run:
    pytest tests/browser -v
Set ORSTUDIO_URL to test another address.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright

BASE_URL = os.environ.get("ORSTUDIO_URL", "http://localhost:8501")
SHOTS = Path(__file__).resolve().parents[2] / "artifacts" / "screens"
SHOTS.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def browser():
    import urllib.request

    try:
        urllib.request.urlopen(BASE_URL + "/_stcore/health", timeout=5)
    except OSError:
        pytest.skip(f"OR Studio is not running at {BASE_URL}")
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def _open(browser, width=1440, height=900, scale=1, path="/"):
    context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=scale)
    page = context.new_page()
    page.set_default_timeout(30000)
    page.goto(BASE_URL + path)
    page.wait_for_selector("[data-testid='stApp']")
    page.locator(".st-key-ors_topbar").wait_for()
    page.locator(".ors-css-anchor").first.wait_for(state="attached")
    idle(page)
    return context, page


@pytest.fixture
def open_page(browser):
    contexts = []

    def factory(**kwargs):
        context, page = _open(browser, **kwargs)
        contexts.append(context)
        return page

    yield factory
    for context in contexts:
        context.close()


@pytest.fixture
def page(open_page) -> Page:
    return open_page()


def idle(page: Page, settle: int = 350) -> None:
    page.wait_for_timeout(settle)
    page.wait_for_function(
        "() => { const s = document.querySelector('[data-testid=\"stStatusWidget\"]'); return !s || !/Running/i.test(s.innerText); }",
        timeout=60000,
    )
    page.wait_for_timeout(150)


def shot(page: Page, name: str, full: bool = True) -> Path:
    path = SHOTS / f"{name}.png"
    page.screenshot(path=str(path), full_page=full)
    return path


def click(page: Page, name: str, exact: bool = True, nth: int = 0) -> None:
    page.get_by_role("button", name=name, exact=exact).nth(nth).click()
    idle(page)


def no_horizontal_overflow(page: Page) -> bool:
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
