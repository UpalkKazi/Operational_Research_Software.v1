"""End-to-end browser tests for OR Studio (Playwright, Chromium).

Numeric fixture: maximize 45c + 80t s.t. 5c + 20t <= 400 (Wood), 10c + 15t <= 450 (Labor).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from conftest import click, idle, no_horizontal_overflow, shot

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "uploads"


def composer(page: Page):
    return page.locator(".st-key-w_draft textarea")


def run_card(page: Page):
    return page.locator("[class*='st-key-run_']").last


def wait_result(page: Page, text: str, timeout: int = 60000):
    expect(run_card(page)).to_contain_text(text, timeout=timeout)
    idle(page)


def metric(page: Page, label: str):
    return page.locator("[data-testid='stMetric']").filter(has_text=label).locator("[data-testid='stMetricValue']").first


def open_live_editor_from_chat(page: Page):
    click(page, "Open in Playground")
    expect(page.get_by_text("Objective", exact=True).first).to_be_visible()


def rhs_input(page: Page, uid: str = "c1"):
    return page.locator(f"[class*='_rhs_{uid}'] input").first


# ---------------------------------------------------------------------------

def test_orlearn_readme_example_from_composer(page: Page):
    """Priority: the verbatim OR-Learn README LP, pasted with format Auto, solves from the main composer (Ctrl+Enter)."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.services.catalog import ORLEARN_LP

    composer(page).fill(ORLEARN_LP)
    composer(page).click()
    page.keyboard.press("Control+Enter")
    idle(page)
    wait_result(page, "Optimal")
    expect(metric(page, "Objective")).to_have_text("2,200")
    card = run_card(page)
    expect(card).to_contain_text("chairs")
    expect(card).to_contain_text("24")
    expect(card).to_contain_text("14")
    expect(card).to_contain_text("COIN-OR CBC")
    expect(page.get_by_text(re.compile(r"Parsed with the OR-Learn library .* invoked"))).to_be_visible()
    expect(page.locator("[data-testid='stChatMessage']").first).to_contain_text("Auto → OR-Learn")
    card.get_by_text("Diagnostics").click()
    expect(card).to_contain_text("OR-Learn cross-check")
    expect(card).to_contain_text("solve() → 2,200")
    expect(card).to_contain_text("38355732")
    shot(page, "after_chat_inline_result")


def test_fixture_edit_compare_sweep_reset(page: Page):
    click(page, "OR-Learn example")
    click(page, "Solve Problem")
    wait_result(page, "Optimal")
    open_live_editor_from_chat(page)
    expect(page.locator(".st-key-le_actions")).to_contain_text("Baseline")
    box = rhs_input(page, "c1")
    expect(box).to_have_value("400")
    box.fill("300")
    box.press("Tab")
    idle(page)
    expect(page.get_by_text("Unsolved edits").first).to_be_visible()
    click(page, "Solve Edited Model")
    expect(page.get_by_text("Compare with baseline")).to_be_visible(timeout=60000)
    idle(page)
    expect(metric(page, "Baseline objective")).to_have_text("2,200")
    expect(metric(page, "Edited objective")).to_have_text("2,100")
    expect(metric(page, "Difference")).to_have_text("-100")
    compare = page.locator("[class*='st-key-cmp_']").first
    expect(compare).to_contain_text("Wood RHS: 400 → 300")
    expect(compare).to_contain_text("36")
    expect(compare).to_contain_text("6")
    shot(page, "after_live_editor_compare")

    page.get_by_text("Sensitivity sweep").click()
    values = page.locator("[class*='_sw_vals'] input").first
    values.fill("300, 350, 400")
    values.press("Enter")
    idle(page)
    click(page, "Run sweep")
    table = page.locator("[data-testid='stTable']").filter(has_text="RHS").last
    expect(table).to_contain_text("2,100", timeout=60000)
    expect(table).to_contain_text("2,150")
    expect(table).to_contain_text("2,200")
    expect(table).to_contain_text("Optimal")
    expect(rhs_input(page, "c1")).to_have_value("300")
    shot(page, "after_sweep")

    click(page, "Reset to Baseline")
    expect(rhs_input(page, "c1")).to_have_value("400")
    page.get_by_text(re.compile(r"Run history")).click()
    expect(page.locator("[class*='st-key-hist_']").filter(has_text="historical").first).to_be_visible()


def test_older_result_opens_exact_revision(page: Page):
    click(page, "OR-Learn example")
    click(page, "Solve Problem")
    wait_result(page, "Optimal")
    open_live_editor_from_chat(page)
    rhs_input(page).fill("300")
    rhs_input(page).press("Tab")
    idle(page)
    click(page, "Solve Edited Model")
    expect(page.get_by_text("Compare with baseline")).to_be_visible(timeout=60000)
    page.get_by_role("radio", name="Chat", exact=True).click()
    idle(page)
    click(page, "Open in Playground")
    expect(rhs_input(page)).to_have_value("400")


def test_draft_survives_format_loader_solver_and_navigation(page: Page):
    text = "maximize z: 3*x + 2*y;\nsubject to c1: x + y <= 4;"
    composer(page).fill(text)
    composer(page).press("Tab")
    idle(page)
    page.locator(".st-key-w_chat_fmt").click()
    page.get_by_role("option", name="AMPL-style").click()
    idle(page)
    page.locator(".st-key-w_chat_solver").click()
    page.get_by_role("option", name="SCIP").click()
    idle(page)
    click(page, "Load Problem", nth=0)
    expect(page.get_by_role("dialog")).to_be_visible()
    page.keyboard.press("Escape")
    idle(page)
    page.get_by_role("radio", name="Model Playground", exact=True).click()
    idle(page)
    page.get_by_role("radio", name="Chat", exact=True).click()
    idle(page)
    expect(composer(page)).to_have_value(text)
    expect(page.locator(".st-key-w_chat_fmt input")).to_have_value("AMPL-style")
    expect(page.locator(".st-key-w_chat_solver input")).to_have_value("SCIP")


def test_parse_error_never_falls_through(page: Page):
    text = "var x >= 0;\nmaximize z: 3*x*x;\nsubject to c: x <= 4;"
    composer(page).fill(text)
    composer(page).press("Tab")
    idle(page)
    click(page, "Solve Problem")
    reply = page.locator("[data-testid='stChatMessage']").last
    expect(reply).to_contain_text("Parse error")
    expect(reply).to_contain_text("Line 2")
    expect(reply).to_contain_text("Nothing was sent to an AI provider")
    expect(composer(page)).to_have_value(text)
    shot(page, "after_parse_error")


def test_natural_language_without_credentials(page: Page):
    from dotenv import load_dotenv

    from src.services.ai_service import provider_status

    # The server under test loads .env; this process has to as well to agree with it.
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)
    if provider_status()["configured"]:
        pytest.skip("an AI provider is configured, so the server answers instead of refusing")
    text = "A bakery makes bread and cake. Bread earns 3 and cake earns 5. We have 40 hours of oven time."
    composer(page).fill(text)
    composer(page).press("Tab")
    idle(page)
    click(page, "Solve Problem")
    reply = page.locator("[data-testid='stChatMessage']").last
    expect(reply).to_contain_text("AI credentials required")
    expect(reply.get_by_role("button", name="Try a template")).to_be_visible()
    expect(composer(page)).to_have_value(text)
    shot(page, "after_credentials_required")


def test_ambiguous_input_asks_for_format(page: Page):
    composer(page).fill("maximize 3x + 2y subject to x + y <= 4")
    composer(page).press("Tab")
    idle(page)
    click(page, "Solve Problem")
    expect(page.get_by_text("Which format is this?")).to_be_visible()
    click(page, "Treat as AMPL-style")
    expect(page.locator("[data-testid='stChatMessage']").last).to_contain_text("Parse error")


TEMPLATE_OBJECTIVES = {
    "Linear program": "2,200",
    "Integer program": "40",
    "Transportation": "2,280",
    "Assignment": "13",
    "Knapsack": "700",
    "Scheduling": "5",
}


def test_easy_start_templates(open_page):
    page = open_page(path="/?view=playground")
    for index, (title, objective) in enumerate(TEMPLATE_OBJECTIVES.items()):
        card = page.locator("[class*='st-key-tplcard_']").filter(has_text=title)
        card.get_by_role("button").click()
        idle(page)
        expect(page.locator("[class*='st-key-tplcard_sel_']")).to_contain_text(title)
        preview = page.locator(".st-key-tpl_preview")
        expect(preview).to_contain_text(title)
        expect(preview.locator(".katex").first).to_be_visible()
        if index == 0:
            shot(page, "after_easy_start_selected")
        click(page, "Solve Template")
        expect(preview.locator("[class*='st-key-run_']")).to_contain_text("Optimal", timeout=60000)
        idle(page)
        expect(preview.locator("[data-testid='stMetricValue']").first).to_have_text(objective)
    click(page, "Edit in Live Editor")
    expect(page.get_by_text("Constraints ·", exact=False).first).to_be_visible()


def test_unsaved_edits_prompt(page: Page):
    click(page, "OR-Learn example")
    click(page, "Solve Problem")
    wait_result(page, "Optimal")
    open_live_editor_from_chat(page)
    rhs_input(page).fill("300")
    rhs_input(page).press("Tab")
    idle(page)
    page.get_by_role("radio", name="Easy Start").click()
    idle(page)
    page.locator("[class*='st-key-tplcard_']").filter(has_text="Knapsack").get_by_role("button").click()
    idle(page)
    click(page, "Edit in Live Editor")
    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("haven't been solved")
    dialog.get_by_role("button", name="Keep Editing").click()
    idle(page)
    expect(rhs_input(page)).to_have_value("300")


def test_algebraic_tab(open_page):
    page = open_page(path="/?view=playground")
    page.get_by_role("radio", name="Algebraic").click()
    idle(page)
    click(page, "Load Example")
    page.get_by_role("button", name="Production planning with sets · AMPL-style").click()
    idle(page)
    preview = page.locator(".st-key-alg_preview")
    expect(preview).to_contain_text("Valid AMPL-style")
    preview.get_by_text("Sets, parameters and indexed variables").click()
    expect(preview).to_contain_text("set PRODUCTS")
    expect(preview).to_contain_text("param use")
    expect(preview.locator(".katex").first).to_be_visible()
    shot(page, "after_algebraic")
    source = page.locator(".st-key-w_alg_text textarea")
    source.fill(source.input_value() + "\nsubject to bad: make[chairs] * make[tables] <= 3;\n")
    source.press("Tab")
    idle(page)
    expect(preview).to_contain_text("Line")
    expect(page.get_by_role("button", name="Solve Model")).to_be_disabled()
    click(page, "Load Example")
    page.get_by_role("button", name="Production planning (OR-Learn README)").click()
    idle(page)
    expect(preview).to_contain_text("Valid OR-Learn")
    expect(preview).to_contain_text("invoked")
    click(page, "Solve Model")
    expect(page.locator("[class*='st-key-run_alg_']")).to_contain_text("Optimal", timeout=60000)
    click(page, "Open in Live Editor")
    expect(rhs_input(page)).to_have_value("400")


def test_symbols_keypad_and_math_edit(open_page):
    page = open_page(path="/?view=playground")
    page.locator("[class*='st-key-tplcard_']").filter(has_text="Linear program").get_by_role("button").click()
    idle(page)
    click(page, "Edit in Live Editor")
    page.locator("[class*='_obj_btn'] button:visible").first.click()
    idle(page)
    frame = page.frame_locator("iframe[title*='mathlive']").first
    toggle = frame.get_by_role("button", name="Symbols keypad")
    expect(toggle).to_have_attribute("aria-expanded", "false")
    toggle.click()
    expect(toggle).to_have_attribute("aria-expanded", "true")
    expect(frame.get_by_role("button", name=re.compile("less than or equal"))).to_have_attribute("aria-disabled", "true")
    page.wait_for_timeout(500)
    shot(page, "after_keypad")
    frame.locator("math-field").click()
    frame.locator("math-field").press("Escape")
    expect(toggle).to_have_attribute("aria-expanded", "false")
    toggle.press("Enter")
    expect(toggle).to_have_attribute("aria-expanded", "true")
    first_key = frame.locator("#common .key").first
    expect(first_key).to_be_focused()
    first_key.press("Escape")
    expect(toggle).to_have_attribute("aria-expanded", "false")
    expect(toggle).to_be_focused()

    field = frame.locator("math-field")
    field.click()
    field.press("Control+a")
    field.press_sequentially("50chairs+80tables", delay=30)
    page.wait_for_timeout(800)
    idle(page)
    click(page, "Solve Edited Model")
    expect(page.locator("[class*='st-key-run_le_']")).to_contain_text("Optimal", timeout=60000)
    idle(page)
    expect(page.locator("[class*='st-key-run_le_'] [data-testid='stMetricValue']").first).to_have_text("2,320")


def test_unsupported_math_is_rejected(open_page):
    page = open_page(path="/?view=playground")
    page.locator("[class*='st-key-tplcard_']").filter(has_text="Linear program").get_by_role("button").click()
    idle(page)
    click(page, "Edit in Live Editor")
    page.locator("[class*='_obj_btn'] button:visible").first.click()
    idle(page)
    frame = page.frame_locator("iframe[title*='mathlive']").first
    field = frame.locator("math-field")
    field.click()
    field.press("Control+a")
    field.press_sequentially("chairs*tables", delay=30)
    page.wait_for_timeout(900)
    idle(page)
    expect(page.get_by_text("Not applied").first).to_be_visible()
    page.get_by_role("button", name=re.compile(r"^Solve (Edited )?Model$")).first.click()
    idle(page)
    expect(page.locator("[class*='st-key-run_le_']")).to_have_count(0)


def test_load_problem_examples_and_uploads(page: Page):
    click(page, "Load Problem", nth=0)
    dialog = page.get_by_role("dialog")
    for category in ["Linear Programming", "Integer Programming", "Transportation", "Assignment", "Scheduling", "Knapsack"]:
        expect(dialog.get_by_role("radio", name=category)).to_be_visible()
    dialog.get_by_role("radio", name="Knapsack").click()
    idle(page)
    expect(dialog).to_contain_text("0-1 knapsack (OR-Learn README)")
    dialog.get_by_role("tab", name="Upload").click()
    upload = dialog.locator("input[type='file']")
    upload.set_input_files(str(FIXTURES / "fixture.mps"))
    idle(page, 800)
    expect(dialog).to_contain_text("MPS model imported")
    shot(page, "after_upload_mps")
    upload.set_input_files(str(FIXTURES / "corrupt.mps.gz"))
    idle(page, 800)
    expect(dialog).to_contain_text("Your active model is unchanged")
    upload.set_input_files(str(FIXTURES / "fixture.mps"))
    idle(page, 800)
    dialog.get_by_role("button", name="Solve in Chat").click()
    idle(page)
    wait_result(page, "Optimal")
    expect(metric(page, "Objective")).to_have_text("2,200")


@pytest.mark.network
def test_miplib_download_then_solve(page: Page):
    click(page, "Load Problem", nth=0)
    dialog = page.get_by_role("dialog")
    dialog.get_by_role("tab", name="MIPLIB").click()
    dialog.get_by_role("radio", name="By name").click()
    idle(page)
    name = dialog.get_by_label("Instance name")
    name.fill("flugpl")
    name.press("Enter")
    idle(page)
    dialog.get_by_role("button", name="Load", exact=True).click()
    idle(page)
    reply = page.locator("[data-testid='stChatMessage']").last
    expect(reply).to_contain_text("Model loaded", timeout=120000)
    expect(reply).to_contain_text("18 variables")
    reply.get_by_role("button", name="Solve").click()
    idle(page)
    wait_result(page, "Optimal", timeout=120000)
    expect(metric(page, "Objective")).to_have_text("1,201,500")
    shot(page, "after_miplib")


@pytest.mark.parametrize("width", [390, 768, 1440])
def test_responsive_layouts(open_page, width):
    page = open_page(width=width, height=900)
    assert no_horizontal_overflow(page)
    shot(page, f"after_chat_empty_{width}", full=False)
    page.get_by_role("radio", name="Model Playground", exact=True).click()
    idle(page)
    page.locator("[class*='st-key-tplcard_']").filter(has_text="Linear program").get_by_role("button").click()
    idle(page, 900)
    assert no_horizontal_overflow(page)
    if width < 900:
        top = page.locator(".st-key-tpl_preview").bounding_box()["y"]
        assert -5 <= top < 900 - 200, f"preview not scrolled into view (y={top})"
    shot(page, f"after_easy_start_{width}", full=False)
    click(page, "Edit in Live Editor")
    idle(page)
    page.locator("[class*='_btn_c1'] button:visible").first.click()
    idle(page)
    frame = page.frame_locator("iframe[title*='mathlive']").first
    frame.get_by_role("button", name="Symbols keypad").click()
    page.wait_for_timeout(600)
    iframe = page.locator("iframe[title*='mathlive']").first
    box = iframe.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= width + 1
    keys_fit = frame.locator("body").evaluate("b => b.scrollWidth <= b.clientWidth + 1")
    assert keys_fit, "keypad overflows horizontally"
    assert no_horizontal_overflow(page)
    iframe.scroll_into_view_if_needed()
    shot(page, f"after_keypad_{width}", full=False)


def test_browser_zoom_200(open_page):
    page = open_page(width=720, height=450, scale=2)
    assert no_horizontal_overflow(page)
    page.get_by_role("radio", name="Model Playground", exact=True).click()
    idle(page)
    assert no_horizontal_overflow(page)
    shot(page, "after_zoom_200", full=False)


def test_focus_visible_and_contrast(page: Page):
    for _ in range(8):
        page.keyboard.press("Tab")
        if page.evaluate("() => document.activeElement.tagName") == "BUTTON":
            break
    outline = page.evaluate("() => { const e = document.activeElement; const s = getComputedStyle(e); return [e.tagName, s.outlineStyle, s.outlineWidth]; }")
    assert outline[1] != "none" and outline[2] != "0px", outline
    ratio = page.evaluate("""() => {
      const lum = c => { const v = c.match(/\\d+/g).slice(0,3).map(Number).map(x => { x/=255; return x <= 0.03928 ? x/12.92 : Math.pow((x+0.055)/1.055, 2.4); }); return 0.2126*v[0]+0.7152*v[1]+0.0722*v[2]; };
      const b = document.querySelector('.st-key-chat_solve button'); const s = getComputedStyle(b);
      const L1 = lum(s.color), L2 = lum(s.backgroundColor); return (Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);
    }""")
    assert ratio >= 4.5, ratio
