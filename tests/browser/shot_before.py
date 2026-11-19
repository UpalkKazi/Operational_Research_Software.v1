"""Capture "before" screenshots of legacy_app.py (run it on port 8503 first)."""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8503"
OUT = Path(__file__).parents[2] / "artifacts" / "screens"
OUT.mkdir(parents=True, exist_ok=True)


def settle(page, ms=1500):
    page.wait_for_timeout(400)
    page.locator("[data-testid='stStatusWidget']").wait_for(state="detached", timeout=60000)
    page.wait_for_timeout(ms)


def tab(page, label):
    page.get_by_role("tab", name=label).first.click()
    settle(page)


with sync_playwright() as p:
    browser = p.chromium.launch()
    for width, height, suffix in [(1440, 900, ""), (390, 844, "_390")]:
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(URL)
        page.wait_for_selector("[data-testid='stApp']")
        settle(page, 3000)
        page.screenshot(path=str(OUT / f"before_chat{suffix}.png"))
        tab(page, "🧮 Model Playground")
        page.screenshot(path=str(OUT / f"before_easy_start{suffix}.png"))
        tab(page, "⌨️ Algebraic")
        page.screenshot(path=str(OUT / f"before_algebraic{suffix}.png"))
        tab(page, "✏️ Live Editor")
        page.screenshot(path=str(OUT / f"before_live_editor{suffix}.png"), full_page=True)
        page.close()
    browser.close()
print("saved to", OUT)
