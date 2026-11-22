"""CVSF Model – graphical user interface (Streamlit).

Start:  streamlit run gui/app.py      (or start_gui.bat / start_gui.sh in the package root)

The interface collects the inputs, calls the model code in ../scripts via engine.py and visualizes the results
(filtration module: cake filtration, gas deliquoring, evaporation; two-stage washing)."""
import io
import json
import os
import sys
import tempfile

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components

import base64

import calibration as C
import database as D
import engine as E
import apparatus3d as A3
import theme as T
import target_page as TP

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import model_update as MU                                                     # noqa: E402

_MV = MU.current()
APP_NAME = "CVSF Process Simulator"
SW_VERSION = "1.2"
APP_VERSION = f"Model {_MV['tag'] or _MV['commit'] or '?'}"
st.set_page_config(page_title=APP_NAME, page_icon=os.path.join(ASSETS, "cvsf_favicon.png"), layout="wide",
                   initial_sidebar_state="expanded",
                   menu_items={"About": f"{APP_NAME} {SW_VERSION} – {APP_VERSION}\n\nMechanistic model of the continuous vacuum "
                                        "screw filter (CVSF): cake filtration, gas deliquoring, evaporation, and "
                                        "two-stage washing.\n\nM.P. Meier, M. Vogel, L. Ohm – TU Dortmund University"})


# appearance: light / dark mode (stored as user preference)
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = bool(C.get_pref("dark_mode", False))
if T.apply(st.session_state.dark_mode):
    st.rerun()
T.install()


def _toggle_dark():
    C.set_pref("dark_mode", bool(st.session_state.dark_mode))


def _b64(name):
    with open(os.path.join(ASSETS, name), "rb") as f:
        return base64.b64encode(f.read()).decode()


ICON_B64 = _b64("cvsf_icon.svg")

C_BP, C_C, C_N = "#E6AF2D", "#00A0FF", "#A0A0A0"
SHAPE_COL = {"bipyramidal": C_BP, "cuboid": C_C, "needle": C_N}
RED, GREEN, BLUE, DARK = "#C00000", "#2E8B57", "#1F4E79", "#1E1E1E"

st.markdown("""
<style>
  [data-testid="stToolbar"] {display: none;}
  header[data-testid="stHeader"] {background: transparent; height: 2.4rem;}
  .block-container {padding-top: 1.2rem; padding-bottom: 1rem; max-width: 1680px;}
  /* product header */
  .appbar {display:flex; align-items:center; gap:18px; padding:14px 22px; border-radius:14px; margin-bottom:14px;
           background: linear-gradient(110deg, #0A1E33 0%, #16395F 55%, #1F4E79 100%); color:#fff;
           box-shadow: 0 4px 14px rgba(10,30,51,0.18);}
  .appbar img {width:62px; height:62px; border-radius:14px; box-shadow: 0 2px 8px rgba(0,0,0,0.35);}
  .appbar .t1 {font-size:1.65rem; font-weight:800; letter-spacing:0.5px; line-height:1.1;}
  .appbar .t1 span {font-weight:400; color:#BFD3E6;}
  .appbar .t2 {font-size:0.86rem; color:#BFD3E6; margin-top:3px; letter-spacing:0.3px;}
  .appbar .sp {flex:1;}
  .chip {display:inline-block; padding:4px 11px; margin-left:6px; border-radius:999px; font-size:0.76rem;
         background: rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.25); color:#EAF2FA;}
  .chip.v {background:#E6AF2D; color:#1E1E1E; border-color:#E6AF2D; font-weight:650;}
  /* KPI cards */
  .kpi {border-radius: 12px; padding: 11px 15px; background: #FFFFFF; border: 1px solid #E1E6EE; height: 100%;
        box-shadow: 0 1px 4px rgba(16,40,70,0.06);}
  .kpi .lab {font-size: 0.74rem; color: #5A6573; margin-bottom: 3px; letter-spacing: 0.2px; font-weight: 600;}
  .kpi .val {font-size: 1.4rem; font-weight: 700; color: #0A1E33;}
  .kpi .sub {font-size: 0.74rem; color: #6B7684;}
  .ok {border-left: 5px solid #2E8B57;} .bad {border-left: 5px solid #C00000;} .neu {border-left: 5px solid #1F4E79;}
  /* tabs */
  .stTabs [data-baseweb="tab-list"] {gap: 4px; border-bottom: 1px solid #DCE3EB;}
  .stTabs button[role="tab"] {padding: 6px 16px !important; border-radius: 8px 8px 0 0; background: #F3F6FA;}
  .stTabs [aria-selected="true"] {background: #16395F !important; color: #fff !important;}
  .stTabs [aria-selected="true"] p {color: #fff !important;}
  .stTabs [data-baseweb="tab-highlight"] {display:none;}
  /* sidebar */
  section[data-testid="stSidebar"] {background: #F3F6FA; border-right: 1px solid #DCE3EB;}
  div[data-testid="stSidebar"] .stNumberInput label, div[data-testid="stSidebar"] .stSelectbox label {font-size: 0.85rem;}
  .brand {display:flex; align-items:center; gap:12px; margin: -2.2rem 0 18px 0;}
  .brand img {width:52px; height:52px; border-radius:12px;}
  .brand .b1 {font-size:1.45rem; font-weight:800; color:#16395F; letter-spacing:1.5px; line-height:1.05;}
  .brand .b2 {font-size:0.68rem; font-weight:600; color:#5A6B7D; letter-spacing:2.2px;}
  .sbtitle {font-size:0.78rem; font-weight:700; color:#5A6573; letter-spacing:1px; text-transform:uppercase;
            margin: 4px 0 6px 2px;}
  /* footer */
  .footer {margin-top: 28px; padding: 10px 4px; border-top: 1px solid #E1E6EE; color:#7A8694; font-size: 0.76rem;
           display:flex; justify-content: space-between;}
</style>""", unsafe_allow_html=True)


if T.is_dark():
    st.markdown(T.DARK_CSS, unsafe_allow_html=True)


def kpi(col, label, value, sub="", kind="neu"):
    col.markdown(f'<div class="kpi {kind}"><div class="lab">{label}</div><div class="val">{value}</div>'
                 f'<div class="sub">{sub}</div></div>', unsafe_allow_html=True)


def fmt(x, nd=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "–"
    return f"{x:.{nd}f}"


def sci(x, nd=2):
    return "–" if x is None else f"{x:.{nd}e}".replace("e+0", "·10^").replace("e+", "·10^").replace("e-0", "·10^-")


# ------------------------------------------------------------------------------------------------------------
# state: inputs (load / save)
# ------------------------------------------------------------------------------------------------------------
if "inp" not in st.session_state:
    _i = E.Inputs()
    _i.shape, _i.psd_results, _i.psd_descriptors = E.example_paths(list(E.EXAMPLES)[0])
    _i.psd_mode = "file"
    st.session_state.inp = _i
if "tmpdir" not in st.session_state:
    st.session_state.tmpdir = tempfile.mkdtemp(prefix="cvsf_gui_")
I = st.session_state.inp


def save_upload(up):
    if up is None:
        return None
    p = os.path.join(st.session_state.tmpdir, up.name)
    with open(p, "wb") as f:
        f.write(up.getbuffer())
    return p


# ------------------------------------------------------------------------------------------------------------
# sidebar: inputs
# ------------------------------------------------------------------------------------------------------------
sb = st.sidebar
sb.markdown(f'''<div class="brand"><img src="data:image/svg+xml;base64,{ICON_B64}"/><div><div class="b1">CVSF</div>
<div class="b2">PROCESS SIMULATOR</div></div></div>''', unsafe_allow_html=True)
sb.toggle("Dark mode", key="dark_mode", on_change=_toggle_dark, help="Switch between light and dark appearance "
          "(remembered for the next start).")
if "mode" not in st.session_state:
    st.session_state.mode = "Simulation"
_MICON = {"Simulation": ":material/play_circle: ", "Calibration": ":material/model_training: ",
          "Experiment design": ":material/science: "}
sb.segmented_control("Mode", list(_MICON), key="mode", width="stretch", format_func=lambda m: _MICON[m] + m,
                     help="Simulation: predict the process for given inputs. Calibration: update the model parameters "
                          "with experimental data of completed CVSF runs (Bayesian calibration). Experiment design: "
                          "plan the experiments that improve the model most (Bayesian experimental design).")
MODE = st.session_state.mode or "Simulation"
_MANUAL = os.path.join(os.path.dirname(ASSETS), "docs", "CVSF_Process_Simulator_Manual.pdf")
if os.path.exists(_MANUAL):
    sb.download_button("User manual (PDF)", open(_MANUAL, "rb").read(), "CVSF_Process_Simulator_Manual.pdf",
                       icon=":material/menu_book:", width="stretch")
st.markdown(f'''<div class="appbar"><img src="data:image/svg+xml;base64,{ICON_B64}"/>
<div><div class="t1">CVSF <span>Process Simulator</span></div>
<div class="t2">Continuous vacuum screw filter · mechanistic process model</div></div><div class="sp"></div>
<div><span class="chip">Cake filtration</span><span class="chip">Gas deliquoring</span><span class="chip">Evaporation</span>
<span class="chip">Two-stage washing</span><span class="chip v">{APP_VERSION}</span></div></div>''', unsafe_allow_html=True)

def _footer():
    st.markdown(f'<div class="footer"><span>{APP_NAME} {SW_VERSION} · {APP_VERSION} (CVSF_Model_Filtration_Deliquoring_Washing_V01)'
                '</span><span>M.P. Meier, M. Vogel, L. Ohm · TU Dortmund University, Laboratory of Plant and Process Design'
                '</span></div>', unsafe_allow_html=True)


if MODE == "Experiment design":
    import design_page
    sb.markdown('<div class="sbtitle">Experiment design</div>', unsafe_allow_html=True)
    sb.markdown("1. Choose the current model state and the experiment types\n2. Define the design spaces\n"
                "3. **Compute experiment plan** (Bayesian optimization of the information gain)\n"
                "4. Download the plan as Excel template, carry out the experiments, upload them in the mode "
                "Calibration")
    design_page.render(kpi)
    _footer()
    st.stop()

if MODE == "Calibration":
    import calib_page
    sb.markdown('<div class="sbtitle">Calibration workflow</div>', unsafe_allow_html=True)
    sb.markdown("1. **Add data:** upload the filled Excel template and the PSD files, check, add as dataset\n"
                "2. **Experiment database:** activate / deactivate datasets and experiments (with reason)\n"
                "3. **Recalibrate model** with all active experiments, check the results\n"
                "4. **Adopt** the new model state – the simulation uses it")
    sb.caption("Experiment database and parameter sets: " + C.storage_root())
    calib_page.render(kpi, st.session_state.tmpdir)
    _footer()
    st.stop()

# ---- model parameter set (simulation)
SETS = C.list_sets()
_names = list(SETS)
_CUR = D.all_current()
if st.session_state.get("param_set") not in _names:
    _c = _CUR.get("L-alanine / water")
    st.session_state.param_set = _c if _c in _names else C.REFERENCE_NAME
sb.markdown('<div class="sbtitle">Model parameter set</div>', unsafe_allow_html=True)
st.session_state.param_set = sb.selectbox(
    "Model parameter set", _names, index=_names.index(st.session_state.param_set), label_visibility="collapsed",
    format_func=lambda n: ("★ " if n in _CUR.values() or (n == C.REFERENCE_NAME and "L-alanine / water" not in _CUR)
                           else "") + n,
    help="Parameters A, B, μs, a, b and material data; new sets are created in the mode Calibration.")
if st.session_state.get("applied_set") != st.session_state.param_set:
    C.apply_set(I, SETS[st.session_state.param_set])
    st.session_state.applied_set = st.session_state.param_set
ACTIVE = SETS[st.session_state.param_set]
I.param_set = ACTIVE["name"]
_mat = ACTIVE.get("material_system") or ACTIVE.get("material", {}).get("name", "")
try:
    if D.is_outdated(_mat, SETS):
        sb.caption(f":orange[New active experiments of '{_mat}' are not yet in the current model state – "
                   "recalibrate in the mode Calibration.]")
except Exception:                                   # noqa: BLE001
    pass
sb.markdown('<div class="sbtitle">Input parameters</div>', unsafe_allow_html=True)
with sb.expander("Load / save input set", expanded=False, icon=":material/folder_open:"):
    up_json = st.file_uploader("Load inputs (JSON)", type=["json"], key="upjson")
    if up_json is not None and st.button("Apply loaded inputs"):
        st.session_state.inp = E.Inputs.from_json(up_json.getvalue().decode())
        st.rerun()
    st.download_button("Save current inputs (JSON)", I.to_json(), file_name="cvsf_inputs.json", mime="application/json")

# ---- 1 particle system
with sb.expander("Particle system", expanded=True, icon=":material/grain:"):
    shapes = list(E.SHAPES)
    I.shape = st.selectbox("Particle shape", shapes, index=shapes.index(I.shape),
                           format_func=lambda s: E.SHAPES[s]["label"])
    modes = {"file": "Measured PSD (Excel file of dynamic image analysis)",
             "lognormal": "Log-normal PSD (d50,3 and σg)",
             "characteristic": "Characteristic diameters (d10,3 / d50,3 / d90,3)"}
    I.psd_mode = st.radio("PSD input", list(modes), index=list(modes).index(I.psd_mode),
                          format_func=lambda m: modes[m])
    if I.psd_mode == "file":
        cur_ex = next((n for n in E.EXAMPLES if E.example_paths(n)[1] == I.psd_results), None)
        if cur_ex is not None or not I.psd_results:
            src0 = 0
        elif str(I.psd_results).startswith(st.session_state.tmpdir):
            src0 = 1
        else:
            src0 = 2
        src = st.radio("Source", ["Example data", "Upload", "Local path"], index=src0, horizontal=True)
        if src == "Example data":
            names = [n for n in E.EXAMPLES if E.EXAMPLES[n]["shape"] == I.shape] or list(E.EXAMPLES)
            ex = st.selectbox("Example", names, index=names.index(cur_ex) if cur_ex in names else 0)
            shp, res, desc = E.example_paths(ex)
            I.shape, I.psd_results, I.psd_descriptors = shp, res, desc
            st.caption(f"`{os.path.basename(res)}`" + (f" + `{os.path.basename(desc)}`" if desc else ""))
        elif src == "Upload":
            u1 = st.file_uploader("PSDResults_*.xlsx (PSD and agglomeration degree)", type=["xlsx"])
            p1 = save_upload(u1)
            if p1:
                I.psd_results = p1
            if I.shape != "bipyramidal":
                u2 = st.file_uploader("ImageDescriptors_*.xlsx (min./max. Feret diameters)", type=["xlsx"])
                p2 = save_upload(u2)
                if p2:
                    I.psd_descriptors = p2
        else:
            I.psd_results = st.text_input("Path to PSDResults_*.xlsx", I.psd_results or "")
            if I.shape != "bipyramidal":
                I.psd_descriptors = st.text_input("Path to ImageDescriptors_*.xlsx", I.psd_descriptors or "")
        ov = st.checkbox("Override agglomeration degree Ag3 of the file", value=I.Ag3 is not None)
        I.Ag3 = st.number_input("Ag3 / -", 0.0, 0.99, float(I.Ag3 or 0.3), 0.01) if ov else None
    else:
        if I.psd_mode == "lognormal":
            c1, c2 = st.columns(2)
            I.d50 = c1.number_input("d50,3 / µm", 1.0, 2500.0, float(I.d50), 5.0)
            I.sigma_g = c2.number_input("σg / -", 0.05, 1.5, float(I.sigma_g), 0.05)
        else:
            c1, c2, c3 = st.columns(3)
            I.d10 = c1.number_input("d10,3 / µm", 0.0, 2500.0, float(I.d10 or 25.0), 1.0) or None
            I.d50 = c2.number_input("d50,3 / µm", 0.0, 2500.0, float(I.d50 or 60.0), 1.0) or None
            I.d90 = c3.number_input("d90,3 / µm", 0.0, 2500.0, float(I.d90 or 150.0), 1.0) or None
            st.caption("Zero = not specified. σg is calculated assuming a log-normal Q3 distribution.")
        pm = {"preset": "Preset of the particle shape", "effective": "Effective sphericity ψ",
              "geometric": "Geometric sphericity + agglomeration degree"}
        I.psi_mode = st.radio("Sphericity", list(pm), index=list(pm).index(I.psi_mode), format_func=lambda m: pm[m])
        if I.psi_mode == "preset":
            st.caption(f"ψ_eff = {E.SHAPES[I.shape]['psi_eff']:.2f} (agglomeration-corrected, filtration study)")
        elif I.psi_mode == "effective":
            I.psi_eff = st.slider("ψ_eff / -", 0.2, 1.0, float(I.psi_eff), 0.01)
        else:
            c1, c2 = st.columns(2)
            I.psi_geo = c1.number_input("ψ (geometric) / -", 0.2, 1.0, float(I.psi_geo), 0.01)
            I.Ag3 = c2.number_input("Ag3 / -", 0.0, 0.99, float(I.Ag3 or 0.3), 0.01)
            st.caption("ψ_eff = ψ · (1 − Ag3 / A), Fit F1")

# ---- 2 operation
with sb.expander("Operating point", expanded=True, icon=":material/speed:"):
    c1, c2 = st.columns(2)
    I.Q = c1.number_input("Q_susp / mL min⁻¹", 1.0, 300.0, float(I.Q), 5.0)
    I.ws = c2.number_input("w_solid / wt.-%", 0.5, 30.0, float(100 * I.ws), 0.5) / 100
    nm = st.radio("Rotational screw speed", ["set", "alpha"], index=["set", "alpha"].index(I.n_mode), horizontal=True,
                  format_func=lambda m: "set n_screw" if m == "set" else "from target filling degree")
    I.n_mode = nm
    if nm == "set":
        I.n = st.number_input("n_screw / rpm", 0.1, 20.0, float(I.n), 0.5)
    else:
        I.alpha_target = st.slider("Target filling degree α / %", 20, 100, int(100 * I.alpha_target), 5) / 100
    c1, c2 = st.columns(2)
    I.dp = c1.number_input("Δp / mbar", 5.0, 900.0, float(I.dp), 5.0)
    I.T = c2.number_input("ϑ_susp / °C", 1.0, 80.0, float(I.T), 1.0)

# ---- 3 apparatus
with sb.expander("Apparatus and screw design", expanded=False, icon=":material/precision_manufacturing:"):
    sk = list(E.SETUPS) + ["custom"]
    I.setup = st.selectbox("Module geometry", sk, index=sk.index(I.setup),
                           format_func=lambda s: E.SETUPS[s]["label"] if s in E.SETUPS else "Custom")
    if I.setup in E.SETUPS:
        g = E.SETUPS[I.setup]; I.L_f, I.L_T, I.D_i = g["L_f"], g["L_T"], g["D_i"]
        st.caption(f"Filter length L_f = {I.L_f:g} cm · transport zone L_T = {I.L_T:g} cm · "
                   f"d_i,module = {1e3 * I.D_i:.1f} mm")
    else:
        c1, c2, c3 = st.columns(3)
        I.L_f = c1.number_input("L_f / cm", 1.0, 50.0, float(I.L_f), 0.5)
        I.L_T = c2.number_input("L_T / cm", 0.0, 50.0, float(I.L_T), 0.5)
        I.D_i = c3.number_input("d_i,mod / mm", 10.0, 100.0, float(1e3 * I.D_i), 0.1) / 1e3
    scr = list(E.SCREWS) + ["custom"]
    sel = st.selectbox("Screw design", scr, index=scr.index(I.screw) if I.screw in scr else 0,
                       format_func=lambda s: E.SCREWS[s]["label"] if s in E.SCREWS else "Custom")
    I.screw = sel
    if sel in E.SCREWS:
        s = E.SCREWS[sel]; I.d_i, I.P, I.N, I.w = s["d_i"], s["P"], int(s["N"]), s["w"]
    else:
        c1, c2 = st.columns(2)
        I.d_i = c1.number_input("Shaft diameter d_i / mm", 5.0, 24.0, float(1e3 * I.d_i), 0.5) / 1e3
        I.P = c2.number_input("Pitch distance P / mm", 4.0, 60.0, float(1e3 * I.P), 0.5) / 1e3
        I.N = int(c1.number_input("Number of flights", 1, 4, int(I.N), 1))
        I.w = c2.number_input("Blade width / mm", 0.1, 5.0, float(1e3 * I.w), 0.1) / 1e3
        st.caption("Outer screw diameter d_o = 25 mm.")
    c1, c2 = st.columns(2)
    I.R_m = c1.number_input("R_m / 10⁸ m⁻¹", 0.1, 100.0, float(I.R_m / 1e8), 0.5) * 1e8
    I.b = c2.number_input("Filter width B_f / mm", 5.0, 100.0, float(1e3 * I.b), 1.0) / 1e3

# ---- 4 air
with sb.expander("Air flow (evaporation)", expanded=False, icon=":material/air:"):
    c1, c2, c3 = st.columns(3)
    I.t_air = c1.number_input("ϑ_air / °C", 0.0, 80.0, float(I.t_air), 1.0)
    I.RH = c2.number_input("φ_RH / %", 0.0, 100.0, float(100 * I.RH), 5.0) / 100
    I.Q_air = c3.number_input("Q_air / L min⁻¹", 0.1, 50.0, float(I.Q_air), 1.0)

# ---- 5 model parameters
with sb.expander("Model parameters (advanced)", expanded=False, icon=":material/tune:"):
    c1, c2 = st.columns(2)
    I.A = c1.number_input("A (Fit F1)", 1.0, 10.0, float(I.A), 0.01)
    I.B = c2.number_input("B (Fit F2)", 0.5, 5.0, float(I.B), 0.01)
    I.use_theta = st.checkbox("Particle backslip via θm correlation (Fit 1)", value=I.use_theta)
    c1, c2, c3 = st.columns(3)
    I.mu_s = c1.number_input("μs", 0.5, 2.0, float(I.mu_s), 0.001, format="%.4f")
    I.a_rtd = c2.number_input("a", -1.0, 1.0, float(I.a_rtd), 0.001, format="%.4f")
    I.b_rtd = c3.number_input("b", -1.0, 1.0, float(I.b_rtd), 0.001, format="%.4f")
    c1, c2 = st.columns(2)
    I.rhos = c1.number_input("ρ_solid / kg m⁻³", 500.0, 5000.0, float(I.rhos), 10.0)
    I.sigma = c2.number_input("σ_ML / mN m⁻¹", 10.0, 100.0, float(1e3 * I.sigma), 0.5) / 1e3
    st.caption("Changes here deviate from the selected parameter set.")
    if st.button("Reset to the parameter set"):
        C.apply_set(I, ACTIVE); I.use_theta = True
        st.rerun()

sb.markdown("---")
run_btn = sb.button("Run simulation", type="primary", width="stretch", icon=":material/play_arrow:")
sb.caption(f"Parameter set: {ACTIVE['name']} · material system: {ACTIVE.get('material', {}).get('name', '–')}. "
           "Liquid properties: L-alanine/water mother liquor; washing liquids ethanol/water.")


# ------------------------------------------------------------------------------------------------------------
# calculation
# ------------------------------------------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _run(inp_json):
    inp = E.Inputs.from_json(inp_json)
    r = E.run_filtration(inp)
    s = E.studies(r)
    return r, s




if run_btn or "run" not in st.session_state:
    try:
        with st.spinner("Calculating filtration module …"):
            st.session_state.run, st.session_state.study = _run(I.to_json())
            st.session_state.pop("wash", None)
            st.session_state.error = None
    except Exception as ex:                                 # noqa: BLE001
        st.session_state.error = str(ex)
        st.session_state.pop("run", None)

if st.session_state.get("error"):
    st.error(f"Calculation not possible: {st.session_state.error}")
    st.stop()

R = st.session_state.run
S = st.session_state.study
K, inp = R["kpi"], R["inp"]
res, part = R["res"], R["part"]
if run_btn is False and inp.to_json() != I.to_json():
    st.info("Inputs were changed – press **Run simulation** to update the results.", icon="ℹ️")

# ---- KPI row
c = st.columns(6)
ok = K["finished"]
kpi(c[0], "End of cake formation z_S1", f"{fmt(K['z_S1'])} cm",
    f"L_f = {inp.L_f:g} cm · {'completed on filter' if ok else 'NOT completed on filter'}", "ok" if ok else "bad")
@st.cache_data(show_spinner=False)
def _phi_ci(inp_json, sdB):
    return C.phi_interval(E.Inputs.from_json(inp_json), dict(std=dict(B=sdB)))


_sdB = float(ACTIVE.get("std", {}).get("B", 0) or 0) if abs(inp.B - ACTIVE["params"]["B"]) < 1e-9 else 0.0
_ci = _phi_ci(inp.to_json(), _sdB) if ok and _sdB > 0 else None
kpi(c[1], "Residual moisture φ_RM(L_f + L_T)", f"{fmt(100 * K['phi_end'], 1)} %" if ok else "–",
    (f"95 % interval (B): {100 * _ci[0]:.1f}–{100 * _ci[1]:.1f} % · " if _ci else "")
    + (f"at z = {inp.L_f + inp.L_T:g} cm · S = {fmt(K['S_end'])}" if ok else "cake formation not completed"))
kpi(c[2], "Dimensionless residence time θm", fmt(K["theta_m"], 3),
    f"τ on filter = {fmt(K['tau_f'])} min · v_p,ax = {fmt(60e3 * K['v_ax'], 1)} mm/min")
kpi(c[3], "Filling degree α", f"{fmt(100 * K['alpha'], 0)} %", f"n_screw = {fmt(inp.n)} rpm",
    "ok" if 0.3 <= K["alpha"] <= 1.0 else "bad")
kpi(c[4], "Porosity ε · cake resistance α_FC", f"{fmt(100 * K['eps'], 1)} %", f"α_FC = {sci(K['alpha_s'])} m/kg")
kpi(c[5], "Minimum Δp for z_S1 = L_f", f"{fmt(K['dp_req'], 0)} mbar",
    f"applied: {inp.dp:g} mbar · h_c = {fmt(1e3 * K['h_c'], 1)} mm")
for w in R["warnings"]:
    st.warning(w, icon="⚠️")

tabs = st.tabs([":material/view_timeline: Filtration module", ":material/view_in_ar: 3D apparatus",
                ":material/grain: Particles & filter cake",
                ":material/insights: Process design", ":material/water_drop: Washing", ":material/download: Export",
                ":material/science: Experiments for this prediction", ":material/menu_book: Model & references"])


# ------------------------------------------------------------------------------------------------------------
# figure helpers
# ------------------------------------------------------------------------------------------------------------
def module_figure(R):
    inp, res, K = R["inp"], R["res"], R["kpi"]
    Lf, LT = inp.L_f, inp.L_T
    zmax = Lf + LT
    col = SHAPE_COL.get(inp.shape, C_BP)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.36, 0.34, 0.30], vertical_spacing=0.08,
                        subplot_titles=("Filtration module (axial coordinate z)", "Residual moisture φ_RM(z)",
                                        "Filter cake height h_c(z)"))
    # --- schematic in true dimensions (y = height above the filter medium in mm)
    D = 1e3 * inp.D_i
    pre = 1.0 if inp.setup == "current" else 0.0
    fig.add_shape(type="rect", x0=-pre, x1=zmax, y0=0, y1=D, line=dict(color=DARK, width=1.4),
                  fillcolor="#F3F7FB", row=1, col=1)
    fig.add_shape(type="rect", x0=0, x1=Lf, y0=-2.2, y1=0.0, line=dict(color=DARK, width=0.8),
                  fillcolor="#C8C8C8", row=1, col=1)
    # screw flights (helix projected onto the z-y plane)
    P = 100 * inp.P
    Nf = max(int(inp.N), 1)
    x = -pre - P
    while x < zmax:
        for k in range(Nf):
            xs = x + k * P / Nf
            xa, xb = max(xs, -pre), min(xs + 0.5 * P, zmax)
            if xb > xa:
                ya = 0.5 + (D - 1) * (xa - xs) / (0.5 * P); yb = 0.5 + (D - 1) * (xb - xs) / (0.5 * P)
                fig.add_shape(type="line", x0=xa, x1=xb, y0=ya, y1=yb, line=dict(color="#9A9A9A", width=1.2),
                              row=1, col=1)
        x += P
    shaft = 1e3 * inp.d_i
    fig.add_shape(type="rect", x0=-pre, x1=zmax, y0=D / 2 - shaft / 2, y1=D / 2 + shaft / 2, line=dict(width=0),
                  fillcolor="rgba(150,150,150,0.18)", row=1, col=1)
    zS = min(K["z_S1"], zmax)
    hc_end = 1e3 * K["h_c"]
    zc = np.asarray(R["hc_z"]); hc = 1e3 * np.asarray(R["hc"])
    # suspension above the growing cake (schematic level) until z_S1
    if zS > 0:
        top = hc_end + (min(1.6 * hc_end, 0.9 * D) - hc_end) * (1 - zc / max(zS, 1e-9))
        fig.add_trace(go.Scatter(x=np.r_[zc, zc[::-1]], y=np.r_[top, hc[::-1]], fill="toself", mode="lines",
                                 fillcolor="rgba(0,112,192,0.30)", line=dict(width=0), name="suspension",
                                 hoverinfo="skip"), row=1, col=1)
    # saturated filter cake (S = 1) up to z_S1, deliquored filter cake afterwards
    fig.add_trace(go.Scatter(x=np.r_[zc, zc[::-1]], y=np.r_[hc, np.zeros_like(hc)], fill="toself", fillcolor=col, mode="lines",
                             line=dict(color=col, width=1), name="filter cake, saturated (S = 1)", hoverinfo="skip"),
                  row=1, col=1)
    if zS < zmax:
        fig.add_trace(go.Scatter(x=[zS, zmax, zmax, zS], y=[0, 0, hc_end, hc_end], fill="toself", fillcolor=col,
                                 opacity=0.45, line=dict(width=0), mode="lines", name="filter cake, deliquored (S < 1)",
                                 hoverinfo="skip"), row=1, col=1)
    fig.add_vline(x=zS, line=dict(color=BLUE, width=2), row=1, col=1)
    fig.add_annotation(x=zS, y=D + 2.5, text=f"<b>z_S1 = {K['z_S1']:.2f} cm</b>", showarrow=False, xanchor="left",
                       font=dict(color=BLUE, size=12), row=1, col=1)
    fig.add_annotation(x=Lf / 2, y=-4.2, text="filter medium (frit, Δp)", showarrow=False, font=dict(size=11),
                       row=1, col=1)
    if LT > 0:
        fig.add_annotation(x=Lf + LT / 2, y=-4.2, text="transport zone (evaporation)", showarrow=False,
                           font=dict(size=11), row=1, col=1)
    fig.add_annotation(x=zmax, y=D + 2.5, text="→ washing module", showarrow=False, xanchor="right",
                       font=dict(size=10), row=1, col=1)
    fig.update_yaxes(title_text="y / mm", range=[-6, D + 5], showgrid=False, row=1, col=1)
    # --- residual moisture
    z, phi, phie = res["z"], 100 * np.asarray(res["phi"]), 100 * np.asarray(res["phi_evap"])
    fig.add_trace(go.Scatter(x=z, y=phi, name="φ_RM without evaporation", line=dict(color="#7F7F7F", dash="dot")),
                  row=2, col=1)
    fig.add_trace(go.Scatter(x=z, y=phie, name="φ_RM (filtration, deliquoring, evaporation)",
                             line=dict(color=col, width=3)), row=2, col=1)
    fig.add_hline(y=100 * K["phi_S1"], line=dict(color=BLUE, dash="dot", width=1), row=2, col=1,
                  annotation_text="φ_RM at S = 1", annotation_position="top right")
    fig.update_yaxes(title_text="φ_RM / %", row=2, col=1)
    # --- cake height
    zz = np.r_[R["hc_z"], [zmax]]
    hh = np.r_[1e3 * R["hc"], [1e3 * R["hc"][-1]]]
    fig.add_trace(go.Scatter(x=zz, y=hh, name="h_c", line=dict(color=DARK, width=2.5), showlegend=False),
                  row=3, col=1)
    fig.update_yaxes(title_text="h_c / mm", rangemode="tozero", row=3, col=1)
    for rr in (2, 3):
        for xx, cc, ds in [(Lf, RED, "dash"), (zmax, DARK, "dash"), (zS, BLUE, "dot")]:
            fig.add_vline(x=xx, line=dict(color=cc, width=1.2, dash=ds), row=rr, col=1)
    fig.add_annotation(x=Lf, y=1.0, yref="y2 domain", text="L_f", showarrow=False, xanchor="left",
                       font=dict(color=RED, size=11))
    fig.update_xaxes(title_text="z / cm", range=[-pre - 0.2, zmax + 0.6], row=3, col=1)
    fig.update_layout(height=760, template="simple_white", margin=dict(l=60, r=20, t=40, b=40),
                      legend=dict(orientation="h", y=-0.08), hovermode="x unified")
    return fig


# ------------------------------------------------------------------------------------------------------------
# tab 1: filtration module
# ------------------------------------------------------------------------------------------------------------
with tabs[0]:
    l, r = st.columns([2.5, 1.4])
    l.plotly_chart(module_figure(R), width="stretch")
    with r:
        st.markdown("#### Results")
        tab = pd.DataFrame([
            ("End of cake formation z_S1", f"{K['z_S1']:.3f}", "cm"),
            ("Filter length L_f", f"{inp.L_f:g}", "cm"),
            ("Residual moisture at S = 1", f"{100 * K['phi_S1']:.1f}", "%"),
            ("Residual moisture at end of filter L_f", fmt(100 * K["phi_Lf"], 2), "%"),
            ("Residual moisture at L_f + L_T", fmt(100 * K["phi_end"], 2) if ok else "–", "%"),
            ("  without evaporation", fmt(100 * K["phi_end_noevap"], 2) if ok else "–", "%"),
            ("Reduction by evaporation", fmt(100 * K["dphi_evap"], 2) if ok else "–", "%-pts."),
            ("Liquid saturation degree at L_f + L_T", fmt(K["S_end"], 3) if ok else "–", "-"),
            ("Filter cake height h_c", f"{1e3 * K['h_c']:.2f}", "mm"),
            ("θm", f"{K['theta_m']:.3f}", "-"),
            ("Axial particle velocity v_p,ax", f"{60e3 * K['v_ax']:.2f}", "mm/min"),
            ("Residence time on filter medium", f"{K['tau_f']:.2f}", "min"),
            ("Residence time in transport zone", f"{K['tau_T']:.2f}", "min"),
            ("Filling degree α", f"{100 * K['alpha']:.1f}", "%"),
            ("Rotational screw speed", f"{inp.n:.2f}", "rpm"),
            ("Solids mass flow", f"{1e3 * K['m_s']:.1f}", "g/h"),
            ("Minimum Δp for z_S1 = L_f", f"{K['dp_req']:.0f}", "mbar"),
        ], columns=["Quantity", "Value", "Unit"])
        st.dataframe(tab, hide_index=True, width="stretch", height=640)
    st.caption("Axial profiles are model predictions: the enclosed module does not allow spatially resolved sampling; "
               "experimentally, the residual moisture is accessible only at the module outlet.")

# ------------------------------------------------------------------------------------------------------------
# tab 2: particles
# ------------------------------------------------------------------------------------------------------------
with tabs[2]:
    l, r = st.columns([2.2, 1])
    x, Q3, dQ3 = part["centers"], part["Q3"], part["dQ3"]
    m = x > 0
    dx = np.gradient(np.log(np.where(m, x, 1)))
    q3 = np.where(m, dQ3 / np.maximum(dx, 1e-12), 0)
    q3 = q3 / max(q3.max(), 1e-12)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=x[m], y=100 * Q3[m], name="Q3 (model input)", line=dict(color=DARK, width=2.5)))
    if part.get("meas_x") is not None:
        fig.add_trace(go.Scatter(x=part["meas_x"], y=100 * part["meas_Q3"], mode="markers", name="Q3 measured",
                                 marker=dict(color=RED, size=7)))
    fig.add_trace(go.Scatter(x=x[m], y=q3[m], name="q3,lg (normalized)", fill="tozeroy",
                             line=dict(color=SHAPE_COL.get(inp.shape, C_BP)), opacity=0.5), secondary_y=True)
    for v, n, yy in [(K["d10"], "d10,3", 10), (K["d50"], "d50,3", 50), (K["d90"], "d90,3", 90)]:
        fig.add_trace(go.Scatter(x=[v, v], y=[0, yy], mode="lines", line=dict(color="#7F7F7F", dash="dot"),
                                 showlegend=False, hoverinfo="skip"))
        fig.add_annotation(x=np.log10(v), y=yy, text=f"{n} = {v:.0f} µm", showarrow=False, xanchor="right",
                           yanchor="bottom", font=dict(size=11))
    fig.update_xaxes(type="log", title_text="d_p / µm",
                     range=[np.log10(max(K["d10"] / 4, 1)), np.log10(K["d90"] * 3)])
    fig.update_yaxes(title_text="Q3 / %", range=[0, 102], secondary_y=False)
    fig.update_yaxes(title_text="q3,lg / - (normalized)", range=[0, 1.05], tickformat=".1f", secondary_y=True,
                     showgrid=False)
    fig.update_layout(template="simple_white", height=470, legend=dict(orientation="h", y=-0.2),
                      title="Particle size distribution")
    l.plotly_chart(fig, width="stretch")
    with r:
        st.markdown("#### Filter cake properties")
        st.dataframe(pd.DataFrame([
            ("Particle shape", E.SHAPES[inp.shape]["label"]),
            ("d10,3 / d50,3 / d90,3", f"{K['d10']:.0f} / {K['d50']:.0f} / {K['d90']:.0f} µm"),
            ("σg (log-normal)", f"{K['sigma_g']:.2f}"),
            ("Agglomeration degree Ag3", fmt(K["Ag3"], 2) if K["Ag3"] is not None else "– (not used)"),
            ("Geometric sphericity ψ", fmt(part.get("psi_geo"), 3) if part.get("psi_geo") else "–"),
            ("Effective sphericity ψ_eff", f"{K['psi_eff']:.3f}"),
            ("Porosity ε", f"{100 * K['eps']:.1f} %"),
            ("Spec. filter cake resistance α_FC", f"{sci(K['alpha_s'])} m/kg"),
            ("Permeability k", f"{sci(1 / (K['alpha_s'] * inp.rhos * (1 - K['eps'])))} m²"),
        ], columns=["Property", "Value"]), hide_index=True, width="stretch")
        st.caption("Porosity: modified linear packing model (Yu et al.); α_FC: additive Carman-Kozeny approach "
                   "(Bourcier et al.); sphericity corrected by the agglomeration degree (Fit F1, A = "
                   f"{inp.A:.2f}).")

# ------------------------------------------------------------------------------------------------------------
# tab 3: process design
# ------------------------------------------------------------------------------------------------------------
with tabs[3]:
    def _line_fig(x, ys, title, xt, xop):
        f = go.Figure()
        for y, nm, sty in ys:
            f.add_trace(go.Scatter(x=x, y=y, name=nm, mode="lines", line=sty))
        f.add_trace(go.Scatter(x=[x[0], x[-1]], y=[inp.L_f] * 2, mode="lines", name="L_f",
                               line=dict(color=RED, dash="dash", width=1.5)))
        f.add_trace(go.Scatter(x=[xop], y=[K["z_S1"]], mode="markers", marker=dict(size=12, color=RED, symbol="diamond"),
                               name="operating point"))
        f.update_layout(template="simple_white", height=360, title=title, xaxis_title=xt, yaxis_title="z_S1 / cm",
                        legend=dict(orientation="h", y=-0.3), margin=dict(t=50, b=10))
        f.update_yaxes(rangemode="tozero")
        return f
    c1, c2, c3 = st.columns(3)
    c1.plotly_chart(_line_fig(S["dp"], [(S["z_dp"], "z_S1", dict(color=BLUE, width=3))], "Pressure difference",
                              "Δp / mbar", inp.dp), width="stretch")
    c2.plotly_chart(_line_fig(S["Q"], [(S["z_Q"], "with particle backslip (θm)", dict(color=BLUE, width=3)),
                                       (S["z_Q_ideal"], "ideal transport (θm = 1)", dict(color="#7F7F7F", dash="dot"))],
                              "Throughput at constant filling degree",
                              f"Q_susp / mL min⁻¹  (Q/n = {inp.Q / inp.n:.1f} mL rpm⁻¹ min⁻¹)", inp.Q), width="stretch")
    c3.plotly_chart(_line_fig(S["T"], [(S["z_T"], "z_S1", dict(color=BLUE, width=3))], "Suspension temperature",
                              "ϑ_susp / °C", inp.T), width="stretch")
    q, qhi = S["Qmax"], float(S["Q"][-1])
    qtxt = (f"> {qhi:.0f} mL/min (limit not reached up to n_screw = 5 rpm)" if not np.isfinite(q)
            else ("below the studied range" if q == 0 else f"{q:.0f} mL/min"))
    st.markdown(f"**Design hints** – minimum pressure difference for complete cake formation on the filter medium: "
                f"**{K['dp_req']:.0f} mbar** · maximum suspension volume flow rate at the present filling degree "
                f"(n_screw adjusted proportionally): **{qtxt}**. Neglecting particle backslip (dotted line) "
                f"underestimates the required filter length.")

    st.markdown("#### Operating window: z_S1 over suspension volume flow rate and rotational screw speed")

    @st.cache_data(show_spinner=False)
    def _ow(inp_json):
        rr = E.run_filtration(E.Inputs.from_json(inp_json))
        return E.operating_window(rr)
    with st.spinner("Calculating operating window …"):
        OW = _ow(inp.to_json())
    zc = np.minimum(OW["z"], 3 * inp.L_f)
    fo = go.Figure()
    fo.add_trace(go.Contour(x=OW["Q"], y=OW["n"], z=zc, colorscale="Blues", ncontours=18,
                            colorbar=dict(title="z_S1 / cm"), contours=dict(showlabels=False),
                            hovertemplate="Q = %{x:.0f} mL/min<br>n = %{y:.2f} rpm<br>z_S1 = %{z:.2f} cm<extra></extra>"))
    fo.add_trace(go.Contour(x=OW["Q"], y=OW["n"], z=OW["z"], showscale=False, contours_coloring="none",
                            contours=dict(start=inp.L_f, end=inp.L_f, size=1, showlabels=True,
                                          labelfont=dict(color=RED, size=12)),
                            line=dict(color=RED, width=3), name="z_S1 = L_f", hoverinfo="skip"))
    fo.add_trace(go.Contour(x=OW["Q"], y=OW["n"], z=OW["alpha"], showscale=False, contours_coloring="none",
                            contours=dict(start=0.25, end=1.0, size=0.25, showlabels=True,
                                          labelfont=dict(color=DARK, size=11)),
                            line=dict(color=DARK, width=1.2, dash="dot"), name="filling degree α", hoverinfo="skip"))
    fo.add_trace(go.Scatter(x=[inp.Q], y=[inp.n], mode="markers", marker=dict(size=14, color=RED, symbol="diamond",
                            line=dict(color="white", width=1.5)), name="operating point"))
    fo.update_layout(template="simple_white", height=480, xaxis_title="Q_susp / mL min⁻¹",
                     yaxis_title="n_screw / rpm", legend=dict(orientation="h", y=-0.18), margin=dict(t=20))
    l, r = st.columns([2.2, 1])
    l.plotly_chart(fo, width="stretch")
    r.markdown("**Reading the map** – blue shading: end of cake formation z_S1 (capped at 3·L_f). "
               "**Red line:** z_S1 = L_f; operating points to the upper left of it complete cake formation on the "
               "filter medium and leave the remaining filter length for gas deliquoring. **Dotted lines:** filling "
               "degree α (labels as fraction); α > 1 indicates overfilling of the screw channel. All other inputs are "
               "kept at the values of the sidebar.")
    r.caption("θm correlation and filling degree were validated for n_screw = 1–5 rpm; values below 1 rpm are "
              "extrapolated.")

# ------------------------------------------------------------------------------------------------------------
# tab 4: washing
# ------------------------------------------------------------------------------------------------------------
with tabs[4]:
    st.markdown("Two-stage displacement washing (washing study): ADE with flowing and stagnant pore compartments, "
                "coupled to the filtration module (porosity, α_FC, h_c, θm, filling degree). Washing step 1: "
                "ethanol/water mixture, washing step 2: ethanol.")
    with st.form("wash_form"):
        c1, c2, c3, c4, c5 = st.columns(5)
        dpw = c1.number_input("Δp washing modules / mbar", 10.0, 500.0, 100.0, 5.0)
        psi1 = c2.number_input("Ethanol : water (vol.) step 1", 0.5, 50.0, 4.0, 0.5)
        xs = c3.number_input("Target X* / %", 0.001, 10.0, 0.03, 0.01, format="%.3f") / 100
        auto = c4.checkbox("WR₁ = WR_crit,1", value=True)
        wr1 = c4.number_input("WR₁ / -", 0.0, 40.0, 5.0, 0.5, disabled=auto)
        wr2 = c5.number_input("WR₂ / -", 0.0, 40.0, 4.5, 0.5)
        go_w = st.form_submit_button("Run washing model", type="primary", icon=":material/play_arrow:")
    if not K["finished"]:
        st.session_state.wash_err = ("cake formation is not completed on the filter medium of the filtration module "
                                     "(z_S1 > L_f), i.e. no deliquored filter cake enters the washing modules. Adjust "
                                     "the operating point first (see the design hints in the tab Process design).")
    elif go_w or "wash" not in st.session_state:
        with st.spinner("Solving the ADE of both washing steps …"):
            try:
                st.session_state.wash = E.run_washing(R, dp_wash=dpw, Psi1=psi1, WR1=None if auto else wr1, WR2=wr2,
                                                      X_star=xs)
                st.session_state.wash_err = None
            except Exception as ex:                       # noqa: BLE001
                st.session_state.wash_err = str(ex)
    if st.session_state.get("wash_err"):
        st.warning(f"Washing model not evaluated: {st.session_state.wash_err}", icon="⚠️")
    else:
        W = st.session_state.wash
        c = st.columns(5)
        kpi(c[0], "Critical wash ratio WR_crit,1", fmt(W["WR_crit1"]) if np.isfinite(W["WR_crit1"]) else "> 40",
            f"for X* ≤ {100 * W['target']:.3g} %", "ok" if np.isfinite(W["WR_crit1"]) else "bad")
        kpi(c[1], "Washing liquid flow step 1", f"{fmt(W['Q_WL1'])} mL/min", f"WR₁ = {fmt(W['WR1'])}")
        kpi(c[2], "Washing liquid flow step 2", f"{fmt(W['Q_WL2'])} mL/min", f"WR₂ = {fmt(W['WR2'])}")
        kpi(c[3], "X* after step 1 / step 2", f"{100 * W['X1_end']:.3g} / {100 * W['X2_end']:.3g} %",
            "relative impurity loading")
        kpi(c[4], "Pore volume flow Q_pore", f"{fmt(W['Q_pore'], 3)} mL/min", f"f₁ = {W['f1']:.3f} · γ = {W['gamma']:.2f}")
        fw = go.Figure()
        FLOOR = 1e-7                                       # below: numerical resolution of the ADE solver
        y1 = np.clip(W["X1"], FLOOR, None); y2 = np.clip(W["X2"], FLOOR, None)
        fw.add_trace(go.Scatter(x=W["W"], y=y1, name="washing step 1 (X* over WR₁)", mode="lines",
                                line=dict(color=BLUE, width=3)))
        fw.add_trace(go.Scatter(x=W["W"], y=y2, name=f"washing step 2 after WR₁ = {W['WR1']:.2f} (X* over WR₂)",
                                mode="lines", line=dict(color=C_BP, width=3, dash="dash")))
        fw.add_trace(go.Scatter(x=[0, W["W"][-1]], y=[W["target"]] * 2, mode="lines", name=f"target X* = "
                                f"{100 * W['target']:.3g} %", line=dict(color=RED, dash="dot", width=1.5)))
        if np.isfinite(W["WR_crit1"]):
            fw.add_trace(go.Scatter(x=[W["WR_crit1"]] * 2, y=[FLOOR, 1], mode="lines", name="WR_crit,1",
                                    line=dict(color=BLUE, dash="dot", width=1.5)))
        fw.add_trace(go.Scatter(x=[W["WR2"]], y=[max(W["X2_end"], FLOOR)], mode="markers", name="end of step 2",
                                marker=dict(color=C_BP, size=11, symbol="diamond", line=dict(color=DARK, width=1))))
        fw.update_yaxes(type="log", title_text="X* / -", exponentformat="power", range=[-7, 0.1])
        fw.update_xaxes(title_text="Wash ratio WR / -")
        fw.update_layout(template="simple_white", height=480, legend=dict(orientation="h", y=-0.2),
                         title="Wash curves (relative impurity loading)")
        l, r = st.columns([2, 1.2])
        l.plotly_chart(fw, width="stretch")
        # apparatus overview
        ap = go.Figure()
        segs = [("Dead", 1, "#FFFFFF"), ("F1", 6, "#D9D9D9"), ("T1", 8, "#FFFFFF"), ("W1", 6, "#CFE8FA"),
                ("T2", 8, "#FFFFFF"), ("W2", 6, "#FBE5B6"), ("T3", 8, "#FFFFFF")]
        x0 = -1.0
        for nm, L, colr in segs:
            ap.add_shape(type="rect", x0=x0, x1=x0 + L, y0=0, y1=1, fillcolor=colr, line=dict(color=DARK, width=1))
            if L > 2:
                ap.add_annotation(x=x0 + L / 2, y=0.5, text=nm, showarrow=False, font=dict(size=13))
            x0 += L
        ap.add_annotation(x=0, y=1.0, ax=12, ay=-35, text="suspension", arrowhead=2, xanchor="left")
        ap.add_annotation(x=14 + 3, y=1.0, ax=0, ay=-35, text="EtOH/water", arrowhead=2)
        ap.add_annotation(x=28, y=1.0, ax=0, ay=-35, text="ethanol", arrowhead=2)
        ap.add_shape(type="line", x0=K["z_S1"] if K["z_S1"] < 6 else 6, x1=K["z_S1"] if K["z_S1"] < 6 else 6, y0=-0.1,
                     y1=1.1, line=dict(color=BLUE, width=3))
        ap.add_annotation(x=min(K["z_S1"], 6), y=-0.25, text="z_S1", showarrow=False, font=dict(color=BLUE))
        ap.update_xaxes(title_text="z / cm (from start of filter medium F1)", range=[-1.5, 43])
        ap.update_yaxes(visible=False, range=[-0.5, 1.6])
        ap.update_layout(template="simple_white", height=230, margin=dict(t=30, b=40), title="CVSF configuration FWW")
        r.plotly_chart(ap, width="stretch")
        r.caption("Values below X* = 10⁻⁷ are not resolved by the numerical solution and are not shown. "
                  "Current CVSF: frits of 6 cm, transport zones of 8 cm. Dosing in washing module 1 in the centre of "
                  "the frit (remaining filter length 3 cm), in washing module 2 at the beginning of the frit.")
        st.info("The correlations for the stagnant pore volume fraction and the mass transfer coefficient are based "
                "on eight wash curves of bipyramidal particles and are not significantly predictive (Q² ≈ 0); "
                "results for other particle shapes, PSD widths, or temperatures are extrapolations.", icon="ℹ️")

# ------------------------------------------------------------------------------------------------------------
# tab 2: 3D apparatus (three.js)
# ------------------------------------------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _wash_default(inp_json):
    r = E.run_filtration(E.Inputs.from_json(inp_json))
    return E.run_washing(r)


with tabs[1]:
    c1, c2, c3 = st.columns([1.4, 1.1, 2.5])
    cfg = c1.segmented_control("Module configuration", list(A3.CONFIGS), default="F-W-W-D", key="cfg3d",
                               help="F: filtration/deliquoring module (feed), W: washing module, D: deliquoring module; "
                                    "the end piece with the discharge follows the last module.")
    wash_on = c2.toggle("Show washing", value=True, key="wash3d",
                        help="Colours of the pore liquid from the washing model (tab Washing). Without a calculation "
                             "there, the default washing parameters are used.")
    c3.caption("Geometry from the CAD model of the CVSF (Fusion 360), scaled to the design inputs of the sidebar "
               "(L_f, L_T, D_i, screw). Screw speed, particle velocity v_p,ax = P·n/θm, z_S1, h_c(z) and the wash "
               "curves X*(WR) are taken from the model. Drag to rotate, scroll to zoom, right-drag to pan.")
    W3 = None
    if wash_on and K["finished"] and cfg and "W" in cfg:
        if "wash" in st.session_state and not st.session_state.get("wash_err"):
            W3 = st.session_state.wash
        else:
            try:
                with st.spinner("Solving the washing model for the 3D view …"):
                    W3 = _wash_default(inp.to_json())
            except Exception as ex:                       # noqa: BLE001
                st.warning(f"Washing model not evaluated: {ex}", icon="⚠️")
    data3 = A3.scene_data(R, W3, cfg or "F-W-W-D", wash_on)
    _h3 = A3.html(data3, height=720)
    if hasattr(st, "iframe"):
        st.iframe(_h3, height=726)
    else:                                                  # older Streamlit versions
        components.html(_h3, height=726, scrolling=False)

# ------------------------------------------------------------------------------------------------------------
# tab 5: export
# ------------------------------------------------------------------------------------------------------------
with tabs[5]:
    prof = pd.DataFrame(dict(z_cm=res["z"], phi_RM=res["phi"], phi_RM_evap=res["phi_evap"]))
    kp = {k: (float(v) if isinstance(v, (int, float, np.floating, np.integer, bool)) and v is not None else v)
          for k, v in K.items()}
    out = dict(inputs=json.loads(inp.to_json()), results=kp, warnings=R["warnings"])
    if "wash" in st.session_state and not st.session_state.get("wash_err"):
        W = st.session_state.wash
        out["washing"] = {k: float(W[k]) for k in ["WR_crit1", "WR1", "WR2", "X1_end", "X2_end", "Q_WL1", "Q_WL2",
                                                     "Q_pore", "f1", "f2", "ka1", "ka2", "gamma", "b_D"]}
    c1, c2, c3 = st.columns(3)
    c1.download_button("Results (JSON)", json.dumps(out, indent=1, default=float), "cvsf_results.json",
                       "application/json", width="stretch")
    c2.download_button("Residual moisture profile (CSV)", prof.to_csv(index=False), "cvsf_profile.csv", "text/csv",
                       width="stretch")
    c3.download_button("Inputs (JSON)", inp.to_json(), "cvsf_inputs.json", "application/json", width="stretch")
    st.dataframe(pd.DataFrame([(k, v) for k, v in out["results"].items() if k != "mu_star_hint"],
                              columns=["key", "value"]), hide_index=True, width="stretch")

# ------------------------------------------------------------------------------------------------------------
# tab 6: model description
# ------------------------------------------------------------------------------------------------------------
with tabs[6]:
    TP.render(R, R["inp"], ACTIVE, kpi)

with tabs[7]:
    with st.container(border=True):
        st.markdown("#### Model version")
        mv1, mv2, mv3 = st.columns([1.2, 1, 1])
        mv1.markdown(f"Model code **CVSF_Model {_MV['tag'] or '(no released tag)'}** · commit `{_MV['commit']}`  \n"
                     "Embedded as git submodule `cvsf_model/`; new released model versions are taken over on GitHub "
                     "after the self test has passed.")
        if mv2.button("Check for updates", icon=":material/sync:"):
            try:
                st.session_state.newest_model = MU.newest()
            except Exception as ex:                    # noqa: BLE001
                st.session_state.newest_model = f"not available ({ex})"
        if st.session_state.get("newest_model"):
            mv2.caption(f"Newest released model version: {st.session_state.newest_model}")
        if mv3.button("Update software and model", icon=":material/download:",
                      help="git pull of the tested state from GitHub; restart the application afterwards"):
            try:
                after = MU.update_software()
                mv3.success(f"Updated (model {after['tag'] or after['commit']}). Please restart the application.")
            except Exception as ex:                    # noqa: BLE001
                mv3.error(f"Update not possible: {ex}")
    st.markdown(f"""
#### Model structure
1. **Filter cake properties** from PSD, particle shape and agglomeration degree: porosity (modified linear packing
   model, Yu et al.), specific filter cake resistance (additive Carman-Kozeny approach, Bourcier et al.), sphericity
   corrected by the agglomeration degree, ψ_eff = ψ · (1 − Ag3/A) with **A = {E.cvsf.A_FIT}** (Fit F1).
2. **Particle transport**: belt filter analogy with the axial particle velocity v_p,ax = P · n_screw / θm; θm from the
   extended vortex efficiency (Roberts), **μs = {E.cvsf.MU_S:.4f}, a = {E.cvsf.A_RTD:.4f}, b = {E.cvsf.B_RTD:.4f}**
   (Fit 1, 13 RTD measurements, R² = 0.954, Q² = 0.93). Filling degree acc. to DIN 15261.
3. **Cake filtration** at constant Δp until the liquid saturation degree S = 1 is reached at **z_S1**.
4. **Gas deliquoring** on the remaining filter medium (Wakeman and Tarleton), S∞,fit = B · S∞ with **B = 2.25**
   (Fit F2).
5. **Evaporation** in the transport zone (convective mass transfer, Gnielinski).
6. **Two-stage washing**: two-compartment advection-dispersion equation (flowing and stagnant pore volume),
   γ = 8.96 (Fit W1), correlations for the stagnant fraction and mass transfer (Fit W3).

#### Validity
Parameters fitted for l-alanine/water (bipyramidal, cuboid, needle-shaped particles) and ethanol/water washing liquids.
Sensitivity analysis ranges: d50,3 20–100 µm, σg 0.3–0.9, ψ 0.3–0.9, ϑ 10–50 °C, Δp 40–200 mbar, Q_susp 20–100
mL/min, n_screw 1–5 rpm, w_solid 2–10 wt.-%. Validation data: OP 1 (60 mL/min, 3 rpm, 80 mbar). Axial profiles are
model predictions (no spatially resolved sampling possible).

#### References
- M.P. Meier, M. Vogel, L. Ohm, Mechanistic Modeling of Filtration and Deliquoring within the Continuous Vacuum Screw
  Filter (filtration study).
- M.P. Meier, L. Ohm, Mechanistic Modeling of Two-Stage Washing within the Continuous Vacuum Screw Filter (washing
  study).
- M.P. Meier, M. Vogel, L. Ohm, CVSF_Model_Filtration_Deliquoring_Washing_V01, TUDOdata (2026).
- M. Vogel, master thesis, TU Dortmund University (2024); L. Ohm, master thesis, TU Dortmund University (2026).
""")

_footer()
