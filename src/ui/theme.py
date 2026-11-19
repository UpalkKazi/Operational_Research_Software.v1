"""Visual system for OR Studio."""

import streamlit as st

CSS = """
<style>
:root {
  --ink: #101114;
  --muted: #666a73;
  --line: rgba(15, 23, 42, .10);
  --surface: rgba(255, 255, 255, .82);
  --accent: #0a84ff;
}
.stApp {
  background:
    radial-gradient(circle at 10% -10%, rgba(10,132,255,.10), transparent 34rem),
    radial-gradient(circle at 95% 5%, rgba(175,82,222,.08), transparent 28rem),
    #f5f5f7;
  color: var(--ink);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
  background: rgba(246, 246, 248, .86);
  border-right: 1px solid var(--line);
}
.block-container { max-width: 1180px; padding-top: 2.2rem; padding-bottom: 4rem; }
h1, h2, h3 { letter-spacing: -.035em; }
h1 { font-size: clamp(2.2rem, 5vw, 4rem) !important; font-weight: 720 !important; }
h2 { font-weight: 680 !important; }
p, label, [data-testid="stCaptionContainer"] { color: var(--muted); }
.or-eyebrow {
  color: var(--accent); font-size: .78rem; font-weight: 700;
  letter-spacing: .12em; text-transform: uppercase; margin-bottom: .4rem;
}
.or-hero {
  padding: 1.2rem 0 1.3rem; border-bottom: 1px solid var(--line); margin-bottom: 1rem;
}
.or-hero p { font-size: 1.08rem; max-width: 720px; margin-top: -.4rem; }
.or-card {
  background: var(--surface); border: 1px solid var(--line); border-radius: 20px;
  padding: 1rem 1.1rem; box-shadow: 0 12px 35px rgba(15,23,42,.05);
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: .35rem; background: rgba(118,118,128,.10); padding: .28rem;
  border-radius: 13px; width: fit-content;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  height: 2.3rem; padding: 0 1rem; border-radius: 10px;
}
[data-testid="stTabs"] [aria-selected="true"] {
  background: white; box-shadow: 0 1px 4px rgba(0,0,0,.10);
}
.stButton > button {
  border-radius: 999px; font-weight: 650; min-height: 2.7rem;
  border: 1px solid var(--line);
}
.stButton > button[kind="primary"] {
  background: var(--accent); color: white; border: none;
}
.stButton > button[kind="primary"] p { color: white !important; }
[data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input,
[data-baseweb="select"] > div {
  border-radius: 12px !important; border-color: var(--line) !important;
  background: rgba(255,255,255,.88) !important;
}
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
  border: 1px solid var(--line); border-radius: 14px; overflow: hidden;
}
[data-testid="stMetric"] {
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 16px; padding: .9rem 1rem;
}
.or-chip {
  display: inline-block; padding: .25rem .55rem; border-radius: 999px;
  font-size: .75rem; font-weight: 650; background: rgba(10,132,255,.10); color: #0568c9;
}
@media (max-width: 700px) {
  .block-container { padding: 1rem .8rem 3rem; }
  h1 { font-size: 2.25rem !important; }
}
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
