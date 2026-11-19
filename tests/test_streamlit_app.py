"""Smoke coverage for the previous (legacy_app.py) Streamlit interface, which stays runnable."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / "legacy_app.py"


def test_app_starts_with_core_workspaces():
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not app.exception
    labels = [tab.label for tab in app.tabs]
    for expected in (
        "💡 Solve Problem",
        "📊 Results",
        "📈 Visualization",
        "🧮 Model Playground",
        "🗄️ MIPLIB Cache",
        "📖 Help",
        "✨ Easy Start",
        "⌨️ Algebraic",
        "📄 Model View",
        "✏️ Live Editor",
        "📊 Sensitivity Sweep",
    ):
        assert expected in labels
    assert app.radio[0].options == [
        "Type Problem",
        "Upload File",
        "Load from MIPLIB",
    ]
    assert any(
        area.label == "Enter problem description in natural language:"
        for area in app.text_area
    )


def test_algebraic_example_is_valid_on_startup():
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not app.exception
    assert any("Valid ORLEARN model" in success.value for success in app.success)


def test_algebraic_model_solves_and_opens_in_live_editor():
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.button(key="pg_alg_solve").click().run()
    assert not app.exception
    assert app.session_state["solution"]["is_optimal"] is True
    assert app.session_state["playground_original_state"]["variables"]
    assert app.session_state["playground_original_solution"]["variable_values"]
