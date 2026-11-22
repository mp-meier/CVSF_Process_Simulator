"""CVSF Process Simulator – mode "Calibration": experimental data of completed CVSF runs -> Bayesian calibration."""
import io
import json
import os
import tempfile

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import calibration as C
import database as D
import engine as E

BLUE, RED, GREY, DARK, GOLD = "#1F4E79", "#C00000", "#9AA5B1", "#1E1E1E", "#E6AF2D"


GUIDE_PDF = os.path.join(E.ROOT, "docs", "Guide_Experimental_Data_Template.pdf")
REF_MATERIAL = "L-alanine / water"


def _excel_bytes(df=None, material=None):
    p = os.path.join(tempfile.mkdtemp(), "t.xlsx")
    C.write_template(p, df, material)
    return open(p, "rb").read()


@st.cache_data(show_spinner=False)
def _template_xlsx():
    return _excel_bytes()


def _go_sim(name):
    st.session_state.param_set = name
    st.session_state.applied_set = None
    st.session_state.mode = "Simulation"


def _prior_for(material):
    """prior of the continuous calibration: reference set; widened for other material systems"""
    ref = C.reference_set()
    scale = 1.0 if material == REF_MATERIAL else 5.0
    return ref, scale


DATA_CFG = {
    "include": st.column_config.CheckboxColumn("use", width="small"),
    "active": st.column_config.CheckboxColumn("active", width="small",
                                              help="only active experiments enter the Bayesian calibration"),
    "exclusion_reason": st.column_config.TextColumn("reason for deactivation", width="medium"),
    "shape": st.column_config.SelectboxColumn("shape", options=list(E.SHAPES)),
    "setup": st.column_config.SelectboxColumn("setup", options=["current", "previous"]),
    "screw": st.column_config.SelectboxColumn("screw", options=["a", "b", "c"]),
    "psd_results": st.column_config.TextColumn("PSD file"),
    "psd_descriptors": st.column_config.TextColumn("descriptors file"),
    "d10_um": st.column_config.NumberColumn("d10,3 / µm", format="%.1f"),
    "d50_um": st.column_config.NumberColumn("d50,3 / µm", format="%.1f"),
    "d90_um": st.column_config.NumberColumn("d90,3 / µm", format="%.1f"),
    "psi_eff": st.column_config.NumberColumn("ψ_eff", format="%.3f"),
    "Ag3": st.column_config.NumberColumn("Ag3", format="%.3f"),
    "Q_mL_min": st.column_config.NumberColumn("Q / mL min⁻¹", format="%.1f"),
    "w_solid_pct": st.column_config.NumberColumn("w_solid / %", format="%.1f"),
    "n_rpm": st.column_config.NumberColumn("n / rpm", format="%.2f"),
    "dp_mbar": st.column_config.NumberColumn("Δp / mbar", format="%.0f"),
    "T_C": st.column_config.NumberColumn("ϑ / °C", format="%.1f"),
    "theta_m_meas": st.column_config.NumberColumn("θm meas.", format="%.3f"),
    "eps_meas_pct": st.column_config.NumberColumn("ε meas. / %", format="%.2f"),
    "alpha_FC_meas": st.column_config.NumberColumn("α_FC meas. / m kg⁻¹", format="%.3e"),
    "phi_RM_meas_pct": st.column_config.NumberColumn("φ_RM meas. / %", format="%.2f"),
}


def render(kpi, tmpdir):
    ss = st.session_state
    if "calib_df" not in ss:
        ss.calib_df = C.empty_table(3)
        ss.calib_mat = dict(name=REF_MATERIAL, rhos=1420.0, sigma=72.25e-3)
        ss.calib_uploads = {}
        ss.calib_src = ""
        ss.calib_example = False
    st.markdown("Experimental data of completed CVSF runs are collected in the **experiment database**. The model "
                "is recalibrated by **Bayesian calibration** with all *active* experiments of a material system, "
                "always starting from the reference parameter set of the filtration study. Datasets or single "
                "experiments can be deactivated at any time (e.g. if an experiment turns out to be not representative); "
                "the next recalibration then no longer contains them.")
    with st.expander("How the calibration works", icon=":material/info:"):
        st.markdown("""
| Stage | Parameters | Experimental data | Model |
|---|---|---|---|
| 1 | μs, a, b (θm correlation, Fit 1) | dimensionless mean solids residence time θm (RTD) | extended vortex efficiency |
| 2 | A (sphericity correction, Fit F1) | filter cake porosity ε and/or specific cake resistance α_FC + PSD | packing model / Carman-Kozeny |
| 3 | B (equilibrium saturation, Fit F2) | residual moisture φ_RM at the outlet of the filtration module + PSD + operating point | complete filtration module |

- **Prior:** reference parameter set of the filtration study with its uncertainty (for other material systems with
  5 × the uncertainty). Its 33 data are not stored in the database again (no double counting).
- **Likelihood:** Gaussian with the stated measurement/model uncertainty. **Posterior:** stage 1 by Markov chain Monte
  Carlo, stages 2 and 3 on a fine parameter grid; later stages use the posterior means of earlier stages.
- **Continuous improvement:** every recalibration uses all active experiments of the material system. The result is a
  versioned *model state* with provenance (datasets, experiments, data fingerprint); after checking the results, it is
  adopted as the current model of the material system and used in the simulation.
- Liquid properties (density, viscosity) are those of the L-alanine/water mother liquor; the washing model is not
  calibrated in this version.
""")
    t1, t2, t3, t4 = st.tabs([":material/upload_file: 1 · Add data", ":material/database: 2 · Experiment database",
                              ":material/model_training: 3 · Recalibrate model",
                              ":material/inventory_2: 4 · Model states & parameter sets"])
    with t1:
        _tab_add(kpi, tmpdir)
    with t2:
        _tab_db(kpi)
    with t3:
        _tab_calib(kpi)
    with t4:
        _tab_sets()


# ------------------------------------------------------------------------------------------------------ 1 add data
def _tab_add(kpi, tmpdir):
    ss = st.session_state
    st.markdown("##### Template and guide")
    c1, c2, c3 = st.columns(3)
    c1.download_button("Excel template", _template_xlsx(), "CVSF_experimental_data_template.xlsx",
                       icon=":material/download:", width="stretch",
                       help="sheets: Instructions, Experiments (to fill), Example, Material system")
    if os.path.exists(GUIDE_PDF):
        c2.download_button("Guide with screenshots (PDF)", open(GUIDE_PDF, "rb").read(),
                           "Guide_Experimental_Data_Template.pdf", icon=":material/menu_book:", width="stretch")
    if c3.button("Show example rows", icon=":material/visibility:", width="stretch",
                 help="three example rows of the filtration study (cannot be added to the database)"):
        ss.calib_df = C.example_rows()
        ss.calib_mat = dict(name=REF_MATERIAL, rhos=1420.0, sigma=72.25e-3)
        ss.calib_example = True
        ss.calib_src = "example"
        st.rerun()
    st.markdown("##### Upload")
    u1, u2 = st.columns(2)
    up = u1.file_uploader("Filled template (xlsx)", type=["xlsx"], key="calib_up")
    if up is not None and ss.get("calib_up_name") != up.name + str(up.size):
        try:
            df, mat = C.read_table(up)
            ss.calib_df = df
            if mat:
                ss.calib_mat = mat
            ss.calib_src = up.name
            ss.calib_example = False
        except Exception as ex:                                # noqa: BLE001
            st.error(f"The file could not be read as CVSF template: {ex}")
        ss.calib_up_name = up.name + str(up.size)
        st.rerun()
    ups = u2.file_uploader("PSD files referenced in the template (PSDResults_*.xlsx, ImageDescriptors_*.xlsx)",
                           type=["xlsx"], accept_multiple_files=True, key="calib_psd")
    for f in ups or []:
        if f.name not in ss.calib_uploads:
            p = os.path.join(tmpdir, f.name)
            with open(p, "wb") as fh:
                fh.write(f.getbuffer())
            ss.calib_uploads[f.name] = p
    if ss.calib_uploads:
        u2.caption("Uploaded: " + ", ".join(sorted(ss.calib_uploads)))

    st.markdown("##### Check and complete the experiments" + (f" – source: `{ss.calib_src}`" if ss.calib_src else ""))
    df = ss.calib_df.copy()
    df["include"] = df["include"].astype(bool)
    ed = st.data_editor(df, num_rows="dynamic", column_config=DATA_CFG, width="stretch", height=300,
                        key=f"calib_editor_{ss.calib_src}", hide_index=True)
    ed = ed.copy()
    ed["include"] = ed["include"].fillna(True).astype(bool).astype(int)
    ss.calib_df = C._types(ed)
    chk = C.check_table(ss.calib_df, ss.calib_uploads)
    nth = int(chk["usable"].str.contains("θm").sum())
    nab = int(chk["usable"].str.contains("ε/α").sum())
    nph = int(chk["usable"].str.contains("φ_RM").sum())
    bad = chk[chk["issues"] != ""]
    c = st.columns(4)
    kpi(c[0], "θm values (stage 1: μs, a, b)", str(nth), "RTD measurements", "ok" if nth else "neu")
    kpi(c[1], "Filter cakes (stage 2: A)", str(nab), "porosity / cake resistance", "ok" if nab else "neu")
    kpi(c[2], "Residual moistures (stage 3: B)", str(nph), "outlet of the filtration module", "ok" if nph else "neu")
    npl = int((chk["plausibility"] != "").sum())
    kpi(c[3], "Rows with issues", str(len(bad)), ("fix them before adding" if len(bad) else "all rows complete")
        + (f" · {npl} plausibility hints" if npl else ""), "bad" if len(bad) or npl else "ok")
    st.dataframe(chk.rename(columns={"usable": "usable for", "issues": "missing information",
                                     "plausibility": "plausibility check (units?)"}), hide_index=True, width="stretch",
                 height=min(38 + 35 * len(chk), 260))
    st.markdown("##### Dataset information")
    m1, m2, m3 = st.columns(3)
    ss.calib_mat["name"] = m1.text_input("Material system", ss.calib_mat["name"],
                                         help="datasets with the same name are calibrated together")
    ss.calib_mat["rhos"] = m2.number_input("ρ_solid / kg m⁻³", 300.0, 8000.0, float(ss.calib_mat["rhos"]), 10.0)
    ss.calib_mat["sigma"] = m3.number_input("σ_liquid / mN m⁻¹", 5.0, 100.0, 1e3 * float(ss.calib_mat["sigma"]),
                                            0.5) / 1e3
    d1, d2, d3 = st.columns([1.4, 1, 1])
    name = d1.text_input("Dataset name", os.path.splitext(ss.calib_src)[0] if ss.calib_src not in ("", "example")
                         else "", placeholder="e.g. CVSF campaign 2027-03, screw (c)")
    operator = d2.text_input("Operator", "")
    date = d3.date_input("Date of the experiments", value=None)
    desc = st.text_area("Description (purpose, special features, deviations)", height=70)
    usable = nth + nab + nph
    disabled = ss.calib_example or usable == 0 or not name
    if ss.calib_example:
        st.info("The example rows are part of the reference parameter set and cannot be added (double counting).",
                icon=":material/block:")
    elif len(bad):
        st.warning("Rows with issues are stored, but not used in the calibration until they are complete.",
                   icon="⚠️")
    if st.button("Add dataset to the experiment database", type="primary", icon=":material/library_add:",
                 disabled=disabled):
        ds = D.add_dataset(ss.calib_df, ss.calib_mat, name, operator, date, desc, ss.calib_src, ss.calib_uploads)
        st.success(f"Dataset {ds} added ({len(ss.calib_df)} experiments). The current model state of "
                   f"'{ss.calib_mat['name']}' is now outdated – recalibrate in tab 3.", icon=":material/check_circle:")
        ss.calib_df = C.empty_table(3)
        ss.calib_src = ""
    if not name and not ss.calib_example:
        st.caption("Enter a dataset name to add the data.")


# ------------------------------------------------------------------------------------------------------ 2 database
def _tab_db(kpi):
    db = D.load()
    mats = sorted(D.materials(db))
    with st.expander("Storage location of the experiment database and the parameter sets", icon=":material/folder:"):
        st.caption(f"Current folder: `{C.storage_root()}`")
        new = st.text_input("New folder (e.g. a shared network folder of the working group)", "")
        if st.button("Use this folder", disabled=not new):
            try:
                C.set_storage_root(new)
                st.success("Storage location changed.")
                st.rerun()
            except OSError as ex:
                st.error(f"Folder not usable: {ex}")
    if not db["datasets"]:
        st.info("The experiment database is still empty. Add experimental data in tab 1.", icon=":material/inbox:")
        _log_view()
        return
    mat = st.selectbox("Material system", ["all"] + mats)
    tab = D.datasets_table(db, None if mat == "all" else mat)
    st.markdown("##### Datasets")
    st.caption("Deactivate a dataset (checkbox) to exclude all its experiments from the calibration; enter the reason. "
               "Changes are logged.")
    ed = st.data_editor(tab, hide_index=True, width="stretch", key=f"ds_editor_{mat}",
                        disabled=[c for c in tab.columns if c not in ("active", "exclusion_reason")],
                        column_config={"active": DATA_CFG["active"],
                                       "exclusion_reason": DATA_CFG["exclusion_reason"],
                                       "experiments": st.column_config.NumberColumn("exp.", width="small"),
                                       "active_experiments": st.column_config.NumberColumn("active exp.",
                                                                                           width="small"),
                                       "theta_m": st.column_config.NumberColumn("θm", width="small"),
                                       "cakes": st.column_config.NumberColumn("ε/α", width="small"),
                                       "phi_RM": st.column_config.NumberColumn("φ_RM", width="small")})
    changed = ed[(ed["active"] != tab["active"]) | (ed["exclusion_reason"].fillna("") != tab["exclusion_reason"].fillna(""))]
    if len(changed):
        miss = changed[(~changed["active"]) & (changed["exclusion_reason"].fillna("").str.strip() == "")]
        if len(miss):
            st.warning("Please enter a reason for each deactivated dataset.", icon="⚠️")
        if st.button("Save dataset changes", type="primary", icon=":material/save:", disabled=bool(len(miss))):
            for _, r in changed.iterrows():
                D.set_dataset_active(r["dataset_id"], bool(r["active"]), r["exclusion_reason"] or "")
            st.rerun()
    st.markdown("##### Experiments of a dataset")
    opts = list(tab["dataset_id"])
    sel = st.selectbox("Dataset", opts, format_func=lambda i: f"{i} – {tab.set_index('dataset_id').loc[i, 'dataset']}")
    d = next(x for x in db["datasets"] if x["id"] == sel)
    if not d.get("active", True):
        st.warning(f"The whole dataset is deactivated: {d.get('exclusion_reason', '')}", icon=":material/block:")
    rf = D.rows_frame(d)
    chk = C.check_table(rf.assign(include=1))
    rf["usable for"] = chk["usable"].values
    rf["issues"] = chk["issues"].values
    show = ["active", "exclusion_reason", "row_id", "ID", "usable for", "issues"] + [c for c in C.COLS if c not in
                                                                                    ("ID", "include")]
    rv = st.data_editor(rf[show], hide_index=True, width="stretch", key=f"row_editor_{sel}", height=320,
                        disabled=[c for c in show if c not in ("active", "exclusion_reason")], column_config=DATA_CFG)
    ch = rv[(rv["active"] != rf["active"]) | (rv["exclusion_reason"].fillna("") != rf["exclusion_reason"].fillna(""))]
    if len(ch):
        miss = ch[(~ch["active"]) & (ch["exclusion_reason"].fillna("").str.strip() == "")]
        if len(miss):
            st.warning("Please enter a reason for each deactivated experiment.", icon="⚠️")
        if st.button("Save experiment changes", type="primary", icon=":material/save:", disabled=bool(len(miss))):
            D.set_rows_active(sel, {r["row_id"]: (bool(r["active"]), r["exclusion_reason"] or "")
                                    for _, r in ch.iterrows()})
            st.rerun()
    with st.expander(f"Dataset details and deletion ({sel})", icon=":material/description:"):
        st.write({k: d.get(k) for k in ("name", "material", "experiment_date", "operator", "added", "added_by",
                                        "source_file", "description")})
        st.download_button("Export dataset (Excel)", _excel_bytes(rf[C.COLS], d["material"]), f"{sel}.xlsx",
                           icon=":material/download:")
        conf = st.checkbox(f"I want to delete dataset {sel} permanently (deactivation is usually sufficient)")
        if st.button("Delete dataset", icon=":material/delete:", disabled=not conf):
            D.delete_dataset(sel)
            st.rerun()
    _log_view()


def _log_view():
    with st.expander("Change log", icon=":material/history:"):
        st.dataframe(D.read_log(), hide_index=True, width="stretch")


# ------------------------------------------------------------------------------------------------------ 3 calibrate
def _tab_calib(kpi):
    ss = st.session_state
    db = D.load()
    mats = sorted(set(D.materials(db)) | {REF_MATERIAL})
    mat = st.selectbox("Material system", mats, index=mats.index(REF_MATERIAL), key="cal_mat")
    sets = C.list_sets()
    act = D.active_data(mat, db)
    cur = D.current_state(mat) or (C.REFERENCE_NAME if mat == REF_MATERIAL else None)
    outdated = D.is_outdated(mat, sets)
    chk = C.check_table(act, {}) if len(act) else pd.DataFrame(columns=["usable"])
    nth = int(chk["usable"].str.contains("θm").sum()) if len(chk) else 0
    nab = int(chk["usable"].str.contains("ε/α").sum()) if len(chk) else 0
    nph = int(chk["usable"].str.contains("φ_RM").sum()) if len(chk) else 0
    c = st.columns(4)
    kpi(c[0], "Current model state", (cur or "–").split("–")[-1].strip(), cur or "no model state yet",
        "bad" if outdated else "ok")
    kpi(c[1], "Status", "outdated" if outdated else "up to date",
        "active data changed since the current model state" if outdated else "current model state uses all active data",
        "bad" if outdated else "ok")
    kpi(c[2], "Active experiments", str(len(act)),
        f"{len(set(act['dataset_id'])) if len(act) else 0} datasets · θm {nth} · ε/α {nab} · φ_RM {nph}")
    ref, scale = _prior_for(mat)
    kpi(c[3], "Prior", "reference set", f"filtration study · uncertainty × {scale:g}")
    if not len(act):
        st.info("No active experiments for this material system – the model corresponds to the reference parameter "
                "set" + (" (current model state)." if mat == REF_MATERIAL else "."), icon=":material/info:")
        if mat == REF_MATERIAL and cur != C.REFERENCE_NAME and st.button("Reset current model state to the reference set"):
            D.set_current_state(mat, C.REFERENCE_NAME)
            st.rerun()
        return
    st.markdown("**Parameters to calibrate**")
    cc = st.columns(5)
    free = [k for j, k in enumerate(C.PARAMS) if cc[j].checkbox(C.SHORT[k], value=True, key=f"free_{k}",
                                                               help=C.LABEL[k])]
    with st.expander("Prior distributions (normal; editable)", icon=":material/functions:"):
        pr = pd.DataFrame([(k, C.LABEL[k], ref["params"][k], ref["std"][k] * scale) for k in C.PARAMS],
                          columns=["key", "parameter", "prior mean", "prior SD"])
        pr = st.data_editor(pr, disabled=["key", "parameter"], hide_index=True, width="stretch", key=f"prior_{mat}",
                            column_config={"key": None, "prior mean": st.column_config.NumberColumn(format="%.4f"),
                                           "prior SD": st.column_config.NumberColumn(format="%.4f")})
    nz0 = dict(theta_rel=0.05, eps_rel=0.05, alpha_log=0.42, phi_abs=0.02)
    nz0.update(ref.get("noise", {}))
    with st.expander("Measurement and model uncertainty (likelihood)", icon=":material/straighten:"):
        n1, n2, n3, n4 = st.columns(4)
        nz = dict(theta_rel=n1.number_input("θm, relative / %", 0.1, 50.0, 100 * nz0["theta_rel"], 0.5) / 100,
                  eps_rel=n2.number_input("ε, relative / %", 0.1, 50.0, 100 * nz0["eps_rel"], 0.5) / 100,
                  alpha_log=n3.number_input("α_FC, SD of ln / -", 0.01, 3.0, float(nz0["alpha_log"]), 0.05),
                  phi_abs=n4.number_input("φ_RM, absolute / %-pts.", 0.1, 20.0, 100 * nz0["phi_abs"], 0.1) / 100)
        st.caption("Defaults: root-mean-square residuals of the reference data (scatter of measurement and model).")
    mats_db = D.materials(db)
    material = mats_db.get(mat, dict(name=mat, rhos=1420.0, sigma=72.25e-3))
    if st.button("Recalibrate model with all active experiments", type="primary", icon=":material/play_arrow:"):
        bar = st.progress(0.0, "starting …")
        ov = {r["key"]: (r["prior mean"], max(r["prior SD"], 1e-9)) for _, r in pr.iterrows()}
        try:
            res = C.calibrate(act, ref, free=free, prior_override=ov, noise=nz, material=material, uploads={},
                              progress=lambda f, t: bar.progress(min(max(f, 0.0), 1.0), t))
            ss.calib_res = res
            ss.calib_state = D.model_state(res, mat, act, dict(base=ref["name"], scale=scale,
                                                               free=free, noise=nz))
            bar.empty()
        except Exception as ex:                                # noqa: BLE001
            bar.empty()
            st.error(f"Calibration failed: {ex}")
    st.caption("Run time: approx. 6 s per residual moisture value (complete filtration module on a B grid).")
    R, S = ss.get("calib_res"), ss.get("calib_state")
    if R and S and S.get("material_system") == mat:
        st.markdown("---")
        st.markdown(f"#### Result: {S['name']}")
        st.caption(S["description"] + f" Data fingerprint: {S['provenance']['fingerprint']}.")
        b1, b2, b3 = st.columns(3)
        if b1.button("Adopt as current model state", type="primary", icon=":material/verified:", width="stretch"):
            C.save_set(S)
            D.set_current_state(mat, S["name"])
            st.success("Adopted – the simulation uses this model state for "
                       f"'{mat}' (selectable in the sidebar).", icon=":material/check_circle:")
        if b2.button("Save only (not current)", icon=":material/save:", width="stretch"):
            C.save_set(S)
            st.success("Saved.")
        b3.download_button("Download model state (JSON)", json.dumps(S, indent=1, default=float),
                           C._slug(S["name"]) + ".json", icon=":material/download:", width="stretch")
        _results(R, kpi)


# ------------------------------------------------------------------------------------------------------ 4 sets
def _tab_sets():
    sets = C.list_sets()
    cur = D.all_current()
    rows = []
    for n, s in sets.items():
        p, sd = s["params"], s["std"]
        is_cur = n in cur.values() or (n == C.REFERENCE_NAME and REF_MATERIAL not in cur)
        rows.append(dict(current=is_cur, name=n, kind=s.get("kind", "reference" if s.get("readonly") else
                                                                    "parameter set"),
                         material=s.get("material", {}).get("name", ""),
                         **{C.SHORT[k]: f"{p[k]:.4g} ± {sd.get(k, 0):.2g}" for k in C.PARAMS},
                         experiments=s.get("provenance", {}).get("n_experiments"),
                         created=s.get("created", "")))
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    up = st.file_uploader("Import parameter set / model state (JSON)", type=["json"], key="set_up")
    if up is not None and st.button("Import", icon=":material/upload:"):
        try:
            C.save_set(json.loads(up.getvalue().decode()))
            st.success("Imported.")
        except (ValueError, KeyError) as ex:
            st.error(f"Import failed: {ex}")
    for n, s in sets.items():
        with st.expander(n, icon=":material/lock:" if s.get("readonly") else (
                ":material/verified:" if n in cur.values() else ":material/description:")):
            st.write(s.get("description", ""))
            if s.get("provenance"):
                pv = s["provenance"]
                st.caption(f"Datasets: {', '.join(pv['datasets']) or '–'} · experiments: {pv['n_experiments']} · "
                           f"fingerprint {pv['fingerprint']} · created by {pv.get('created_by', '')}")
            c1, c2, c3, c4 = st.columns(4)
            c1.button("Use in simulation", key=f"use_{n}", on_click=_go_sim, args=(n,),
                      icon=":material/rocket_launch:")
            m = s.get("material_system") or s.get("material", {}).get("name", REF_MATERIAL)
            if c2.button("Set as current model state", key=f"cur_{n}", icon=":material/verified:"):
                D.set_current_state(m, n)
                st.rerun()
            c3.download_button("JSON", json.dumps(s, indent=1, default=float), C._slug(n) + ".json",
                               key=f"dl_{n}", icon=":material/download:")
            if not s.get("readonly") and n not in cur.values() and c4.button("Delete", key=f"del_{n}",
                                                                             icon=":material/delete:"):
                C.delete_set(n)
                st.rerun()


def _parity(x, ys, title, xt, log=False, band=None, fmt="%.3f"):
    f = go.Figure()
    allv = np.concatenate([np.asarray(x, float)] + [np.asarray(y, float) for y, *_ in ys])
    allv = allv[np.isfinite(allv)]
    lo, hi = allv.min(), allv.max()
    pad = (hi - lo) * 0.08 if not log else 0
    lo, hi = (lo / 1.4, hi * 1.4) if log else (lo - pad, hi + pad)
    f.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", line=dict(color=DARK, width=1), name="1:1",
                           hoverinfo="skip"))
    for y, nm, sty, ids in ys:
        err = None
        if band is not None and nm.startswith("posterior"):
            err = dict(type="data", symmetric=False, array=band[:, 1] - y, arrayminus=y - band[:, 0], color=BLUE,
                       thickness=1)
        f.add_trace(go.Scatter(x=x, y=y, mode="markers", name=nm, marker=sty, error_y=err, text=ids,
                               hovertemplate="%{text}<br>measured %{x:.4g}<br>model %{y:.4g}<extra></extra>"))
    f.update_layout(template="simple_white", height=380, title=title, xaxis_title="measured " + xt,
                    yaxis_title="model " + xt, legend=dict(orientation="h", y=-0.25), margin=dict(t=50))
    if log:
        f.update_xaxes(type="log", range=[np.log10(lo), np.log10(hi)])
        f.update_yaxes(type="log", range=[np.log10(lo), np.log10(hi)])
    else:
        f.update_xaxes(range=[lo, hi])
        f.update_yaxes(range=[lo, hi])
    return f


def _q(v):
    return "n.a. (< 3 data)" if v is None or not np.isfinite(v) else f"{v:.2f}"


def _results(R, kpi):
    for w in R["warnings"]:
        st.warning(w, icon="⚠️")
    sm = pd.DataFrame(R["summary"])
    cols = st.columns(5)
    for j, r in sm.iterrows():
        k = r["param"]
        ch = r["post_mean"] - r["prior_mean"]
        kpi(cols[j], C.LABEL[k], f"{r['post_mean']:.4g} ± {r['post_sd']:.2g}",
            (f"prior {r['prior_mean']:.4g} ± {r['prior_sd']:.2g} · change {ch:+.3g}" if r["updated"]
             else "not updated (no data or not selected)"),
            ("ok" if r["sd_ratio"] <= 0.8 else "bad") if r["updated"] else "neu")
    st.markdown("##### Prior and posterior distributions")
    S1, S2, S3 = R["stages"]["theta"], R["stages"]["A"], R["stages"]["B"]
    upd = [r["param"] for _, r in sm.iterrows() if r["updated"]]
    if upd:
        fig = make_subplots(rows=1, cols=len(upd), subplot_titles=[C.SHORT[k] for k in upd])
        for j, k in enumerate(upd, start=1):
            m0, s0 = R["prior"]["mean"][k], R["prior"]["sd"][k]
            if k in ("A", "B"):
                g = (S2 if k == "A" else S3)[k]
                lo_ = min(m0 - 4 * s0, g["mean"] - 5 * g["sd"])
                hi_ = max(m0 + 4 * s0, g["mean"] + 5 * g["sd"])
                msk = (g["grid"] >= lo_) & (g["grid"] <= hi_)
                x, pdf = g["grid"][msk], g["pdf"][msk]
                fig.add_trace(go.Scatter(x=x, y=pdf, fill="tozeroy", line=dict(color=BLUE), name="posterior",
                                         showlegend=j == 1), row=1, col=j)
                xr = x
            else:
                smp = S1[k]["samples"]
                fig.add_trace(go.Histogram(x=smp, histnorm="probability density", marker_color=BLUE, opacity=0.75,
                                           name="posterior", showlegend=j == 1, nbinsx=40), row=1, col=j)
                xr = np.linspace(min(smp.min(), m0 - 3 * s0), max(smp.max(), m0 + 3 * s0), 300)
            xx = xr if k not in ("A", "B") else np.linspace(max(xr[0], m0 - 4 * s0), min(xr[-1], m0 + 4 * s0), 300)
            fig.add_trace(go.Scatter(x=xx, y=np.exp(-0.5 * ((xx - m0) / s0) ** 2) / (s0 * np.sqrt(2 * np.pi)),
                                     line=dict(color=GREY, dash="dash"), name="prior", showlegend=j == 1), row=1, col=j)
        fig.update_layout(template="simple_white", height=300, margin=dict(t=40, b=30),
                          legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")
    st.markdown("##### Model vs. experiment (prior parameters, posterior parameters, leave-one-out prediction)")
    figs = []
    if S1.get("y") is not None:
        figs.append(_parity(S1["y"], [(S1["pred_prior"], "prior", dict(color=GREY, size=8), S1["ID"]),
                                      (S1["pred_loo"], "leave-one-out", dict(color=BLUE, size=10, symbol="circle-open"),
                                       S1["ID"]),
                                      (S1["pred_post"], "posterior", dict(color=BLUE, size=8), S1["ID"])],
                            f"θm · RMSE {S1['rmse_prior']:.3f} → {S1['rmse_post']:.3f} · Q²_LOO "
                            + _q(S1['q2']), "θm / -"))
    if S2.get("y_eps") is not None:
        m = np.isfinite(S2["y_eps"])
        figs.append(_parity(100 * S2["y_eps"][m], [(100 * S2["eps_prior"][m], "prior", dict(color=GREY, size=8),
                                                    np.array(S2["ID"])[m]),
                                                   (100 * S2["eps_loo"][m], "leave-one-out",
                                                    dict(color=BLUE, size=10, symbol="circle-open"), np.array(S2["ID"])[m]),
                                                   (100 * S2["eps_post"][m], "posterior", dict(color=BLUE, size=8),
                                                    np.array(S2["ID"])[m])],
                            f"Porosity · Q²_LOO {_q(S2['q2_eps'])}", "ε / %"))
        m = np.isfinite(S2["y_alpha"])
        figs.append(_parity(S2["y_alpha"][m], [(S2["alpha_prior"][m], "prior", dict(color=GREY, size=8),
                                                np.array(S2["ID"])[m]),
                                               (S2["alpha_loo"][m], "leave-one-out",
                                                dict(color=BLUE, size=10, symbol="circle-open"), np.array(S2["ID"])[m]),
                                               (S2["alpha_post"][m], "posterior", dict(color=BLUE, size=8),
                                                np.array(S2["ID"])[m])],
                            f"Cake resistance · Q²_LOO (ln) {_q(S2['q2_alpha'])}", "α_FC / m kg⁻¹", log=True))
    if S3.get("y") is not None:
        figs.append(_parity(100 * S3["y"], [(100 * S3["pred_prior"], "prior", dict(color=GREY, size=8), S3["ID"]),
                                            (100 * S3["pred_loo"], "leave-one-out",
                                             dict(color=BLUE, size=10, symbol="circle-open"), S3["ID"]),
                                            (100 * S3["pred_post"], "posterior (95 % interval from B)",
                                             dict(color=BLUE, size=8), S3["ID"])],
                            f"Residual moisture · RMSE {100 * S3['rmse_prior']:.2f} → {100 * S3['rmse_post']:.2f} %-pts."
                            f" · Q²_LOO {_q(S3['q2'])}", "φ_RM / %", band=100 * S3["band"]))
    for i in range(0, len(figs), 2):
        cc = st.columns(2)
        for j, f in enumerate(figs[i:i + 2]):
            cc[j].plotly_chart(f, width="stretch")
    if S1.get("corr") and len(S1.get("params", [])) > 1:
        st.caption("Posterior correlation of the θm parameters: " + ", ".join(
            f"{C.SHORT[S1['params'][i]]}–{C.SHORT[S1['params'][j]]}: {S1['corr'][i][j]:+.2f}"
            for i in range(len(S1["params"])) for j in range(i + 1, len(S1["params"]))))
    st.caption("Q²_LOO: each experiment is predicted with parameters calibrated without it (values near 1: good "
               "predictive capability; ≤ 0: no predictive capability beyond the mean). Residual moisture error bars: "
               "95 % interval from the posterior uncertainty of B.")
