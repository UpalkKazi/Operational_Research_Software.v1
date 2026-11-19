"""MathLive Streamlit component (bi-directional).

MathLive (MIT, https://cortexjs.io/mathlive/) is vendored under
``mathlive_build/vendor`` so the editor works without a CDN.  The component
returns the current LaTeX string, sending it on every edit (debounced) and
immediately on blur so a Solve click never loses the last edit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import streamlit.components.v1 as components

_component_func = components.declare_component(
    "mathlive_editor",
    path=str(Path(__file__).parent / "mathlive_build"),
)


def mathlive_editor(
    label: str,
    initial_latex: str = "",
    height: Optional[int] = None,
    key: str = "mathlive",
    read_only: bool = False,
    toolbar_mode: str = "or_full",
    mode: str = "expression",
    variables: Optional[List[Dict[str, str]]] = None,
    focus_token: Optional[str] = None,
) -> Optional[str]:
    """Render one MathLive field with the Symbols keypad.

    ``mode`` is ``"expression"`` (relations allowed) or ``"objective"``
    (relations marked unsolvable).  ``variables`` is a list of
    ``{"name", "latex"}`` shown as insertable keys.  Returns the latest LaTeX,
    or ``None`` before the first edit.
    """
    return _component_func(
        label=label,
        initial_latex=initial_latex,
        read_only=read_only,
        mode=mode,
        variables=variables or [],
        focus_token=focus_token,
        key=key,
        default=None,
    )
