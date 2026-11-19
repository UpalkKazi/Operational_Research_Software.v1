"""OR Studio light theme: tokens, layout widths, focus states, status chips."""

from __future__ import annotations

import streamlit as st

TOKENS = {
    "page": "#F6F8FB",
    "surface": "#FFFFFF",
    "text": "#172235",
    "muted": "#475569",
    "blue": "#1D4ED8",
    "line": "#D5DDE8",
}

STATUS = {
    "optimal": ("#14532D", "#DCFCE7", "check_circle", "Optimal"),
    "feasible": ("#7C2D12", "#FFEDD5", "timelapse", "Feasible"),
    "infeasible": ("#7F1D1D", "#FEE2E2", "block", "Infeasible"),
    "unbounded": ("#7F1D1D", "#FEE2E2", "all_inclusive", "Unbounded"),
    "no_solution": ("#7F1D1D", "#FEE2E2", "hourglass_disabled", "No solution"),
    "cancelled": ("#334155", "#E2E8F0", "cancel", "Cancelled"),
    "error": ("#7F1D1D", "#FEE2E2", "error", "Error"),
    "unsupported": ("#7C2D12", "#FFEDD5", "do_not_disturb_on", "Not run"),
    "running": ("#1E3A8A", "#DBEAFE", "progress_activity", "Running"),
    "info": ("#1E3A8A", "#DBEAFE", "info", "Info"),
    "neutral": ("#334155", "#EEF2F7", "radio_button_unchecked", "Not solved"),
    "edited": ("#7C2D12", "#FFEDD5", "edit_note", "Unsolved edits"),
}


def chip(kind: str, text: str = "") -> str:
    fg, bg, icon, default = STATUS.get(kind, STATUS["neutral"])
    label = text or default
    return (
        f'<span class="ors-chip" style="color:{fg};background:{bg};">'
        f'<span class="material-symbols-rounded" aria-hidden="true">{icon}</span>{label}</span>'
    )


def css(rules: str) -> None:
    """Style-only st.html goes to the transient event container; anchor it in the page instead."""
    st.html(f'<style>{rules}</style><span class="ors-css-anchor"></span>')


MONO_TEXTAREA = '{key} textarea{{font-family:ui-monospace,"Cascadia Code",Consolas,monospace!important;font-size:14.5px!important;line-height:1.5!important}}'


def inject(view: str) -> None:
    width = "880px" if view == "chat" else "1240px"
    st.html(
        f"""
<style>
.material-symbols-rounded {{ font-family: "Material Symbols Rounded"; font-weight: normal; font-style: normal; line-height: 1; letter-spacing: normal; text-transform: none; white-space: nowrap; direction: ltr; -webkit-font-smoothing: antialiased; font-feature-settings: "liga"; display:inline-block; overflow:hidden; width:1em; }}
:root {{ --ors-page:{TOKENS['page']}; --ors-surface:#FFFFFF; --ors-text:{TOKENS['text']}; --ors-muted:{TOKENS['muted']}; --ors-blue:{TOKENS['blue']}; --ors-line:{TOKENS['line']}; }}
html, body, .stApp {{ background: var(--ors-page) !important; color: var(--ors-text); }}
.stApp {{ font-size: 16px; }}
header[data-testid="stHeader"] {{ display:none !important; }}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {{ display:none !important; }}
.block-container, [data-testid="stMainBlockContainer"] {{ max-width: {width} !important; padding: 0 20px 96px !important; }}
@media (max-width: 640px) {{ .block-container, [data-testid="stMainBlockContainer"] {{ padding: 0 12px 96px !important; }} }}
p, li, label, .stMarkdown {{ color: var(--ors-text); }}
small, .ors-muted, [data-testid="stCaptionContainer"] {{ color: var(--ors-muted) !important; }}
h1 {{ font-size: 1.9rem !important; font-weight: 700 !important; letter-spacing: -0.01em; color: var(--ors-text) !important; }}
h2 {{ font-size: 1.3rem !important; font-weight: 650 !important; color: var(--ors-text) !important; }}
h3 {{ font-size: 1.08rem !important; font-weight: 650 !important; color: var(--ors-text) !important; }}
.katex {{ font-size: 1.12em !important; }}
.katex-display {{ overflow-x: auto; overflow-y: hidden; padding: 2px 0; margin: 0.2em 0 !important; text-align: left !important; }}
.katex-display > .katex {{ text-align: left !important; }}

/* Focus visibility (WCAG 2.4.7) */
.stApp button:focus-visible, .stApp a:focus-visible, .stApp input:focus-visible, .stApp textarea:focus-visible,
.stApp [role="tab"]:focus-visible, .stApp [role="radio"]:focus-visible, .stApp summary:focus-visible,
[role="dialog"] button:focus-visible, [data-baseweb="popover"] button:focus-visible {{
  outline: 3px solid var(--ors-blue) !important; outline-offset: 2px !important; border-radius: 8px;
}}

/* Header */
.st-key-ors_topbar {{
  position: sticky; top: 0; z-index: 999; background: rgba(246,248,251,0.96); backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--ors-line); min-height: 60px; padding: 8px 0 !important; margin: 0 -20px 16px !important;
  padding-left: 20px !important; padding-right: 20px !important; align-items: center !important;
}}
.ors-brand {{ display:flex; align-items:center; gap:8px; font-weight:750; font-size:1.08rem; color:var(--ors-text); white-space:nowrap; }}
.ors-brand .mark {{ width:28px; height:28px; border-radius:8px; background: var(--ors-blue); color:#fff; display:inline-flex; align-items:center; justify-content:center; font-size:15px; font-weight:800; }}
.ors-model {{ display:flex; align-items:center; gap:6px; color: var(--ors-muted); font-size: 0.9rem; max-width: 280px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.ors-model b {{ color: var(--ors-text); font-weight:600; overflow:hidden; text-overflow:ellipsis; }}
@media (max-width: 760px) {{ .ors-model {{ display:none; }} .ors-brand .word {{ display:none; }} }}

/* Cards and chips */
.ors-chip {{ display:inline-flex; align-items:center; gap:4px; padding:2px 10px 2px 7px; border-radius:999px; font-size:0.84rem; font-weight:600; line-height:1.6; white-space:nowrap; }}
.ors-chip .material-symbols-rounded {{ font-size:16px; }}
.ors-kv {{ color: var(--ors-muted); font-size: 0.9rem; }}
.ors-kv b {{ color: var(--ors-text); font-weight: 600; }}
.ors-mono, .ors-mono textarea {{ font-family: ui-monospace, "Cascadia Code", "SFMono-Regular", Consolas, monospace !important; font-size: 14.5px !important; line-height: 1.5 !important; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ background: var(--ors-surface); border-color: var(--ors-line) !important; border-radius: 14px !important; }}
.st-key-composer, .st-key-composer_mono {{ position: sticky; bottom: 12px; z-index: 50; }}
.st-key-composer > div, .st-key-composer_mono > div {{ box-shadow: 0 8px 24px rgba(23,34,53,0.08); }}
.st-key-composer_mono textarea {{ font-family: ui-monospace, "Cascadia Code", Consolas, monospace !important; font-size: 14.5px !important; }}
textarea {{ font-size: 15.5px !important; color: var(--ors-text) !important; background: #FFFFFF !important; }}
textarea::placeholder, input::placeholder {{ color: #5B6B82 !important; opacity: 1; }}
[data-testid="stTextArea"] [data-baseweb="textarea"], [data-testid="stTextArea"] [data-baseweb="base-input"] {{ background: #FFFFFF !important; }}
[data-testid="stChatMessage"] {{ background: transparent; padding: 6px 0; }}
.ors-user {{ background: #EEF2FF; border: 1px solid #C7D2FE; border-radius: 14px; padding: 10px 14px; }}
.ors-error-line {{ background:#FEF2F2; border-left: 4px solid #B91C1C; padding: 6px 10px; border-radius: 6px; font-family: ui-monospace, Consolas, monospace; font-size: 14px; white-space: pre; overflow-x: auto; color: #450A0A; }}
.ors-selected > div {{ border: 2px solid var(--ors-blue) !important; box-shadow: 0 0 0 3px #DBEAFE; }}
[class*="st-key-tplcard_sel_"] {{ border: 2px solid var(--ors-blue) !important; box-shadow: 0 0 0 3px #DBEAFE; background: #F8FAFF; }}
[class*="st-key-tplcard_"] {{ height: 100%; }}
.ors-hero {{ text-align:center; margin: 9vh 0 18px; }}
.ors-hero h1 {{ font-size: 2.1rem !important; }}
.ors-hero p {{ color: var(--ors-muted); font-size: 1.02rem; }}
.stButton button, .stDownloadButton button, .stFormSubmitButton button {{ border-radius: 10px; font-weight: 600; min-height: 40px; }}
.stButton button[kind="primary"], .stButton button[data-testid="stBaseButton-primary"] {{ background: var(--ors-blue); border-color: var(--ors-blue); color: #FFFFFF; }}
.stButton button[data-testid="stBaseButton-primary"]:hover {{ background: #1E40AF; border-color:#1E40AF; color:#fff; }}
.stButton button[data-testid="stBaseButton-primary"] p {{ color: #FFFFFF !important; }}
[data-testid="stExpander"] details {{ border-radius: 12px; border-color: var(--ors-line); background: var(--ors-surface); }}
[data-testid="stExpander"] summary p {{ font-weight: 600; }}
.ors-kbd {{ font-size: 0.8rem; color: var(--ors-muted); white-space: nowrap; }}
.ors-kbd kbd {{ border:1px solid var(--ors-line); border-bottom-width:2px; border-radius:5px; padding:0 5px; background:#fff; font-size:0.78rem; }}
iframe[title="src.ui.mathlive_component.mathlive_editor"] {{ border-radius: 10px; }}
.sr-only {{ position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }}
.st-key-le_actions {{ position: sticky; bottom: 0; z-index: 60; background: rgba(246,248,251,0.97); border-top: 1px solid var(--ors-line); padding: 10px 0 !important; }}
.stButton button[data-testid="stBaseButton-tertiary"] {{ text-align:left; justify-content:flex-start; min-height: 40px; padding: 4px 8px; border-radius: 8px; color: var(--ors-text); }}
.stButton button[data-testid="stBaseButton-tertiary"]:hover {{ background: #EFF6FF; color: var(--ors-blue); }}
[class*="st-key-crow_"] {{ border-bottom: 1px solid #EEF2F7; padding-bottom: 4px; }}
@media (max-width: 640px) {{
  .st-key-le_con_head {{ display:none !important; }}
  [class*="st-key-crow_"] {{ border: 1px solid var(--ors-line); border-radius: 12px; padding: 10px 12px; margin-bottom: 8px; background: var(--ors-surface); }}
  .st-key-ors_topbar {{ margin: 0 -12px 12px !important; padding-left: 12px !important; padding-right: 12px !important; }}
  .ors-hero {{ margin-top: 4vh; }}
  .ors-hero h1 {{ font-size: 1.6rem !important; }}
}}
.stElementContainer:has(.ors-css-anchor) {{ display:none !important; }}
</style>
<span class="ors-css-anchor"></span>
"""
    )
