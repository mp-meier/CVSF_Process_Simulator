"""Light / dark appearance of the CVSF Process Simulator (Streamlit theme, CSS of the custom elements, Plotly)."""
import streamlit as st

LIGHT = dict(base="light", primaryColor="#1F4E79", backgroundColor="#FFFFFF", secondaryBackgroundColor="#F3F6FA",
             textColor="#1E1E1E")
DARK = dict(base="dark", primaryColor="#4A9EE0", backgroundColor="#0E1620", secondaryBackgroundColor="#16212D",
            textColor="#E6EAF0")

DARK_CSS = """
<style>
  .kpi {background:#16212D !important; border-color:#2A3A4C !important; box-shadow:none !important;}
  .kpi .lab {color:#9FB0C2 !important;} .kpi .val {color:#F0F4F8 !important;} .kpi .sub {color:#9AA7B5 !important;}
  .neu {border-left-color:#4A9EE0 !important;} .ok {border-left-color:#3CB371 !important;}
  .bad {border-left-color:#FF5A5A !important;}
  .stTabs [data-baseweb="tab-list"] {border-bottom-color:#2A3A4C !important;}
  .stTabs button[role="tab"] {background:#16212D !important;}
  .stTabs [aria-selected="true"] {background:#1F6FB2 !important;}
  section[data-testid="stSidebar"] {background:#111B26 !important; border-right-color:#243243 !important;}
  .brand .b1 {color:#DCE8F4 !important;} .brand .b2 {color:#8FA3B7 !important;}
  .sbtitle {color:#8FA3B7 !important;}
  .footer {border-top-color:#243243 !important; color:#8794A3 !important;}
  .appbar {box-shadow:0 4px 18px rgba(0,0,0,0.45) !important;}
</style>"""

# colours that are too dark on a dark background -> lighter equivalents
_MAP = {"#1e1e1e": "#e6eaf0", "#000000": "#e6eaf0", "#000": "#e6eaf0", "black": "#e6eaf0", "#1f4e79": "#5aa2e0",
        "#16395f": "#7fb6e6", "#0a1e33": "#cfe0f0", "#c00000": "#ff6b6b", "#444444": "#b8c2cc", "#333333": "#c3ccd5",
        "#555555": "#aab4be"}


_FILL = {"#f3f7fb": "rgba(255,255,255,0.05)", "#ffffff": "rgba(255,255,255,0.05)", "white": "rgba(255,255,255,0.05)",
         "#c8c8c8": "#5a6573", "#f3f6fa": "rgba(255,255,255,0.05)"}


def is_dark():
    return bool(st.session_state.get("dark_mode", False))


def apply(dark):
    """set the Streamlit theme; returns True if it changed (the caller then reruns the script)"""
    t = DARK if dark else LIGHT
    changed = False
    for k, v in t.items():
        if st._config.get_option(f"theme.{k}") != v:
            st._config.set_option(f"theme.{k}", v)
            changed = True
    return changed


def _c(v):
    return _MAP.get(v.lower(), v) if isinstance(v, str) else v


def darken(fig):
    """Plotly figure for the dark theme: transparent background, light fonts and grid, lighter dark trace colours"""
    try:
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font_color="#E6EAF0", legend_bgcolor="rgba(0,0,0,0)")
        fig.update_xaxes(gridcolor="#26364a", linecolor="#8796A6", zerolinecolor="#3a4c60", tickcolor="#8796A6")
        fig.update_yaxes(gridcolor="#26364a", linecolor="#8796A6", zerolinecolor="#3a4c60", tickcolor="#8796A6")
        for tr in fig.data:
            for path in ("line", "marker"):
                obj = getattr(tr, path, None)
                if obj is not None and hasattr(obj, "color") and isinstance(obj.color, str):
                    obj.color = _c(obj.color)
                if path == "marker" and obj is not None and getattr(obj, "line", None) is not None \
                        and isinstance(obj.line.color, str):
                    obj.line.color = _c(obj.line.color)
            if hasattr(tr, "textfont") and tr.textfont is not None and isinstance(tr.textfont.color, str):
                tr.textfont.color = _c(tr.textfont.color)
        for a in fig.layout.annotations or []:
            if a.font is not None and isinstance(a.font.color, str):
                a.font.color = _c(a.font.color)
            elif a.font is None or a.font.color is None:
                a.font.color = "#E6EAF0"
            if isinstance(a.arrowcolor, str):
                a.arrowcolor = _c(a.arrowcolor)
        for sh in fig.layout.shapes or []:
            if sh.line is not None and isinstance(sh.line.color, str):
                sh.line.color = _c(sh.line.color)
            if isinstance(sh.fillcolor, str):
                sh.fillcolor = _FILL.get(sh.fillcolor.lower(), sh.fillcolor)
    except Exception:                                          # noqa: BLE001  (appearance only)
        pass
    return fig


def install():
    """route all plotly_chart calls (st.plotly_chart and columns/containers) through darken() in dark mode"""
    from streamlit.delta_generator import DeltaGenerator
    if getattr(DeltaGenerator, "_cvsf_pc", None) is None:
        orig = DeltaGenerator.plotly_chart
        DeltaGenerator._cvsf_pc = orig

        def plotly_chart(self, fig, *a, **k):
            if is_dark():
                fig = darken(fig)
            return orig(self, fig, *a, **k)
        DeltaGenerator.plotly_chart = plotly_chart
    if getattr(st, "_cvsf_pc", None) is None:
        st._cvsf_pc = st.plotly_chart

        def st_plotly_chart(fig, *a, **k):
            if is_dark():
                fig = darken(fig)
            return st._cvsf_pc(fig, *a, **k)
        st.plotly_chart = st_plotly_chart
