"""Bayesian calibration of the CVSF model parameters with experimental data of completed CVSF runs.

Interface-independent layer used by the GUI (gui/app.py, mode "Calibration") and usable from Python scripts.

Calibrated parameters and data (sequential calibration, same structure as the fits of the filtration study):
  stage 1  mu_s, a, b  (residence time correlation, Fit 1)    <- dimensionless mean solids residence times theta_m (RTD)
  stage 2  A           (sphericity correction, Fit F1)        <- filter cake porosity and/or specific cake resistance
  stage 3  B           (equilibrium saturation factor, Fit F2) <- residual moisture at the outlet of the filtration module

Prior: the active parameter set (e.g. the reference set of the filtration study) with its uncertainty; for a new
material system, the prior width is increased. Likelihood: Gaussian with the stated measurement/model uncertainty
(relative for theta_m and porosity, logarithmic for alpha_FC, absolute for the residual moisture). Posterior:
stage 1 by Markov chain Monte Carlo (adaptive Metropolis), stages 2 and 3 on a fine parameter grid; in stage 3 the
residual moisture of each experiment is evaluated on a B grid and interpolated (emulator), because one evaluation
of the filtration module takes approx. 0.5 s. Later stages use the posterior means of earlier stages (plug-in).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re

import numpy as np
import pandas as pd
from scipy import optimize as so
from scipy.interpolate import CubicSpline

import engine as E

cvsf = E.cvsf
PARAMS = ["mu_s", "a_rtd", "b_rtd", "A", "B"]
LABEL = {"mu_s": "μs (friction, θm correlation)", "a_rtd": "a (rotational speed exponent, θm correlation)",
         "b_rtd": "b (number of flights exponent, θm correlation)", "A": "A (sphericity correction, Fit F1)",
         "B": "B (equilibrium saturation factor, Fit F2)"}
SHORT = {"mu_s": "μs", "a_rtd": "a", "b_rtd": "b", "A": "A", "B": "B"}

# ---------------------------------------------------------------------------------------------------------------
# parameter sets
# ---------------------------------------------------------------------------------------------------------------
DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share"),
                        "CVSF_Process_Simulator")
CONFIG = os.path.join(DATA_DIR, "config.json")


def storage_root():
    """folder of the experiment database and the parameter sets (configurable, e.g. a shared network folder)"""
    try:
        r = json.load(open(CONFIG)).get("storage_root")
        if r:
            return r
    except (OSError, ValueError):
        pass
    return DATA_DIR


def set_storage_root(path):
    path = os.path.abspath(os.path.expanduser(path))
    os.makedirs(path, exist_ok=True)
    test = os.path.join(path, ".write_test")
    with open(test, "w") as f:
        f.write("ok")
    os.remove(test)
    os.makedirs(DATA_DIR, exist_ok=True)
    cfg = {}
    if os.path.exists(CONFIG):
        try:
            cfg = json.load(open(CONFIG))
        except ValueError:
            cfg = {}
    cfg["storage_root"] = path
    json.dump(cfg, open(CONFIG, "w"), indent=1)
    return path


def get_pref(key, default=None):
    """user preference from config.json (e.g. dark mode)"""
    try:
        return json.load(open(CONFIG)).get("prefs", {}).get(key, default)
    except (OSError, ValueError):
        return default


def set_pref(key, value):
    os.makedirs(DATA_DIR, exist_ok=True)
    cfg = {}
    if os.path.exists(CONFIG):
        try:
            cfg = json.load(open(CONFIG))
        except ValueError:
            cfg = {}
    cfg.setdefault("prefs", {})[key] = value
    json.dump(cfg, open(CONFIG, "w"), indent=1)


def set_dir():
    return os.path.join(storage_root(), "parameter_sets")
REF_JSON = os.path.join(E.ROOT, "gui", "data", "calibration_reference.json")

REFERENCE_NAME = "L-alanine / water – reference (filtration study)"


def reference_set():
    """built-in, read-only parameter set of the filtration study; uncertainties from gui/data/calibration_reference.json"""
    s = dict(name=REFERENCE_NAME, readonly=True, material=dict(name="L-alanine / water", rhos=1420.0, sigma=72.25e-3),
             params=dict(mu_s=cvsf.MU_S, a_rtd=cvsf.A_RTD, b_rtd=cvsf.B_RTD, A=cvsf.A_FIT, B=2.25),
             std=dict(mu_s=0.02, a_rtd=0.02, b_rtd=0.03, A=0.3, B=0.15), noise=dict(), created="2026-11-22",
             description="Parameters of the filtration study (Fit 1: 13 RTD measurements; Fit F1: 8 filter cakes; "
                         "Fit F2: 12 residual moistures at OP 1).")
    if os.path.exists(REF_JSON):
        r = json.load(open(REF_JSON))
        s["std"].update(r.get("std", {}))
        s["noise"] = r.get("noise", {})
        if "corr_theta" in r:
            s["corr_theta"] = r["corr_theta"]
    return s


def _slug(name):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")[:80] or "parameter_set"


def list_sets():
    sets = {REFERENCE_NAME: reference_set()}
    SD = set_dir()
    if os.path.isdir(SD):
        for f in sorted(os.listdir(SD)):
            if f.endswith(".json"):
                try:
                    s = json.load(open(os.path.join(SD, f)))
                    sets[s["name"]] = s
                except (OSError, ValueError, KeyError):
                    pass
    return sets


def save_set(s):
    if s.get("name") == REFERENCE_NAME:
        raise ValueError("The reference parameter set cannot be overwritten; please choose another name.")
    os.makedirs(set_dir(), exist_ok=True)
    s = dict(s, readonly=False)
    p = os.path.join(set_dir(), _slug(s["name"]) + ".json")
    with open(p, "w") as f:
        json.dump(s, f, indent=1, default=float)
    return p


def delete_set(name):
    p = os.path.join(set_dir(), _slug(name) + ".json")
    if os.path.exists(p):
        os.remove(p)


def apply_set(inp: E.Inputs, s):
    for k, v in s["params"].items():
        setattr(inp, k, float(v))
    m = s.get("material", {})
    if "rhos" in m:
        inp.rhos = float(m["rhos"])
    if "sigma" in m:
        inp.sigma = float(m["sigma"])
    return inp


# ---------------------------------------------------------------------------------------------------------------
# experimental data (template)
# ---------------------------------------------------------------------------------------------------------------
COLUMNS = [  # name, unit / allowed values, description
    ("ID", "text", "Identifier of the experiment / measurement"),
    ("include", "1 / 0", "1 = use for the calibration, 0 = ignore"),
    ("shape", "bipyramidal / cuboid / needle", "Particle shape"),
    ("psd_results", "file name or path", "PSDResults_*.xlsx of the dynamic image analysis (PSD, agglomeration degree)"),
    ("psd_descriptors", "file name or path", "ImageDescriptors_*.xlsx (cuboid and needle-shaped particles only)"),
    ("d10_um", "µm", "alternative to the PSD file: characteristic diameters (log-normal PSD)"),
    ("d50_um", "µm", "alternative to the PSD file"),
    ("d90_um", "µm", "alternative to the PSD file"),
    ("psi_eff", "-", "effective sphericity (only without PSD file; empty = preset of the particle shape)"),
    ("Ag3", "-", "agglomeration degree (only without PSD file; required to inform A)"),
    ("setup", "current / previous", "module generation: current (frit 6 cm) or previous (frit 4.5 cm)"),
    ("screw", "a / b / c", "screw design (a) one flight 12 mm, (b) one flight 23 mm, (c) two flights 24 mm"),
    ("Q_mL_min", "mL/min", "suspension volume flow rate"),
    ("w_solid_pct", "wt.-%", "solid mass fraction of the suspension"),
    ("n_rpm", "rpm", "rotational screw speed"),
    ("dp_mbar", "mbar", "pressure difference of the filtration module"),
    ("T_C", "°C", "suspension temperature"),
    ("theta_m_meas", "-", "measured dimensionless mean solids residence time (RTD) -> stage 1 (μs, a, b)"),
    ("eps_meas_pct", "%", "measured filter cake porosity -> stage 2 (A)"),
    ("alpha_FC_meas", "m/kg", "measured specific filter cake resistance -> stage 2 (A)"),
    ("phi_RM_meas_pct", "%", "measured residual moisture at the outlet of the filtration module -> stage 3 (B)"),
    ("note", "text", "free text"),
]
COLS = [c[0] for c in COLUMNS]


def empty_table(n=3):
    df = pd.DataFrame({c: pd.Series(dtype="object") for c in COLS})
    if n == 0:
        return _types(df)
    for i in range(n):
        df.loc[i] = [f"E{i + 1}", 1, "bipyramidal", "", "", None, None, None, None, None, "current", "a", 60.0, 6.0,
                     3.0, 80.0, 21.0, None, None, None, None, ""]
    return _types(df)


def _types(df):
    df = df.reindex(columns=COLS)
    num = ["include", "d10_um", "d50_um", "d90_um", "psi_eff", "Ag3", "Q_mL_min", "w_solid_pct", "n_rpm", "dp_mbar",
           "T_C", "theta_m_meas", "eps_meas_pct", "alpha_FC_meas", "phi_RM_meas_pct"]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["ID", "shape", "psd_results", "psd_descriptors", "setup", "screw", "note"]:
        df[c] = df[c].astype("object").where(df[c].notna(), "").astype(str)
    df["include"] = df["include"].fillna(1).astype(int)
    return df.reset_index(drop=True)


def reference_dataset():
    """experimental data of the filtration study in the template format (33 rows)"""
    import props as PR
    import Benchmark_data_2 as BD
    rows = []
    smap = {"ES": "a", "MS": "b", "AMS": "c"}
    for i, d in enumerate(BD.DATA_POINTS):
        rows.append(dict(ID=f"RTD-{i + 1:02d} {d.screw_type} {d.configuration} {d.particle_size}", include=1,
                         shape="bipyramidal", setup="current", screw=smap[d.screw_type], Q_mL_min=d.volume_flow,
                         n_rpm=d.screw_speed, theta_m_meas=d.theta_m,
                         note="RTD measurement (Fit 1)"))
    for lab, f, r, dsc, e, a in PR.A_EXP:
        rows.append(dict(ID="Cake " + lab, include=1, shape=f, psd_results=os.path.join(cvsf.MODEL_DIR, r),
                         psd_descriptors=os.path.join(cvsf.MODEL_DIR, dsc) if dsc else "", eps_meas_pct=100 * e,
                         alpha_FC_meas=a, note="filter cake (Fit F1)"))
    for lab, f, r, dsc, phi in PR.B_EXP:
        rows.append(dict(ID="OP1 " + lab, include=1, shape=f, psd_results=os.path.join(cvsf.MODEL_DIR, r),
                         psd_descriptors=os.path.join(cvsf.MODEL_DIR, dsc) if dsc else "", setup="previous",
                         screw="a", Q_mL_min=60.0, w_solid_pct=6.0, n_rpm=3.0, dp_mbar=80.0, T_C=21.0,
                         phi_RM_meas_pct=100 * phi, note="residual moisture at OP 1 (Fit F2)"))
    return _types(pd.DataFrame(rows))


def read_table(file):
    xl = pd.ExcelFile(file)
    sh = "Experiments" if "Experiments" in xl.sheet_names else xl.sheet_names[0]
    df = pd.read_excel(xl, sheet_name=sh)
    df = df[[c for c in df.columns if c in COLS]]
    df = df.dropna(how="all")
    if len(df) and str(df.iloc[0].get("ID", "")).strip().lower() == "text":   # unit row of the template
        df = df.iloc[1:]
    if "ID" in df:
        df = df[~df["ID"].astype(str).str.upper().str.startswith("EXAMPLE")]
    df = df.dropna(how="all")
    mat = None
    if "Material system" in xl.sheet_names:
        m = pd.read_excel(xl, sheet_name="Material system", header=None).dropna(how="all")
        mm = {str(k).strip(): v for k, v in zip(m.iloc[:, 0], m.iloc[:, 1])}
        mat = dict(name=str(mm.get("name", "new material system")),
                   rhos=float(mm.get("rho_solid_kg_m3", 1420.0)),
                   sigma=float(mm.get("sigma_liquid_mN_m", 72.25)) / 1e3)
    return _types(df), mat


REQUIRED = {  # measured quantity -> required columns
    "theta_m_meas": ["screw", "n_rpm"],
    "eps_meas_pct / alpha_FC_meas": ["shape", "psd_results (+ psd_descriptors for cuboid/needle) or d10/d50/d90 + Ag3"],
    "phi_RM_meas_pct": ["shape", "psd_results (+ psd_descriptors) or d10/d50/d90", "setup", "screw", "Q_mL_min",
                        "w_solid_pct", "n_rpm", "dp_mbar", "T_C"],
}


def example_rows():
    """three example rows with values of the filtration study (one per measured quantity)"""
    return _types(pd.DataFrame([
        dict(ID="EXAMPLE-1 RTD", include=1, shape="bipyramidal", setup="current", screw="a", Q_mL_min=20.0, n_rpm=1.0,
             theta_m_meas=1.33, note="residence time measurement: only screw and n_rpm needed"),
        dict(ID="EXAMPLE-2 cake", include=1, shape="bipyramidal", psd_results="PSDResults_Videos_BP355560_1.xlsx",
             eps_meas_pct=39.07, alpha_FC_meas=2.18e6, note="filter cake test: PSD file + porosity and/or alpha_FC"),
        dict(ID="EXAMPLE-3 moisture", include=1, shape="bipyramidal", psd_results="PSDResults_Videos_BP355560_1.xlsx",
             setup="previous", screw="a", Q_mL_min=60.0, w_solid_pct=6.0, n_rpm=3.0, dp_mbar=80.0, T_C=21.0,
             phi_RM_meas_pct=21.0, note="CVSF run: PSD + complete operating point + residual moisture"),
    ]))


def write_template(path, df=None, material=None):
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.worksheet.datavalidation import DataValidation
    df = empty_table(0) if df is None else df
    material = material or dict(name="L-alanine / water", rhos=1420.0, sigma=72.25e-3)
    wb = Workbook()
    hdr = PatternFill("solid", fgColor="16395F")
    sub = PatternFill("solid", fgColor="DCE6F1")
    groups = {"ID": "D9D9D9", "shape": "FCE4C4", "setup": "E2EFDA", "theta_m_meas": "FFF2CC", "note": "D9D9D9"}
    gfill = {}
    cur = "D9D9D9"
    for c, _, _ in COLUMNS:
        cur = groups.get(c, cur)
        gfill[c] = PatternFill("solid", fgColor=cur)
    thin = Side(style="thin", color="B7C3D0")

    def sheet(ws, data, example=False):
        for j, (c, u, d) in enumerate(COLUMNS, start=1):
            h = ws.cell(1, j, c)
            h.font = Font(bold=True, color="FFFFFF")
            h.fill = hdr
            h.alignment = Alignment(horizontal="center")
            h.comment = Comment(f"{c} [{u}]\n{d}", "CVSF Process Simulator", width=320, height=110)
            uc = ws.cell(2, j, u)
            uc.fill = sub
            uc.font = Font(italic=True, size=9)
            uc.alignment = Alignment(horizontal="center")
            ws.column_dimensions[h.column_letter].width = max(11, min(36, len(c) + 4))
        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["C"].width = 26
        ws.column_dimensions["K"].width = 18
        ws.column_dimensions["D"].width = 36
        ws.column_dimensions["E"].width = 30
        ws.column_dimensions["V"].width = 48
        for i, row in enumerate(data.itertuples(index=False), start=3):
            for j, v in enumerate(row, start=1):
                cell = ws.cell(i, j)
                if v is not None and not (isinstance(v, float) and np.isnan(v)) and v != "":
                    cell.value = v
                cell.fill = gfill[COLS[j - 1]] if example else PatternFill()
                cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
                if COLS[j - 1] == "alpha_FC_meas":
                    cell.number_format = "0.00E+00"
        ws.freeze_panes = "B3"
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True

    ws = wb.active
    ws.title = "Experiments"
    sheet(ws, df)
    for col, vals in [("C", "bipyramidal,cuboid,needle"), ("K", "current,previous"), ("L", "a,b,c"), ("B", "1,0")]:
        dv = DataValidation(type="list", formula1=f'"{vals}"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"{col}3:{col}1000")
    ex = wb.create_sheet("Example")
    sheet(ex, example_rows(), example=True)
    ex.cell(7, 1, "Example rows with values of the filtration study (colors: identification / particle system / "
                  "operating point / measured quantities). Rows whose ID starts with EXAMPLE are ignored on upload; "
                  "do not copy them into the sheet Experiments (they are already part of the reference model).").font = \
        Font(italic=True, color="C00000")
    m = wb.create_sheet("Material system")
    for i, (k, v, d) in enumerate([("name", material["name"], "name of the material system (solid / liquid); "
                                                              "datasets with the same name are calibrated together"),
                                   ("rho_solid_kg_m3", material["rhos"], "solid density in kg/m3"),
                                   ("sigma_liquid_mN_m", 1e3 * material["sigma"], "surface tension of the liquid in mN/m")],
                                  start=1):
        m.cell(i, 1, k).font = Font(bold=True)
        m.cell(i, 2, v).fill = PatternFill("solid", fgColor="FFF2CC")
        m.cell(i, 3, d)
    m.cell(5, 1, "Note: density and viscosity of the liquid are those of the L-alanine/water mother liquor (model V01).")
    m.column_dimensions["A"].width = 22
    m.column_dimensions["B"].width = 22
    m.column_dimensions["C"].width = 80
    h = wb.create_sheet("Instructions")
    txt = ["CVSF Process Simulator – experimental data for the Bayesian calibration", "",
           "Step 1  Sheet 'Material system': name of the material system, solid density, surface tension.",
           "Step 2  Sheet 'Experiments': one row per experiment or measurement, starting in row 3 (row 2 = units).",
           "        Several measured quantities may be given in the same row (e.g. residual moisture and theta_m of the "
           "same run).",
           "Step 3  Fill the columns required for the measured quantity (table below); leave all other cells empty.",
           "Step 4  PSD files: enter the file name (e.g. PSDResults_Videos_Run12.xlsx) and upload the files together "
           "with this template, or enter the full path.",
           "Step 5  Save, upload in the CVSF Process Simulator (mode Calibration, tab 'Add data'), check the status "
           "of every row, and add the dataset to the experiment database.",
           "", "Required columns per measured quantity:"]
    for q, cols in REQUIRED.items():
        txt.append(f"  {q:32s} -> " + ", ".join(cols))
    txt += ["", "Definitions:",
            "  theta_m_meas    = tau_m / tau_hy: mean solids residence time from the RTD divided by the residence time of "
            "ideal screw conveying tau_hy = L / (P * n_screw) over the same conveying length L",
            "  eps_meas_pct    = filter cake porosity (void volume / cake volume) in %",
            "  alpha_FC_meas   = mass-related specific filter cake resistance in m/kg (e.g. pressure filtration test, "
            "VDI 2762)",
            "  phi_RM_meas_pct = residual moisture of the product at the outlet of the filtration module, wet basis: "
            "mass of liquid / (mass of liquid + mass of solid) in %",
            "  w_solid_pct     = solid mass fraction of the suspension in wt.-%; dp_mbar = pressure difference of the "
            "filtration module in mbar",
            "  setup           = current (frit 6 cm, transport zone 8 cm) or previous module generation (frit 4.5 cm)",
            "  screw           = a: one flight, P = 12 mm; b: one flight, P = 23 mm; c: two flights, P = 24 mm",
            "  include         = 1 (use) or 0 (store, but do not use); can be changed later in the experiment database",
            "", "Columns of the sheet Experiments:"] + [f"  {c} [{u}]: {d}" for c, u, d in COLUMNS]
    txt += ["", "A step-by-step guide with screenshots: docs/Guide_Experimental_Data_Template.pdf (download in the "
                "interface)."]
    for i, t in enumerate(txt, start=1):
        h.cell(i, 1, t).font = Font(name="Consolas", size=10)
    h.column_dimensions["A"].width = 150
    h["A1"].font = Font(bold=True, size=13)
    wb.move_sheet("Instructions", offset=-3)
    wb.active = 1
    wb.save(path)
    return path


def _resolve(name, uploads):
    if not name:
        return None
    if os.path.exists(name):
        return name
    rel = os.path.join(storage_root(), name)            # files of the experiment database (relative paths)
    if os.path.exists(rel):
        return rel
    b = os.path.basename(str(name).replace("\\", "/"))
    if b in uploads:
        return uploads[b]
    for root in (os.path.join(cvsf.MODEL_DIR, "PSDs", "Experiments"), os.path.join(cvsf.MODEL_DIR, "PSDs", "DataJH")):
        p = os.path.join(root, b)
        if os.path.exists(p):
            return p
    return None


def check_table(df, uploads=None):
    """per row: which quantities are usable and why not"""
    uploads = uploads or {}
    out = []
    for _, r in df.iterrows():
        use, issues = [], []
        if int(r["include"] or 0) != 1:
            out.append(dict(ID=r["ID"], usable="– (excluded)", issues="", plausibility=""))
            continue
        has_file = bool(r["psd_results"])
        psd_ok = False
        if has_file:
            if _resolve(r["psd_results"], uploads) is None:
                issues.append(f"PSD file '{os.path.basename(r['psd_results'])}' not found (upload it)")
            elif r["shape"] != "bipyramidal" and _resolve(r["psd_descriptors"], uploads) is None:
                issues.append("ImageDescriptors file missing")
            else:
                psd_ok = True
        elif pd.notna(r["d50_um"]) or (pd.notna(r["d10_um"]) and pd.notna(r["d90_um"])):
            psd_ok = True
        if pd.notna(r["theta_m_meas"]):
            if r["screw"] in ("a", "b", "c") and pd.notna(r["n_rpm"]):
                use.append("θm")
            else:
                issues.append("θm: screw and n_rpm required")
        if pd.notna(r["eps_meas_pct"]) or pd.notna(r["alpha_FC_meas"]):
            if psd_ok and (has_file or pd.notna(r["Ag3"])):
                use.append("ε/α_FC")
            else:
                issues.append("ε/α_FC: PSD file (or d-values + Ag3) required")
        if pd.notna(r["phi_RM_meas_pct"]):
            need = ["Q_mL_min", "w_solid_pct", "n_rpm", "dp_mbar", "T_C"]
            miss = [c for c in need if pd.isna(r[c])]
            if psd_ok and not miss and r["screw"] in ("a", "b", "c"):
                use.append("φ_RM")
            else:
                issues.append("φ_RM: " + ("PSD missing; " if not psd_ok else "") + ", ".join(miss))
        out.append(dict(ID=r["ID"], usable=", ".join(use) or "–", issues="; ".join(issues),
                        plausibility="; ".join(_plausibility(r))))
    return pd.DataFrame(out)


PLAUS = [  # column, min, max, hint
    ("theta_m_meas", 1.0, 3.0, "θm = τm/τhy is normally between 1 and 3"),
    ("eps_meas_pct", 15.0, 85.0, "porosity in % (e.g. 42.5, not 0.425)"),
    ("phi_RM_meas_pct", 2.0, 80.0, "residual moisture in % (e.g. 21, not 0.21)"),
    ("w_solid_pct", 0.5, 40.0, "solid mass fraction in wt.-% (e.g. 6, not 0.06)"),
    ("alpha_FC_meas", 1e8 / 1e3, 1e13, "cake resistance in m/kg (typically 1e8–1e12)"),
    ("dp_mbar", 5.0, 950.0, "pressure difference in mbar (not Pa)"),
    ("n_rpm", 0.1, 30.0, "rotational screw speed in rpm"),
    ("Q_mL_min", 1.0, 500.0, "suspension volume flow rate in mL/min"),
    ("T_C", 0.0, 90.0, "temperature in °C"),
]


def _plausibility(r):
    w = []
    for c, lo, hi, hint in PLAUS:
        v = r.get(c)
        if v is not None and pd.notna(v) and not (lo <= float(v) <= hi):
            w.append(f"{c} = {v:g}? ({hint})")
    return w


# ---------------------------------------------------------------------------------------------------------------
# model evaluation per row
# ---------------------------------------------------------------------------------------------------------------
def row_inputs(r, params, material, uploads):
    inp = E.Inputs()
    inp.shape = r["shape"] if r["shape"] in E.SHAPES else "bipyramidal"
    if r["psd_results"]:
        inp.psd_mode = "file"
        inp.psd_results = _resolve(r["psd_results"], uploads)
        inp.psd_descriptors = _resolve(r["psd_descriptors"], uploads)
    else:
        inp.psd_mode = "characteristic"
        inp.d10 = None if pd.isna(r["d10_um"]) else float(r["d10_um"])
        inp.d50 = None if pd.isna(r["d50_um"]) else float(r["d50_um"])
        inp.d90 = None if pd.isna(r["d90_um"]) else float(r["d90_um"])
        if pd.notna(r["Ag3"]):
            inp.psi_mode = "geometric"
            inp.Ag3 = float(r["Ag3"])
            inp.psi_geo = float(r["psi_eff"]) if pd.notna(r["psi_eff"]) else E.SHAPES[inp.shape]["psi_eff"]
        elif pd.notna(r["psi_eff"]):
            inp.psi_mode, inp.psi_eff = "effective", float(r["psi_eff"])
    setup = "steenweg" if str(r["setup"]).lower().startswith("prev") or r["setup"] == "steenweg" else "current"
    inp.setup = setup
    g = E.SETUPS[setup]
    inp.L_f, inp.L_T, inp.D_i = g["L_f"], g["L_T"], g["D_i"]
    sc = r["screw"] if r["screw"] in ("a", "b", "c") else "a"
    s = cvsf.SCREWS[sc]
    inp.screw, inp.d_i, inp.P, inp.N, inp.w = sc, s["d_i"], s["P"], int(s["N"]), s["w"]
    for col, att, f in [("Q_mL_min", "Q", 1), ("w_solid_pct", "ws", 0.01), ("n_rpm", "n", 1), ("dp_mbar", "dp", 1),
                        ("T_C", "T", 1)]:
        if pd.notna(r[col]):
            setattr(inp, att, float(r[col]) * f)
    inp.rhos, inp.sigma = material["rhos"], material["sigma"]
    for k, v in params.items():
        setattr(inp, k, float(v))
    return inp


class _Particles:
    """cached particle data of one row: cake properties as function of A"""

    def __init__(self, inp):
        self.inp = inp
        self.file = inp.psd_mode == "file"
        if self.file:
            res = inp.psd_results
            self.Ag = float(cvsf.agglomeration(res))
            if inp.shape == "bipyramidal":
                self.P = E._quiet(cvsf.psd_from_file, res, 200)
                self.psi0 = np.float64(E._quiet(E.Sphericity_Bipyramidal.sphericity, self.P).psi)
            else:
                self.P = E._quiet(E.PSDFit_OtherShape.PSDfit, inp.psd_descriptors, 200)
                self.psi0 = np.asarray(self.P[2], float)

    def props(self, A):
        if not self.file:
            self.inp.A = A
            p = E.prepare_particles(self.inp)
            return p["eps"], p["alpha_s"]
        psi = self.psi0 * (1 - self.Ag / A)
        if self.inp.shape == "bipyramidal":
            eps = cvsf.porosity_yu(self.P, psi)
            return float(eps), float(cvsf.cake_resistance(eps, self.P, self.inp.rhos, psi))
        eps = float(E._quiet(E.Porosity_OtherShape.porosity, self.P, psi, 200))
        return eps, float(E._quiet(E.CakeResistance_OtherShape.alpha, eps, self.P, self.inp.rhos, 200))


def _theta(rows, p):
    out = []
    for inp in rows:
        out.append(cvsf.theta_m(inp.d_i, 0.025, inp.P, inp.n, int(inp.N), p[0], p[1], p[2]))
    return np.array(out)


def _phi(inp, part, A, B, th):
    eps, a_s = part.props(A)
    inp.mu_s, inp.a_rtd, inp.b_rtd = th
    E._set_rtd(inp)
    r = E._quiet(cvsf.module, eps, a_s, op=E._op(inp), B=B, use_theta=True)
    return float(r["phi_evap_end"]) if r["finished"] else np.nan


# ---------------------------------------------------------------------------------------------------------------
# posterior computations
# ---------------------------------------------------------------------------------------------------------------
def _metropolis(logp, x0, cov, n=8000, burn=2000, seed=1):
    rng = np.random.default_rng(seed)
    d = len(x0)
    x, lp = np.array(x0, float), logp(x0)
    L = np.linalg.cholesky(cov * 2.38 ** 2 / d + 1e-14 * np.eye(d))
    chain, acc = [], 0
    for i in range(n):
        y = x + L @ rng.standard_normal(d)
        ly = logp(y)
        if np.log(rng.random()) < ly - lp:
            x, lp = y, ly
            acc += 1
        chain.append(x.copy())
        if i == burn // 2:                                     # one adaptation of the proposal after half burn-in
            c = np.cov(np.array(chain[burn // 4:]).T)
            if np.all(np.isfinite(c)) and np.linalg.det(c) > 0:
                L = np.linalg.cholesky(c * 2.38 ** 2 / d + 1e-14 * np.eye(d))
    return np.array(chain[burn:]), acc / n


def _grid_post(grid, loglik, mu0, sd0):
    lp = loglik + (-0.5 * ((grid - mu0) / sd0) ** 2)
    lp -= np.nanmax(lp)
    w = np.exp(np.nan_to_num(lp, nan=-np.inf))
    w /= np.trapezoid(w, grid)
    mean = np.trapezoid(grid * w, grid)
    sd = np.sqrt(np.trapezoid((grid - mean) ** 2 * w, grid))
    cdf = np.cumsum(w) * (grid[1] - grid[0])
    cdf /= cdf[-1]
    lo, hi = np.interp([0.025, 0.975], cdf, grid)
    return dict(grid=grid, pdf=w, mean=float(mean), sd=float(sd), lo=float(lo), hi=float(hi))


def _q2(y, yloo):
    y, yloo = np.asarray(y), np.asarray(yloo)
    m = np.isfinite(yloo)
    if m.sum() < 3:
        return np.nan
    sst = np.sum((y[m] - y[m].mean()) ** 2)
    return float(1 - np.sum((y[m] - yloo[m]) ** 2) / sst) if sst > 0 else np.nan


def calibrate(df, prior_set, *, free=("mu_s", "a_rtd", "b_rtd", "A", "B"), prior_scale=1.0, prior_override=None,
              noise=None, material=None, uploads=None, progress=None):
    """Bayesian calibration; returns a result dict (posterior summaries, data comparison, new parameter set)"""
    uploads = uploads or {}
    prog = progress or (lambda f, t: None)
    material = material or prior_set.get("material", dict(rhos=1420.0, sigma=72.25e-3))
    material = dict(name=material.get("name", "material system"), rhos=float(material["rhos"]),
                    sigma=float(material["sigma"]))
    nz = dict(theta_rel=0.05, eps_rel=0.05, alpha_log=0.6, phi_abs=0.02)
    nz.update(prior_set.get("noise", {}))
    nz.update(noise or {})
    mu0 = {k: float(prior_set["params"][k]) for k in PARAMS}
    sd0 = {k: float(prior_set["std"][k]) * prior_scale for k in PARAMS}
    for k, v in (prior_override or {}).items():
        mu0[k], sd0[k] = float(v[0]), float(v[1])
    chk = check_table(df, uploads)
    used = df[df["include"] == 1].reset_index(drop=True)
    chk = chk[[True if c != "– (excluded)" else False for c in chk["usable"]]].reset_index(drop=True)
    res = dict(prior=dict(mean=mu0, sd=sd0), noise=nz, material=material, free=list(free), stages={}, warnings=[])
    post = dict(mu0)
    post_sd = dict(sd0)

    # ---------------- stage 1: theta_m
    r1 = [i for i in range(len(used)) if "θm" in chk.loc[i, "usable"]]
    th_free = [k for k in ("mu_s", "a_rtd", "b_rtd") if k in free]
    st1 = dict(n=len(r1), params=th_free)
    if r1 and th_free:
        prog(0.02, f"Stage 1: residence time correlation ({len(r1)} RTD values)")
        rows = [row_inputs(used.loc[i], mu0, material, uploads) for i in r1]
        y = used.loc[r1, "theta_m_meas"].to_numpy(float)
        idx = [PARAMS.index(k) for k in th_free]

        def full(x):
            p = np.array([mu0["mu_s"], mu0["a_rtd"], mu0["b_rtd"]])
            p[idx] = x
            return p

        m0 = np.array([mu0[k] for k in th_free])
        s0 = np.array([sd0[k] for k in th_free])

        def resid(x, keep=None):
            kk = range(len(rows)) if keep is None else keep
            pr = _theta([rows[j] for j in kk], full(x))
            return np.r_[(pr - y[list(kk)]) / (nz["theta_rel"] * y[list(kk)]), (x - m0) / s0]

        def logp(x):
            r = resid(x)
            return -0.5 * np.sum(r ** 2) if np.all(np.isfinite(r)) else -np.inf

        ls = so.least_squares(resid, m0)
        J = ls.jac
        cov = np.linalg.pinv(J.T @ J)
        chain, acc = _metropolis(logp, ls.x, cov)
        m, s = chain.mean(0), chain.std(0)
        for j, k in enumerate(th_free):
            post[k], post_sd[k] = float(m[j]), float(s[j])
            st1[k] = dict(mean=float(m[j]), sd=float(s[j]), lo=float(np.percentile(chain[:, j], 2.5)),
                          hi=float(np.percentile(chain[:, j], 97.5)), samples=chain[::10, j])
        st1["corr"] = np.corrcoef(chain.T).tolist() if len(th_free) > 1 else [[1.0]]
        st1["accept"] = acc
        pred0, pred1 = _theta(rows, full(m0)), _theta(rows, full(m))
        loo = []
        for j in range(len(rows)):
            keep = [k for k in range(len(rows)) if k != j]
            lj = so.least_squares(lambda x: resid(x, keep), ls.x)
            loo.append(_theta([rows[j]], full(lj.x))[0])
        st1.update(ID=list(used.loc[r1, "ID"]), y=y, pred_prior=pred0, pred_post=pred1, pred_loo=np.array(loo),
                   rmse_prior=float(np.sqrt(np.mean((pred0 - y) ** 2))),
                   rmse_post=float(np.sqrt(np.mean((pred1 - y) ** 2))), q2=_q2(y, loo))
    res["stages"]["theta"] = st1

    # ---------------- stage 2: A
    r2 = [i for i in range(len(used)) if "ε/α_FC" in chk.loc[i, "usable"]]
    st2 = dict(n=len(r2), params=["A"] if "A" in free else [])
    parts = {}
    if r2 and "A" in free:
        prog(0.10, f"Stage 2: sphericity correction A ({len(r2)} filter cakes)")
        for i in r2:
            parts[i] = _Particles(row_inputs(used.loc[i], post, material, uploads))
        Agmax = max([p.Ag for p in parts.values() if p.file] + [float(used.loc[i, "Ag3"]) for i in r2
                                                                    if not parts[i].file] + [0.0])
        grid = np.linspace(max(1.05 * Agmax, 0.5), 12.0, 161)
        E_ = {i: used.loc[i, "eps_meas_pct"] / 100 for i in r2}
        Al = {i: used.loc[i, "alpha_FC_meas"] for i in r2}
        pe = {i: np.full(len(grid), np.nan) for i in r2}
        pa = {i: np.full(len(grid), np.nan) for i in r2}
        for k, i in enumerate(r2):
            for g, A in enumerate(grid):
                pe[i][g], pa[i][g] = parts[i].props(A)
            prog(0.10 + 0.25 * (k + 1) / len(r2), f"Stage 2: filter cake {k + 1}/{len(r2)}")

        def ll_rows(keep):
            ll = np.zeros(len(grid))
            for i in keep:
                if pd.notna(E_[i]):
                    ll += -0.5 * ((pe[i] - E_[i]) / (nz["eps_rel"] * E_[i])) ** 2
                if pd.notna(Al[i]):
                    ll += -0.5 * ((np.log(pa[i]) - np.log(Al[i])) / nz["alpha_log"]) ** 2
            return ll

        g2 = _grid_post(grid, ll_rows(r2), mu0["A"], sd0["A"])
        post["A"], post_sd["A"] = g2["mean"], g2["sd"]
        st2["A"] = g2
        ia, i0 = np.argmin(np.abs(grid - g2["mean"])), np.argmin(np.abs(grid - mu0["A"]))
        loo_e, loo_a = [], []
        for i in r2:
            gi = _grid_post(grid, ll_rows([k for k in r2 if k != i]), mu0["A"], sd0["A"])
            j = np.argmin(np.abs(grid - gi["mean"]))
            loo_e.append(pe[i][j]); loo_a.append(pa[i][j])
        ye = np.array([E_[i] for i in r2], float)
        ya = np.array([Al[i] for i in r2], float)
        st2.update(ID=list(used.loc[r2, "ID"]), y_eps=ye, y_alpha=ya,
                   eps_prior=np.array([pe[i][i0] for i in r2]), eps_post=np.array([pe[i][ia] for i in r2]),
                   alpha_prior=np.array([pa[i][i0] for i in r2]), alpha_post=np.array([pa[i][ia] for i in r2]),
                   eps_loo=np.array(loo_e), alpha_loo=np.array(loo_a), q2_eps=_q2(ye, loo_e),
                   q2_alpha=_q2(np.log(ya), np.log(loo_a)))
        if all(p.file and p.Ag < 0.02 for p in parts.values()):
            res["warnings"].append("A: the agglomeration degrees of the filter cakes are close to zero, so A is "
                                   "hardly informed by these data.")
    res["stages"]["A"] = st2

    # ---------------- stage 3: B
    r3 = [i for i in range(len(used)) if "φ_RM" in chk.loc[i, "usable"]]
    st3 = dict(n=len(r3), params=["B"] if "B" in free else [])
    if r3 and "B" in free:
        th = (post["mu_s"], post["a_rtd"], post["b_rtd"])
        th0 = (mu0["mu_s"], mu0["a_rtd"], mu0["b_rtd"])
        Bk = np.linspace(0.4, 5.0, 11)
        grid = np.linspace(0.4, 5.0, 461)
        emu, y = {}, {}
        tot = len(r3)
        for k, i in enumerate(r3):
            prog(0.36 + 0.6 * k / tot, f"Stage 3: residual moisture, experiment {k + 1}/{tot} (filtration module)")
            inp = row_inputs(used.loc[i], post, material, uploads)
            part = parts.get(i) or _Particles(inp)
            vals = np.array([_phi(inp, part, post["A"], b, th) for b in Bk])
            v0 = _phi(inp, part, mu0["A"], mu0["B"], th0)
            if np.all(np.isfinite(vals)):
                emu[i] = (CubicSpline(Bk, vals), v0)
                y[i] = used.loc[i, "phi_RM_meas_pct"] / 100
            else:
                res["warnings"].append(f"{used.loc[i, 'ID']}: cake formation not completed on the filter medium "
                                       "(z_S1 > L_f) – residual moisture not usable for B.")
        ok = list(emu)

        def ll_rows(keep):
            ll = np.zeros(len(grid))
            for i in keep:
                ll += -0.5 * ((emu[i][0](grid) - y[i]) / nz["phi_abs"]) ** 2
            return ll

        if ok:
            g3 = _grid_post(grid, ll_rows(ok), mu0["B"], sd0["B"])
            post["B"], post_sd["B"] = g3["mean"], g3["sd"]
            st3["B"] = g3
            loo = []
            for i in ok:
                gi = _grid_post(grid, ll_rows([k for k in ok if k != i]), mu0["B"], sd0["B"])
                loo.append(float(emu[i][0](gi["mean"])))
            yy = np.array([y[i] for i in ok])
            rng = np.random.default_rng(2)
            Bs = rng.choice(grid, size=400, p=g3["pdf"] / g3["pdf"].sum())
            band = np.array([np.percentile(emu[i][0](Bs), [2.5, 97.5]) for i in ok])
            st3.update(ID=list(used.loc[ok, "ID"]), y=yy, pred_prior=np.array([emu[i][1] for i in ok]),
                       pred_post=np.array([float(emu[i][0](g3["mean"])) for i in ok]), pred_loo=np.array(loo),
                       band=band, q2=_q2(yy, loo))
            st3["rmse_prior"] = float(np.sqrt(np.mean((st3["pred_prior"] - yy) ** 2)))
            st3["rmse_post"] = float(np.sqrt(np.mean((st3["pred_post"] - yy) ** 2)))
        st3["n"] = len(ok)
    res["stages"]["B"] = st3
    prog(1.0, "done")

    # ---------------- summary and identifiability
    summ = []
    for k in PARAMS:
        upd = k in free and ((k in th_free and r1) or (k == "A" and r2) or (k == "B" and st3.get("B")))
        ratio = post_sd[k] / sd0[k] if upd else 1.0
        summ.append(dict(param=k, label=LABEL[k], prior_mean=mu0[k], prior_sd=sd0[k], post_mean=post[k],
                         post_sd=post_sd[k], updated=bool(upd), sd_ratio=ratio))
        if upd and ratio > 0.8:
            res["warnings"].append(f"{SHORT[k]}: posterior uncertainty is still {100 * ratio:.0f} % of the prior "
                                   "uncertainty – the data hardly inform this parameter (result close to the prior).")
    res["summary"] = summ
    res["post"], res["post_sd"] = post, post_sd
    return res


def new_set(res, name, description="", base=None):
    n = {k: res["stages"][s].get("n", 0) for k, s in [("theta_m", "theta"), ("cakes", "A"), ("phi_RM", "B")]}
    s = dict(name=name, readonly=False, material=res["material"], params={k: float(v) for k, v in res["post"].items()},
             std={k: float(v) for k, v in res["post_sd"].items()}, noise=res["noise"],
             created=_dt.datetime.now().strftime("%Y-%m-%d %H:%M"), based_on=base,
             description=description or f"Bayesian calibration with {n['theta_m']} RTD values, {n['cakes']} filter "
                                        f"cakes, and {n['phi_RM']} residual moistures.", data=n)
    if res["stages"]["theta"].get("corr"):
        s["corr_theta"] = res["stages"]["theta"]["corr"]
    return s


def phi_interval(inp, s, n_out=2):
    """95 % interval of the residual moisture at the outlet from the uncertainty of B of a parameter set"""
    sd = float(s.get("std", {}).get("B", 0) or 0)
    if sd <= 0:
        return None
    out = []
    for B in (inp.B - 1.96 * sd, inp.B + 1.96 * sd):
        i2 = E.Inputs.from_json(inp.to_json())
        i2.B = max(B, 0.1)
        r = E.run_filtration(i2)
        out.append(r["kpi"]["phi_end"])
    return min(out), max(out)
