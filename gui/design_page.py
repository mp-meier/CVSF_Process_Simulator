"""CVSF Process Simulator – mode "Experiment design": Bayesian experimental design based on the current model state."""
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
import design as G
import engine as E

BLUE, RED, GREY, DARK, GOLD, GREEN = "#1F4E79", "#C00000", "#9AA5B1", "#1E1E1E", "#E6AF2D", "#2E8B57"
SCREW_COL = {"a": "#1F4E79", "b": "#E6AF2D", "c": "#2E8B57"}
REF_MATERIAL = "L-alanine / water"


@st.cache_data(show_spinner=False)
def _rtd(set_json, n_lo, n_hi):
    return G.rtd_candidates(json.loads(set_json), n_range=(n_lo, n_hi))


@st.cache_data(show_spinner=False)
def _cakes(set_json, shape, sg, psi_geo, d_lo, d_hi, a_lo, a_hi, rhos):
    return G.cake_candidates(json.loads(set_json), shape, sg, psi_geo, (d_lo, d_hi), (a_lo, a_hi), rhos=rhos)


@st.cache_data(show_spinner=False)
def _existing(material, n_hi):
    ex = G.existing(material)
    return ex, G.cake_coords(ex["cakes"])


def _runs(set_json, base_json, xname, xr, yname, yr, nx, ny, bar):
    key = (set_json, base_json, xname, tuple(xr), yname, tuple(yr), nx, ny)
    cache = st.session_state.setdefault("doe_run_cache", {})
    if key not in cache:
        cache.clear()
        cache[key] = G.run_candidates(json.loads(set_json), E.Inputs.from_json(base_json), xname, xr, yname, yr, nx, ny,
                                      progress=lambda f, t: bar.progress(min(f, 1.0), t))
    return cache[key]


def _excel(df, material):
    p = os.path.join(tempfile.mkdtemp(), "plan.xlsx")
    C.write_template(p, df, material)
    return open(p, "rb").read()


def render(kpi):
    ss = st.session_state
    st.markdown("**Bayesian experimental design** – which experiments would improve the current model most? Based on "
                "the current model state (posterior of the latest Bayesian calibration with all active experiments), "
                "the software evaluates candidate experiments: for each candidate, the expected information gain "
                "(EIG) about the model parameters is calculated, and a plan of the next experiments is built by "
                "sequential Bayesian optimization (after each planned experiment, the expected parameter uncertainty "
                "is updated). An exploration term favors experiments in regions without data.")
    with st.expander("Method", icon=":material/info:"):
        st.markdown(r"""
- **Current knowledge:** parameter vector $p = (\mu_s, a, b, A, B)$ with mean and covariance $\Sigma$ of the selected
  parameter set (model state).
- **Candidate experiment $x$:** measured quantities $y(x)$ with uncertainty $R$ (same values as in the calibration).
  Linearization: $J = \partial y / \partial p$ at the current parameters.
- **Expected information gain:** $\mathrm{EIG}(x) = \tfrac{1}{2}\ln\det\left(I + R^{-1} J \Sigma J^\mathsf{T}\right)$
  (D-optimal Bayesian design, in nat). Expected posterior covariance: $\Sigma' = \Sigma - \Sigma J^\mathsf{T}(J\Sigma J^\mathsf{T}+R)^{-1}J\Sigma$.
- **Acquisition function** (sequential batch Bayesian optimization):
  $a(x) = \mathrm{EIG}(x\,|\,\Sigma_k)/\mathrm{cost}$ (normalized) $+\; w \cdot \mathrm{novelty}(x)$; after each selection,
  $\Sigma_k$ is updated and the experiment is added to the existing points of the novelty term.
- **Experiment types:** RTD → θm (informs μs, a, b); filter cake test → ε, α_FC (informs A); CVSF run → residual
  moisture at the outlet (informs B; infeasible operating points with $z_{S1} > L_f$ are excluded).
- **Limits:** the EIG measures information about the parameters of the existing model structure (local,
  linearized). Systematic model deviations are addressed by the exploration term and by checking new data in the
  calibration. Candidates outside the validated ranges are extrapolations of the model.
""")
    sets = C.list_sets()
    names = list(sets)
    cur = D.all_current()
    dflt = cur.get(REF_MATERIAL, C.REFERENCE_NAME)
    c1, c2, c3 = st.columns([1.6, 1, 1])
    sname = c1.selectbox("Model state / parameter set (current knowledge)", names,
                         index=names.index(dflt) if dflt in names else 0,
                         format_func=lambda n: ("★ " if n in cur.values() or (n == C.REFERENCE_NAME and REF_MATERIAL
                                                                               not in cur) else "") + n)
    S_set = sets[sname]
    material = S_set.get("material_system") or S_set.get("material", {}).get("name", REF_MATERIAL)
    k = c2.slider("Number of planned experiments", 1, 10, 5)
    w = c3.slider("Exploration weight w", 0.0, 1.0, 0.3, 0.05,
                  help="0: pure information gain; larger values favor experiments far from existing data")
    st.markdown("**Experiment types and relative effort (cost)**")
    t1, t2, t3 = st.columns(3)
    use_rtd = t1.checkbox("RTD measurement (θm)", True)
    cost_rtd = t1.number_input("cost RTD", 0.1, 10.0, 1.0, 0.1, label_visibility="collapsed")
    use_cake = t2.checkbox("Filter cake test (ε, α_FC)", True)
    cost_cake = t2.number_input("cost cake", 0.1, 10.0, 0.5, 0.1, label_visibility="collapsed")
    use_run = t3.checkbox("CVSF run (residual moisture)", True)
    cost_run = t3.number_input("cost run", 0.1, 10.0, 2.0, 0.1, label_visibility="collapsed")
    cost = {"RTD": cost_rtd, "cake": cost_cake, "CVSF run": cost_run}

    with st.expander("Design space: RTD measurements", icon=":material/timer:"):
        r1, r2 = st.columns(2)
        n_lo, n_hi = r1.slider("n_screw range / rpm", 0.5, 8.0, (1.0, 5.0), 0.25)
        r2.caption("Screws (a), (b), (c); θm correlation validated for n_screw = 1–5 rpm.")
    with st.expander("Design space: filter cake tests", icon=":material/grain:"):
        q1, q2, q3, q4 = st.columns(4)
        shape = q1.selectbox("Particle shape", list(E.SHAPES), format_func=lambda s_: E.SHAPES[s_]["label"])
        psi_default = E.SHAPES[shape]["psi_geo"] or round(E.SHAPES[shape]["psi_eff"] / (1 - 0.3 / 2.86), 3)
        psi_geo = q2.number_input("geometric sphericity ψ", 0.2, 1.0, float(psi_default), 0.01,
                                  help="bipyramidal: 0.876; other shapes: assumed from ψ_eff and Ag3 = 0.3")
        sg = q3.number_input("σg of the PSD", 0.1, 1.2, 0.5, 0.05)
        rhos = q4.number_input("ρ_solid / kg m⁻³", 300.0, 8000.0, float(S_set.get("material", {}).get("rhos", 1420.0)), 10.0)
        a1, a2 = st.columns(2)
        d_lo, d_hi = a1.slider("d50,3 range / µm", 10.0, 1000.0, (50.0, 600.0), 10.0)
        g_lo, g_hi = a2.slider("Ag3 range / -", 0.0, 0.9, (0.0, 0.75), 0.05)
    with st.expander("Design space: CVSF runs", icon=":material/precision_manufacturing:"):
        ax = list(G.AXES)
        b1, b2, b3, b4 = st.columns(4)
        xname = b1.selectbox("x-axis", ax, index=0, format_func=lambda a_: f"{G.AXES[a_][0]} / {G.AXES[a_][1]}")
        yname = b2.selectbox("y-axis", ax, index=2, format_func=lambda a_: f"{G.AXES[a_][0]} / {G.AXES[a_][1]}")
        nx = b3.slider("grid points per axis", 4, 10, 6)
        b4.caption(f"{nx * nx} operating points × 2 evaluations of the filtration module "
                   f"(approx. {nx * nx * 0.6:.0f} s, parallelized).")
        rng = {"Q": (20.0, 120.0), "n": (1.0, 5.0), "dp": (40.0, 200.0), "T": (10.0, 50.0), "ws": (2.0, 10.0)}
        lim = {"Q": (5.0, 300.0), "n": (0.5, 10.0), "dp": (10.0, 600.0), "T": (5.0, 70.0), "ws": (0.5, 25.0)}
        e1, e2 = st.columns(2)
        xr = e1.slider(f"{G.AXES[xname][0]} range", *lim[xname], rng[xname])
        yr = e2.slider(f"{G.AXES[yname][0]} range", *lim[yname], rng[yname])
        st.caption("Fixed conditions of the CVSF runs:")
        f1, f2, f3, f4, f5, f6 = st.columns(6)
        base = E.Inputs()
        base.psd_mode = "lognormal"
        base.shape = f1.selectbox("shape", list(E.SHAPES), key="run_shape", format_func=lambda s_: E.SHAPES[s_]["label"])
        base.d50 = f2.number_input("d50,3 / µm", 10.0, 2000.0, 100.0, 10.0, key="run_d50")
        base.sigma_g = f3.number_input("σg", 0.1, 1.2, 0.5, 0.05, key="run_sg")
        sk = f4.selectbox("setup", list(E.SETUPS), format_func=lambda s_: "current" if s_ == "current" else "previous")
        g = E.SETUPS[sk]
        base.setup, base.L_f, base.L_T, base.D_i = sk, g["L_f"], g["L_T"], g["D_i"]
        scr = f5.selectbox("screw", ["a", "b", "c"])
        sc = E.cvsf.SCREWS[scr]
        base.screw, base.d_i, base.P, base.N, base.w = scr, sc["d_i"], sc["P"], int(sc["N"]), sc["w"]
        fixed_vals = {"Q": 60.0, "n": 3.0, "dp": 100.0, "T": 21.0, "ws": 6.0}
        others = [a_ for a_ in ax if a_ not in (xname, yname)]
        cols = st.columns(len(others))
        for c_, a_ in zip(cols, others):
            v = c_.number_input(f"{G.AXES[a_][0]} / {G.AXES[a_][1]}", *lim[a_], fixed_vals[a_], key=f"fix_{a_}")
            setattr(base, G.AXES[a_][2], v * G.AXES[a_][3])
    if xname == yname:
        st.error("Please choose two different axes for the CVSF runs.")
        return
    if not (use_rtd or use_cake or use_run):
        st.info("Select at least one experiment type.")
        return

    go_btn = st.button("Compute experiment plan", type="primary", icon=":material/auto_awesome:")
    sj = json.dumps(S_set, default=float)
    if go_btn:
        bar = st.progress(0.0, "candidates …")
        cands = []
        res = dict(set=sname, material=material, cost=cost, w=w, k=k)
        if use_rtd:
            bar.progress(0.02, "RTD candidates")
            res["rtd"] = _rtd(sj, n_lo, n_hi)
            cands += res["rtd"]
        if use_cake:
            bar.progress(0.05, "filter cake candidates")
            res["cake"] = _cakes(sj, shape, sg, psi_geo, d_lo, d_hi, g_lo, g_hi, rhos)
            cands += res["cake"]
        if use_run:
            res["run"] = _runs(sj, base.to_json(), xname, xr, yname, yr, nx, nx, bar)
            cands += [c for c in res["run"]["rows"]]
        ex, cc = _existing(material if material in D.materials() else None, n_hi)
        excoords = {}
        for scw in ("a", "b", "c"):
            excoords[scw] = [np.array([n / n_hi]) for n in ex["rtd"][ex["rtd"]["screw"] == scw]["n"]] \
                if len(ex["rtd"]) else []
        if len(cc):
            excoords["cake"] = [np.array([(np.log(max(d, 1)) - np.log(d_lo)) / np.log(d_hi / d_lo),
                                          (a_ - g_lo) / max(g_hi - g_lo, 1e-9)]) for d, a_ in zip(cc["d50"], cc["Ag3"])]
        if use_run and len(ex["runs"]):
            pts = []
            for _, r_ in ex["runs"].iterrows():
                xv, yv = r_.get(xname), r_.get(yname)
                if pd.notna(xv) and pd.notna(yv):
                    pts.append(np.array([(xv - xr[0]) / max(xr[1] - xr[0], 1e-9), (yv - yr[0]) / max(yr[1] - yr[0], 1e-9)]))
            excoords["run"] = pts
        S = G.covariance(S_set)
        sel, sd0, sd1 = G.plan(cands, S, k=k, w_explore=w, cost=cost, existing_coords=excoords)
        per = {}
        for tp, key in (("RTD", "rtd"), ("cake", "cake"), ("CVSF run", "run")):
            cs = [c for c in cands if c["type"] == tp]
            if cs:
                per[tp] = G.plan(cs, S, k=3, w_explore=w, cost=cost, existing_coords=excoords)[0]
        res.update(sel=sel, sd0=sd0, sd1=sd1, per=per, ex=ex, cc=cc, S=S, ranges=dict(n=(n_lo, n_hi), d=(d_lo, d_hi),
                                                                                     g=(g_lo, g_hi)))
        ss.doe = res
        bar.empty()
    R = ss.get("doe")
    if not R:
        st.info("Set the design space and click **Compute experiment plan**.", icon=":material/lightbulb:")
        return
    if R["set"] != sname:
        st.warning("The plan below was computed for another parameter set – recompute.", icon="⚠️")
    _show(R, kpi, base)


def _show(R, kpi, base):
    sel, sd0, sd1 = R["sel"], R["sd0"], R["sd1"]
    run = R.get("run")
    st.markdown("---")
    st.markdown(f"#### Recommended plan of the next {len(sel)} experiments")
    cols = st.columns(5)
    for j, p in enumerate(G.P5):
        red = 100 * (1 - sd1[j] / sd0[j])
        kpi(cols[j], C.LABEL[p], f"−{red:.0f} %" if red >= 0.5 else "≈ 0 %",
            f"SD {sd0[j]:.3g} → {sd1[j]:.3g}", "ok" if red >= 10 else "neu")
    tab = G.plan_table(sel, run, sd0)
    st.dataframe(tab, hide_index=True, width="stretch",
                 column_config={"experiment": st.column_config.TextColumn(width="large")})
    rows = G.plan_template_rows(sel, run, R["material"])
    mat = C.list_sets().get(R["set"], C.reference_set()).get("material", dict(name=R["material"], rhos=1420.0,
                                                                                 sigma=72.25e-3))
    st.download_button("Experiment plan as Excel template (measured columns to be filled after the experiments)",
                       _excel(rows, mat), "CVSF_experiment_plan.xlsx", icon=":material/download:")
    st.caption("EIG in nat (natural units of information); SD↓: expected cumulative reduction of the parameter "
               "uncertainty after the experiments up to this rank. After the experiments, fill in the measured values "
               "and upload the file in the mode Calibration.")

    t = st.tabs([":material/bar_chart: Parameter uncertainty", ":material/precision_manufacturing: CVSF runs",
                 ":material/timer: RTD measurements", ":material/grain: Filter cake tests"])
    with t[0]:
        f = go.Figure()
        lab = [C.SHORT[p] for p in G.P5]
        f.add_trace(go.Bar(x=lab, y=100 * np.ones(5), name="current", marker_color=GREY))
        f.add_trace(go.Bar(x=lab, y=100 * sd1 / sd0, name="after the planned experiments", marker_color=BLUE,
                           text=[f"{100 * v:.0f} %" for v in sd1 / sd0], textposition="outside"))
        f.update_layout(template="simple_white", barmode="group", height=380, yaxis_title="parameter SD / % of current",
                        legend=dict(orientation="h", y=-0.2), yaxis_range=[0, 115])
        st.plotly_chart(f, width="stretch")
        st.caption("Expected standard deviations of the model parameters after the planned experiments (linearized "
                   "Bayesian update), relative to the current model state.")
    with t[1]:
        if not run:
            st.info("CVSF runs not selected.")
        else:
            _run_maps(R, run)
    with t[2]:
        if "rtd" not in R:
            st.info("RTD measurements not selected.")
        else:
            _rtd_plot(R)
    with t[3]:
        if "cake" not in R:
            st.info("Filter cake tests not selected.")
        else:
            _cake_map(R)


def _rank_marks(fig, pts, row=None, col=None, color=RED):
    for c in pts:
        kw = dict(row=row, col=col) if row else {}
        fig.add_trace(go.Scatter(x=[c[0]], y=[c[1]], mode="markers+text", text=[f"{c[2]}"], textposition="top center",
                                 textfont=dict(color=color, size=13), marker=dict(symbol="star", size=17, color=color,
                                                                                  line=dict(color="white", width=1)),
                                 showlegend=False, hovertext=c[3], hoverinfo="text"), **kw)


def _run_maps(R, run):
    S, cost = R["S"], R["cost"]
    xs, ys = run["xs"], run["ys"]
    rows = run["rows"]
    A = np.full((len(ys), len(xs)), np.nan)
    PH = np.full((len(ys), len(xs)), np.nan)
    Z = np.full((len(ys), len(xs)), np.nan)
    for c in rows:
        Z[c["iy"], c["ix"]] = c["z_S1"]
        if c["feasible"]:
            A[c["iy"], c["ix"]] = G.eig(c["J"], c["R"], S) / cost["CVSF run"]
            PH[c["iy"], c["ix"]] = 100 * c["pred"]
    xl, yl = G.AXES[run["xname"]], G.AXES[run["yname"]]
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Acquisition: EIG / cost (nat)", "Predicted residual moisture φ_RM / %"),
                        horizontal_spacing=0.17)
    fig.add_trace(go.Heatmap(x=xs, y=ys, z=A, colorscale="Blues", zsmooth="best", colorbar=dict(x=0.415, len=0.9, thickness=14),
                             hovertemplate=f"{xl[0]} %{{x:.3g}}<br>{yl[0]} %{{y:.3g}}<br>EIG/cost %{{z:.3g}}<extra></extra>"),
                  1, 1)
    fig.add_trace(go.Heatmap(x=xs, y=ys, z=PH, colorscale="YlOrBr", zsmooth="best", colorbar=dict(x=1.0, len=0.9, thickness=14),
                             hovertemplate=f"{xl[0]} %{{x:.3g}}<br>{yl[0]} %{{y:.3g}}<br>φ_RM %{{z:.1f}} %<extra></extra>"),
                  1, 2)
    for cc in (1, 2):
        fig.add_trace(go.Contour(x=xs, y=ys, z=Z, contours=dict(start=run["base"].L_f, end=run["base"].L_f, size=1,
                                                                 coloring="none", showlabels=False),
                                 line=dict(color=RED, width=2.5, dash="dash"), showscale=False, hoverinfo="skip",
                                 name="z_S1 = L_f", showlegend=cc == 1), 1, cc)
    ex = R["ex"]["runs"]
    if len(ex):
        exv = ex[[run["xname"], run["yname"]]].dropna()
        for cc in (1, 2):
            fig.add_trace(go.Scatter(x=exv.iloc[:, 0], y=exv.iloc[:, 1], mode="markers", name="existing experiments",
                                     marker=dict(symbol="x", size=10, color=DARK), showlegend=cc == 1), 1, cc)
    best = R["per"].get("CVSF run", [])
    plan_runs = [c for c in R["sel"] if c["type"] == "CVSF run"]
    _rank_marks(fig, [(c["x"], c["y"], f"#{c['rank']}", f"plan rank {c['rank']}") for c in plan_runs], 1, 1)
    _rank_marks(fig, [(c["x"], c["y"], f"{i + 1}", f"best CVSF run {i + 1}") for i, c in enumerate(best)], 1, 1,
                color=GOLD)
    fig.update_xaxes(title_text=f"{xl[0]} / {xl[1]}", range=[xs[0], xs[-1]])
    fig.update_yaxes(title_text=f"{yl[0]} / {yl[1]}", range=[ys[0], ys[-1]])
    fig.update_layout(template="simple_white", height=470, legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")
    st.caption("Left: information gain per cost of a CVSF run at each operating point (white: infeasible, cake formation "
               "not completed on the filter medium; red dashed: z_S1 = L_f). Gold stars: the three most informative "
               "CVSF runs; red stars with #: CVSF runs in the overall plan. ×: existing experiments (reference data "
               "and active database; other fixed conditions may differ). A CVSF run informs B; it is most informative "
               "where the residual moisture reacts most strongly to the equilibrium saturation (typically where gas "
               "deliquoring approaches equilibrium). Because the residual moisture scatters by several %-pts. around "
               "the model (measurement and model deviation), one run reduces the uncertainty of B only slightly; "
               "replicates and different particle systems are more effective.")


def _rtd_plot(R):
    S, cost = R["S"], R["cost"]
    f = go.Figure()
    for scw in ("a", "b", "c"):
        cs = [c for c in R["rtd"] if c["screw"] == scw]
        f.add_trace(go.Scatter(x=[c["n"] for c in cs], y=[G.eig(c["J"], c["R"], S) / cost["RTD"] for c in cs],
                               mode="lines", name=f"screw ({scw})", line=dict(color=SCREW_COL[scw], width=3)))
        ex = R["ex"]["rtd"]
        if len(ex):
            nn = ex[ex["screw"] == scw]["n"]
            f.add_trace(go.Scatter(x=nn, y=np.full(len(nn), -0.012 * (1 + "abc".index(scw))), mode="markers",
                                   showlegend=False,
                                   marker=dict(symbol="triangle-up", size=11, color=SCREW_COL[scw],
                                               line=dict(color=DARK, width=1)),
                                   hovertext=[f"existing RTD, screw ({scw}), n = {v:g} rpm" for v in nn], hoverinfo="text"))
    S_ = R["S"]
    _rank_marks(f, [(c["n"], G.eig(c["J"], c["R"], S_) / cost["RTD"], f"#{c['rank']}", f"plan rank {c['rank']}")
                    for c in R["sel"] if c["type"] == "RTD"])
    f.update_layout(template="simple_white", height=420, xaxis_title="n_screw / rpm",
                    yaxis_title="EIG / cost (nat), current knowledge", legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(f, width="stretch")
    st.caption("Information gain of one RTD measurement per screw over the rotational screw speed (current knowledge, "
               "before the plan). Triangles: existing RTD measurements; red stars: RTD measurements in the plan "
               "(plotted at their information gain with current knowledge). The curves show where one additional RTD "
               "measurement reduces the uncertainty of μs, a, and b most; the rotational speed exponent a is informed "
               "by measurements far from the existing speeds, the flight-number exponent b by comparing the "
               "one-flight and two-flight screws.")


def _cake_map(R):
    S, cost = R["S"], R["cost"]
    cs = R["cake"]
    d = sorted({c["d50"] for c in cs})
    a = sorted({c["Ag3"] for c in cs})
    M = np.full((len(a), len(d)), np.nan)
    for c in cs:
        M[a.index(c["Ag3"]), d.index(c["d50"])] = G.eig(c["J"], c["R"], S) / cost["cake"]
    f = go.Figure(go.Heatmap(x=d, y=a, z=M, colorscale="Blues", zsmooth="best", colorbar=dict(title="EIG/cost"),
                             hovertemplate="d50,3 %{x:.0f} µm<br>Ag3 %{y:.2f}<br>EIG/cost %{z:.3g}<extra></extra>"))
    cc = R["cc"]
    if len(cc):
        f.add_trace(go.Scatter(x=cc["d50"], y=cc["Ag3"], mode="markers", name="existing filter cakes",
                               marker=dict(symbol="x", size=11, color=DARK), hovertext=cc["ID"], hoverinfo="text"))
    _rank_marks(f, [(c["d50"], c["Ag3"], f"#{c['rank']}", f"plan rank {c['rank']}") for c in R["sel"]
                    if c["type"] == "cake"])
    _rank_marks(f, [(c["d50"], c["Ag3"], f"{i + 1}", f"best cake test {i + 1}") for i, c in
                    enumerate(R["per"].get("cake", []))], color=GOLD)
    f.update_xaxes(type="log", title_text="d50,3 / µm")
    f.update_yaxes(title_text="agglomeration degree Ag3 / -")
    f.update_layout(template="simple_white", height=460, legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(f, width="stretch")
    st.caption("Information gain of a filter cake test (porosity and cake resistance) about the sphericity correction A "
               "over the PSD of the particles. A only acts via the agglomeration degree (ψ_eff = ψ·(1 − Ag3/A)); "
               "strongly agglomerated particle systems are therefore most informative. ×: existing filter cakes.")
