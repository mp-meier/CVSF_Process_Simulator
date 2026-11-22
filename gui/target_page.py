"""CVSF Process Simulator – tab "Experiments for this prediction": Bayesian experimental design targeted at the
current simulation. Which experiments, how many and at which parameters are needed so that the prediction for THESE
inputs (θm, z_S1, φ_RM) comes as close as possible to reality?"""
import json
import os
import tempfile

import numpy as np
import plotly.graph_objects as go
import streamlit as st

import calibration as C
import design as G
import engine as E

COL = {"theta_m": "#1F4E79", "z_S1": "#E6AF2D", "phi_end": "#2E8B57"}
LAB = {"theta_m": "θm (residence time)", "z_S1": "z_S1 (end of cake formation)", "phi_end": "φ_RM (residual moisture)"}
UNIT = {"theta_m": "%", "z_S1": "%", "phi_end": "pp"}


def _compute(inp_json, set_json, goal_red, k_max, cost, types, bar):
    s = json.loads(set_json)
    inp = E.Inputs.from_json(inp_json)
    bar.progress(0.02, "Sensitivities of the simulated quantities to the model parameters …")
    y0, Jt, keep, fin = G.target_jacobian(inp)
    kpi = E.run_filtration(inp)["kpi"]
    cands, info = G.target_candidates(s, inp, kpi, progress=lambda f, t: bar.progress(min(0.1 + f * 0.8, 0.9), t))
    cands = [c for c in G.relevance(cands, inp, kpi) if c["type"] in types]
    S = G.covariance(s)
    ci0 = G._ci(S, y0, Jt, keep)
    fl = G.floors(s)
    goals = {k: max((1 - goal_red / 100) * v, fl[k]) for k, v in ci0.items()}
    bar.progress(0.93, "Sequential Bayesian optimization of the experiment plan …")
    sel, hist, reached = G.target_plan(cands, S, y0, Jt, keep, goals, k_max=k_max, cost=cost)
    bar.progress(1.0, "done")
    nz = G.noise(s)
    return dict(y0=y0, keep=keep, finished=fin, ci0=ci0, goals=goals, sel=sel, hist=hist, reached=reached, info=info,
                material=dict(s.get("material") or {}, name=(s.get("material") or {}).get("name", "material system")), noise=nz, set=s["name"])


def _excel(df, material):
    p = os.path.join(tempfile.mkdtemp(), "plan.xlsx")
    C.write_template(p, df, material)
    return open(p, "rb").read()


def render(R, I, ACTIVE, kpi_fn):
    ss = st.session_state
    st.markdown("**Which experiments make this prediction reliable?** For the current inputs of the simulation, the "
                "software determines by Bayesian experimental design **which** experiments, **how many** and at "
                "**which parameters** in the CVSF reduce the uncertainty of the predicted residence time θm, end of "
                "cake formation z_S1 and residual moisture φ_RM most effectively – starting from the current model "
                f"state *{ACTIVE['name']}*.")
    with st.expander("Method", icon=":material/info:"):
        st.markdown(r"""
- **Prediction uncertainty:** the simulated quantities $y = (\theta_m, z_{S1}, \varphi_{RM})$ are linearized in the
  model parameters $p = (\mu_s, a, b, A, B)$ at the current inputs, $J_y = \partial y/\partial p$. With the parameter
  covariance $\Sigma$ of the model state, the parameter-related variance is $V = \mathrm{diag}(J_y \Sigma J_y^\mathsf{T})$
  (shown as 95 % half-width).
- **Candidate experiments around the simulated point:** RTD measurements (θm) with the simulated and the other screws
  at n_screw = 1–5 rpm and at the simulated speed; filter cake tests (ε, α_FC) with the simulated particle shape,
  d50,3 between half and twice the simulated value and Ag3 ± 0.15; CVSF runs (residual moisture) at Q_susp ± 30 % and
  Δp ± 20 mbar around the simulated operating point.
- **Relevance for this prediction:** the measurement uncertainty $R$ of a candidate is increased with its distance $d$
  to the simulated conditions, $R_\mathrm{eff} = R\,(1 + 3 d^2)$, because the model discrepancy grows with distance.
  Experiments at or near the simulated point are therefore preferred.
- **Sequential Bayesian optimization:** each step selects the experiment with the largest expected reduction of the
  prediction variance $\sum_y (V_y(\Sigma_k) - V_y(\Sigma_{k+1}))/V_y(\Sigma_0)$ per effort (cost), and updates
  $\Sigma_{k+1} = \Sigma_k - \Sigma_k J^\mathsf{T}(J\Sigma_k J^\mathsf{T}+R)^{-1}J\Sigma_k$. Selecting the same
  experiment again means a replicate. The plan stops when the goal is reached for all quantities, when further
  experiments barely help, or at the maximum number. A quantity counts as sufficiently precise when its 95 %
  half-width is below ± 1 % (θm), ± 2 % (z_S1), ± 0.5 pp (φ_RM) or below one third of the 95 % scatter of a single
  measurement of this quantity (a further improvement could hardly be verified experimentally).
- **Limits:** only the parameter-related uncertainty can be reduced by calibration. The scatter of the measurements and
  structural model deviations remain (shown as irreducible scatter for φ_RM). Washing parameters are not calibrated yet.
""")
    c1, c2, c3 = st.columns([1.2, 1.2, 2])
    goal = c1.slider("Goal: reduce the prediction uncertainty by", 10, 90, 50, 5, format="%d %%",
                     help="Reduction of the 95 % half-width of each simulated quantity compared with today")
    k_max = c2.slider("Maximum number of experiments", 3, 30, 20)
    t1, t2, t3 = c3.columns(3)
    use = {"RTD": t1.checkbox("RTD (θm)", True, key="tp_rtd"),
           "cake": t2.checkbox("Filter cake test", True, key="tp_cake"),
           "CVSF run": t3.checkbox("CVSF run (φ_RM)", True, key="tp_run")}
    cost = {"RTD": t1.number_input("effort RTD", 0.1, 10.0, 1.0, 0.1, key="tp_c1"),
            "cake": t2.number_input("effort cake", 0.1, 10.0, 0.5, 0.1, key="tp_c2"),
            "CVSF run": t3.number_input("effort run", 0.1, 10.0, 2.0, 0.1, key="tp_c3")}
    types = [k for k, v in use.items() if v]
    key = json.dumps([I.to_json(), ACTIVE["name"], goal, k_max, cost, types], sort_keys=True, default=str)
    res = ss.get("tp_res") if ss.get("tp_key") == key else None
    if st.button("Plan experiments for this simulation", type="primary", icon=":material/science:",
                 disabled=not types):
        bar = st.progress(0.0, "Starting …")
        try:
            res = _compute(I.to_json(), json.dumps(ACTIVE, default=float), goal, k_max, cost, types, bar)
            ss.tp_res, ss.tp_key = res, key
        except Exception as ex:                                # noqa: BLE001
            st.error(f"The experiment plan could not be computed: {ex}")
            res = None
        bar.empty()
    if res is None:
        if ss.get("tp_res") is not None:
            st.info("Inputs or settings have changed – plan the experiments again for the current simulation.",
                    icon=":material/refresh:")
        else:
            st.caption("Computation time about 10–30 s.")
        return
    sel, hist, keep = res["sel"], res["hist"], res["keep"]
    keys = [G.TARGETS[t][0] for t in keep]
    n = len(sel)
    cols = st.columns(1 + len(keys))
    kpi_fn(cols[0], "Recommended experiments", f"{n}",
           ("goal reached" if res["reached"] else ("goal not fully reachable with these experiment types" if n < k_max
                                                   else f"maximum of {k_max} reached")),
           "ok" if res["reached"] else "bad")
    y0 = res["y0"]
    val = {"theta_m": f"{y0[0]:.3f}", "z_S1": f"{y0[1]:.2f} cm", "phi_end": f"{100 * y0[2]:.1f} %"}
    for j, k in enumerate(keys):
        a, b = res["ci0"][k], hist[-1][k]
        kpi_fn(cols[1 + j], LAB[k], f"± {a:.2g} → ± {b:.2g} {UNIT[k]}",
               f"prediction {val[k]}; 95 % half-width now → after the plan (goal ± {res['goals'][k]:.2g} {UNIT[k]})",
               "ok" if b <= res["goals"][k] + 1e-12 else "neu")
    if not res["finished"]:
        st.warning("Cake formation is not completed on the frit (z_S1 > L_f): no residual moisture is predicted, "
                   "the plan covers θm and z_S1.", icon="⚠️")
    if "phi_end" in keys:
        sc = 100 * 1.96 * float(res["noise"].get("phi_abs", 0.02))
        st.caption(f"φ_RM: in addition to the parameter-related uncertainty, the residual moisture scatters by about "
                   f"± {sc:.1f} pp (95 %, measurement scatter and model deviations of the calibration data). This part "
                   "cannot be reduced by further calibration; replicate CVSF runs at the simulated point show it directly.")
    scr = f"screw ({I.screw})" if I.screw in ("a", "b", "c") else \
        f"the simulated screw (d_i = {1e3 * I.d_i:.1f} mm, P = {1e3 * I.P:.1f} mm, N = {int(I.N)})"
    val_txt = (f"**Validation of this prediction** (independent of the calibration plan): 2 replicate CVSF runs at "
               f"exactly the simulated inputs – Q_susp = {I.Q:g} mL/min, n_screw = {I.n:g} rpm, Δp = {I.dp:g} mbar, "
               f"ϑ = {I.T:g} °C, w_solid = {100 * I.ws:g} wt.-%, {scr} – measuring the residual moisture at the outlet "
               f"(prediction {100 * y0[2]:.1f} %)" if res["finished"] else
               f"**Validation of this prediction**: an RTD measurement with {scr} at n_screw = {I.n:g} rpm")
    val_txt += f", and one RTD measurement with {scr} at n_screw = {I.n:g} rpm (prediction θm = {y0[0]:.3f})." \
        if res["finished"] else f" (prediction θm = {y0[0]:.3f})."
    if n == 0:
        st.success("The parameter-related uncertainty of this prediction already meets the goal – no further "
                   "calibration experiments needed.", icon="✅")
        st.info(val_txt, icon=":material/fact_check:")
        return
    l, r = st.columns([1.5, 1])
    with l:
        st.markdown("**Experiment plan** (order = priority; replicates are summarized)")
        tab = G.target_plan_table(sel, res["info"])
        st.dataframe(tab, hide_index=True, width="stretch",
                     column_config={"Experiment (parameters)": st.column_config.TextColumn(width="large")})
        rows = G.target_template_rows(sel, res["info"], res["material"])
        st.download_button("Experiment plan as Excel template (measured columns to be filled after the experiments)",
                           _excel(rows, res["material"]), "CVSF_experiment_plan_for_this_simulation.xlsx",
                           icon=":material/download:")
        st.info(val_txt, icon=":material/fact_check:")
        st.caption("After the experiments: fill in the measured values, upload the template in the mode *Calibration* "
                   "and recalibrate – the simulation then uses the improved model state.")
    with r:
        f = go.Figure()
        x = list(range(len(hist)))
        for k in keys:
            yv = [100 * h[k] / res["ci0"][k] for h in hist]
            f.add_trace(go.Scatter(x=x, y=yv, mode="lines+markers", name=LAB[k], line=dict(color=COL[k], width=3),
                                   hovertemplate="after %{x} experiments: %{y:.0f} % of today<extra></extra>"))
        f.add_hline(y=100 - goal, line=dict(color="#C00000", dash="dash"), annotation_text=f"goal {100 - goal} % (unless already below the precision floor)",
                    annotation_position="top right")
        types_seq = [c["type"] for c in sel]
        f.add_trace(go.Scatter(x=list(range(1, n + 1)), y=[3] * n, mode="text",
                               text=["R" if t == "RTD" else ("K" if t == "cake" else "V") for t in types_seq],
                               textfont=dict(color="#5A6573", size=11), showlegend=False, hoverinfo="skip"))
        f.update_layout(template="simple_white", height=420, xaxis_title="number of experiments",
                        yaxis_title="95 % half-width / % of today", yaxis_range=[0, 105],
                        legend=dict(orientation="h", y=-0.25), margin=dict(t=30, b=10),
                        title="Prediction uncertainty vs. number of experiments")
        st.plotly_chart(f, width="stretch")
        st.caption("Letters along the axis: R = RTD, K = filter cake test, V = CVSF run (order of the plan).")
