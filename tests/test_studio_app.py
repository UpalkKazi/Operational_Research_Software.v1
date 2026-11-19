"""AppTest smoke coverage for the OR Studio entry point (app.py), without AI credentials."""

import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.services import catalog

APP = Path(__file__).parents[1] / "app.py"


@pytest.fixture(autouse=True)
def no_credentials(monkeypatch):
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.setenv(key, "your_api_key_here")


def settle(app: AppTest, timeout: float = 60) -> AppTest:
    deadline = time.time() + timeout
    app.run()
    while app.session_state["ws"].has_pending() and time.time() < deadline:
        time.sleep(0.2)
        app.run()
    app.run()
    return app


def test_starts_on_chat_without_errors():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not app.exception
    assert app.session_state["pref_view"] == "chat"
    assert app.text_area(key="w_draft") is not None


def test_orlearn_example_from_composer_solves_offline():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.text_area(key="w_draft").set_value(catalog.example("orl-lp")["text"]).run()
    app.button(key="chat_solve").click()
    settle(app)
    assert not app.exception
    ws = app.session_state["ws"]
    run = next(iter(ws.runs.values()))
    assert run.result["kind"] == "optimal"
    assert run.result["objective"] == pytest.approx(2200)
    assert run.result["variables"] == pytest.approx({"chairs": 24, "tables": 14})


def test_natural_language_without_credentials_keeps_draft():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    text = "A bakery makes bread and cakes and wants to maximise profit given oven time."
    app.text_area(key="w_draft").set_value(text).run()
    app.button(key="chat_solve").click().run()
    assert not app.exception
    ws = app.session_state["ws"]
    assert any(m["kind"] == "credentials" for m in ws.messages)
    assert app.session_state["pref_draft"] == text
    assert not ws.runs


def test_parse_error_never_reaches_provider():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.text_area(key="w_draft").set_value("var x >= 0;\nmaximize z: x^2;\nsubject to c: x <= 1;").run()
    app.button(key="chat_solve").click().run()
    ws = app.session_state["ws"]
    errors = [m for m in ws.messages if m["kind"] == "parse_error"]
    assert errors and errors[0]["line"] == 2
    assert not any(m["kind"] in ("ai_job", "credentials") for m in ws.messages)


def test_playground_renders_each_tab():
    app = AppTest.from_file(str(APP), default_timeout=60)
    app.query_params["view"] = "playground"
    app.run()
    assert not app.exception
    for tab in ("Algebraic", "Live Editor", "Easy Start"):
        app.session_state["pref_pg_tab"] = tab
        app.run()
        assert not app.exception, tab
