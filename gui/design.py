"""Bayesian experimental design for the CVSF model ("which experiment improves the model most?").

Basis: the current parameter set / model state (posterior of the latest Bayesian calibration with all active
experiments) with its covariance Sigma of the parameters p = (mu_s, a, b, A, B).

For every candidate experiment the model is linearized around the current parameters (Jacobian J of the measured
quantities with respect to p) and the expected information gain (EIG, D-optimal criterion of Bayesian design) is
calculated:  EIG = 1/2 ln det(I + R^-1 J Sigma J^T)  with R the measurement/model uncertainty of the measured
quantities. The expected posterior covariance after the experiment is Sigma' = Sigma - Sigma J^T (J Sigma J^T + R)^-1 J Sigma.

The plan of the next k experiments is built by sequential (greedy) Bayesian optimization of the acquisition function
    a(x) = EIG(x | Sigma) / cost(type)  normalized  +  w * novelty(x)
after each selected experiment, Sigma is updated, so the next selection accounts for the information already planned.
The novelty term (distance to existing and already planned experiments in the normalized design space) adds
exploration: experiments in regions without data also test the model structure (model discrepancy), which the
parameter information alone does not capture.

Experiment types (same as the calibration stages):
  RTD          residence time distribution -> theta_m       (informs mu_s, a, b)    design: screw, n_screw
  cake         filter cake test -> porosity, alpha_FC      (informs A)             design: d50,3, Ag3 (PSD)
  CVSF run     residual moisture at the module outlet      (informs B)             design: two of Q, n, dp, T, w_solid
"""
from __future__ import annotations

import concurrent.futures as cf
import os

import numpy as np
import pandas as pd

import calibration as C
import database as D
import engine as E

cvsf = E.cvsf
P5 = C.PARAMS                       # mu_s, a_rtd, b_rtd, A, B
AXES = {  # name: (label, unit, Inputs attribute, factor)
    "Q": ("Q_susp", "mL/min", "Q", 1.0),
    "n": ("n_screw", "rpm", "n", 1.0),
    "dp": ("Δp", "mbar", "dp", 1.0),
    "T": ("ϑ_susp", "°C", "T", 1.0),
    "ws": ("w_solid", "wt.-%", "ws", 0.01),
}


# ---------------------------------------------------------------------------------------------------------------
# prior / current posterior
# ---------------------------------------------------------------------------------------------------------------
def covariance(s):
    sd = np.array([float(s["std"][k]) for k in P5])
    R = np.eye(5)
    c = s.get("corr_theta")
    if c is not None and np.shape(c) == (3, 3):
        R[:3, :3] = np.array(c, float)
    return np.outer(sd, sd) * R


def noise(s):
    nz = dict(theta_rel=0.05, eps_rel=0.05, alpha_log=0.42, phi_abs=0.02)
    nz.update(C.reference_set().get("noise", {}))
    nz.update(s.get("noise", {}) or {})
    return nz


def eig(J, R, S):
    J = np.atleast_2d(J)
    M = J @ S @ J.T
    sign, ld = np.linalg.slogdet(np.eye(len(R)) + np.linalg.solve(R, M))
    return 0.5 * ld


def update(S, J, R):
    J = np.atleast_2d(J)
    K = S @ J.T @ np.linalg.inv(J @ S @ J.T + R)
    return S - K @ J @ S


# ---------------------------------------------------------------------------------------------------------------
# candidates with Jacobians
# ---------------------------------------------------------------------------------------------------------------
def rtd_candidates(s, screws=("a", "b", "c"), n_range=(1.0, 5.0), nn=41):
    p = s["params"]
    nz = noise(s)
    rows = []
    for sc in screws:
        g = cvsf.SCREWS[sc]
        for n in np.linspace(*n_range, nn):
            def th(mu, a, b):
                return cvsf.theta_m(g["d_i"], 0.025, g["P"], n, int(g["N"]), mu, a, b)
            base = [p["mu_s"], p["a_rtd"], p["b_rtd"]]
            t0 = th(*base)
            J = np.zeros((1, 5))
            for j in range(3):
                h = 1e-5 * max(abs(base[j]), 1e-2)
                q = list(base); q[j] += h
                J[0, j] = (th(*q) - t0) / h
            R = np.array([[(nz["theta_rel"] * t0) ** 2]])
            rows.append(dict(type="RTD", screw=sc, n=float(n), pred=float(t0), J=J, R=R,
                             coord=np.array([n / n_range[1]]), group=sc))
    return rows


def _lognormal_inp(shape, d50, sg, Ag3, psi_geo, rhos, A):
    inp = E.Inputs()
    inp.shape, inp.psd_mode, inp.d50, inp.sigma_g = shape, "lognormal", float(d50), float(sg)
    inp.psi_mode, inp.psi_geo, inp.Ag3, inp.rhos, inp.A = "geometric", float(psi_geo), float(Ag3), float(rhos), float(A)
    inp.inc3 = 250                                   # coarser synthetic PSD: sufficient for the sensitivities
    return inp


def cake_candidates(s, shape="bipyramidal", sg=0.5, psi_geo=0.876, d50_range=(50.0, 600.0), ag_range=(0.0, 0.75),
                    nd=10, na=9, rhos=1420.0):
    A = float(s["params"]["A"])
    nz = noise(s)
    rows = []
    for d50 in np.geomspace(*d50_range, nd):
        for ag in np.linspace(*ag_range, na):
            if ag >= 0.95 * A:
                continue
            p0 = E.prepare_particles(_lognormal_inp(shape, d50, sg, ag, psi_geo, rhos, A))
            h = 1e-3 * A
            p1 = E.prepare_particles(_lognormal_inp(shape, d50, sg, ag, psi_geo, rhos, A + h))
            J = np.zeros((2, 5))
            J[0, 3] = (p1["eps"] - p0["eps"]) / h
            J[1, 3] = (np.log(p1["alpha_s"]) - np.log(p0["alpha_s"])) / h
            R = np.diag([(nz["eps_rel"] * p0["eps"]) ** 2, nz["alpha_log"] ** 2])
            rows.append(dict(type="cake", shape=shape, d50=float(d50), sigma_g=float(sg), Ag3=float(ag),
                             psi_geo=float(psi_geo), pred_eps=float(p0["eps"]), pred_alpha=float(p0["alpha_s"]), J=J, R=R,
                             coord=np.array([(np.log(d50) - np.log(d50_range[0])) / np.log(d50_range[1] / d50_range[0]),
                                             (ag - ag_range[0]) / max(ag_range[1] - ag_range[0], 1e-9)]),
                             group="cake"))
    return rows


def _phi_pair(args):
    """worker: residual moisture at the outlet for B and B + dB (and z_S1)"""
    inp_json, dB = args
    inp = E.Inputs.from_json(inp_json)
    part = E.prepare_particles(inp)
    E._set_rtd(inp)
    o = E._op(inp)
    r0 = E._quiet(cvsf.module, part["eps"], part["alpha_s"], op=o, B=inp.B, use_theta=inp.use_theta)
    if not r0["finished"]:
        return False, np.nan, np.nan, float(r0["z_S1"])
    r1 = E._quiet(cvsf.module, part["eps"], part["alpha_s"], op=o, B=inp.B + dB, use_theta=inp.use_theta)
    return True, float(r0["phi_evap_end"]), float(r1["phi_evap_end"]), float(r0["z_S1"])


def run_candidates(s, base: E.Inputs, xname, xr, yname, yr, nx=7, ny=7, progress=None, workers=None):
    """grid of CVSF runs over two operating parameters; sensitivity of phi_RM to B (stage 3 of the calibration)"""
    nz = noise(s)
    base = E.Inputs.from_json(base.to_json())
    C.apply_set(base, s)
    xs, ys = np.linspace(*xr, nx), np.linspace(*yr, ny)
    jobs, meta = [], []
    dB = 0.05
    for j, yv in enumerate(ys):
        for i, xv in enumerate(xs):
            inp = E.Inputs.from_json(base.to_json())
            for nm, v in ((xname, xv), (yname, yv)):
                setattr(inp, AXES[nm][2], v * AXES[nm][3])
            jobs.append((inp.to_json(), dB))
            meta.append((i, j, xv, yv))
    out = [None] * len(jobs)
    workers = workers or max(1, min(4, (os.cpu_count() or 2)))
    done = 0
    try:
        if workers > 1:
            with cf.ProcessPoolExecutor(max_workers=workers) as ex:
                futs = {ex.submit(_phi_pair, a): k for k, a in enumerate(jobs)}
                for f in cf.as_completed(futs, timeout=120 + 10 * len(jobs)):
                    out[futs[f]] = f.result()
                    done += 1
                    if progress:
                        progress(done / len(jobs), f"CVSF runs: {done}/{len(jobs)} grid points")
        else:
            raise RuntimeError("serial")
    except Exception:                                          # noqa: BLE001  (fallback: serial evaluation)
        for k, a in enumerate(jobs):
            if out[k] is None:
                out[k] = _phi_pair(a)
            done = sum(o is not None for o in out)
            if progress:
                progress(done / len(jobs), f"CVSF runs: {done}/{len(jobs)} grid points")
    rows = []
    for (i, j, xv, yv), (ok, f0, f1, z) in zip(meta, out):
        J = np.zeros((1, 5))
        if ok:
            J[0, 4] = (f1 - f0) / dB
        R = np.array([[nz["phi_abs"] ** 2]])
        rows.append(dict(type="CVSF run", x=float(xv), y=float(yv), ix=i, iy=j, feasible=bool(ok), pred=f0, z_S1=z,
                         J=J, R=R, coord=np.array([(xv - xr[0]) / max(xr[1] - xr[0], 1e-9),
                                                   (yv - yr[0]) / max(yr[1] - yr[0], 1e-9)]), group="run"))
    return dict(rows=rows, xs=xs, ys=ys, xname=xname, yname=yname, base=base)


# ---------------------------------------------------------------------------------------------------------------
# existing experiments (reference data + active database) in the design coordinates
# ---------------------------------------------------------------------------------------------------------------
def existing(material, run_axes=None, cake_ranges=None, n_max=6.0):
    import Benchmark_data_2 as BD
    import props as PR
    smap = {"ES": "a", "MS": "b", "AMS": "c"}
    rtd = [dict(screw=smap[d.screw_type], n=float(d.screw_speed), source="filtration study") for d in BD.DATA_POINTS]
    cakes, runs = [], []
    for lab, f, r, dsc, e, a in PR.A_EXP:
        cakes.append(dict(file=os.path.join(cvsf.MODEL_DIR, r), desc=os.path.join(cvsf.MODEL_DIR, dsc) if dsc else None,
                          shape=f, source="filtration study", ID=lab))
    for lab, f, r, dsc, phi in PR.B_EXP:
        runs.append(dict(Q=60.0, n=3.0, dp=80.0, T=21.0, ws=6.0, source="filtration study", ID=lab))
    if material:
        act = D.active_data(material)
        for _, r in act.iterrows():
            if pd.notna(r["theta_m_meas"]) and r["screw"] in ("a", "b", "c") and pd.notna(r["n_rpm"]):
                rtd.append(dict(screw=r["screw"], n=float(r["n_rpm"]), source=r["dataset_id"]))
            if pd.notna(r["eps_meas_pct"]) or pd.notna(r["alpha_FC_meas"]):
                cakes.append(dict(file=C._resolve(r["psd_results"], {}) if r["psd_results"] else None,
                                  desc=C._resolve(r["psd_descriptors"], {}) if r["psd_descriptors"] else None,
                                  d50=r["d50_um"], Ag3=r["Ag3"], shape=r["shape"], source=r["dataset_id"], ID=r["ID"]))
            if pd.notna(r["phi_RM_meas_pct"]):
                runs.append(dict(Q=r["Q_mL_min"], n=r["n_rpm"], dp=r["dp_mbar"], T=r["T_C"], ws=r["w_solid_pct"],
                                 source=r["dataset_id"], ID=r["ID"]))
    return dict(rtd=pd.DataFrame(rtd), cakes=pd.DataFrame(cakes), runs=pd.DataFrame(runs))


def cake_coords(cakes):
    """d50,3 and Ag3 of existing filter cakes (from the PSD files or the d-values)"""
    out = []
    for _, c in cakes.iterrows():
        d50, ag = c.get("d50"), c.get("Ag3")
        f = c.get("file")
        if f and os.path.exists(str(f)):
            try:
                inp = E.Inputs()
                inp.shape, inp.psd_mode, inp.psd_results, inp.psd_descriptors = c["shape"], "file", f, c.get("desc")
                p = E.prepare_particles(inp)
                d50, ag = p["d50"], p["Ag3"]
            except Exception:                                  # noqa: BLE001
                pass
        if d50 is not None and pd.notna(d50):
            out.append(dict(d50=float(d50), Ag3=float(ag) if ag is not None and pd.notna(ag) else 0.0,
                            source=c["source"], ID=c.get("ID", "")))
    return pd.DataFrame(out, columns=["d50", "Ag3", "source", "ID"])


# ---------------------------------------------------------------------------------------------------------------
# sequential Bayesian optimization of the experiment plan
# ---------------------------------------------------------------------------------------------------------------
def plan(cands, S, k=5, w_explore=0.3, cost=None, existing_coords=None):
    """greedy batch: maximize EIG/cost (normalized) + w * novelty; update Sigma after every selection"""
    cost = cost or {"RTD": 1.0, "cake": 1.0, "CVSF run": 1.0}
    ex = {g: [np.asarray(c, float) for c in v] for g, v in (existing_coords or {}).items()}
    cands = [c for c in cands if c.get("feasible", True)]
    sel, Sk = [], S.copy()
    sd0 = np.sqrt(np.diag(S))
    for step in range(min(k, len(cands))):
        g = np.array([eig(c["J"], c["R"], Sk) / cost[c["type"]] for c in cands])
        gmax = g.max() if g.max() > 0 else 1.0
        nov = np.zeros(len(cands))
        for i, c in enumerate(cands):
            pts = ex.get(c["group"], [])
            nov[i] = min([np.linalg.norm(c["coord"] - p) for p in pts] + [1.0])
        nov = np.clip(nov / 0.5, 0, 1)                           # distance >= 0.5 (normalized) counts as fully new
        score = g / gmax + w_explore * nov
        i = int(np.argmax(score))
        c = cands[i]
        e = eig(c["J"], c["R"], Sk)
        Sk = update(Sk, c["J"], c["R"])
        ex.setdefault(c["group"], []).append(c["coord"])
        sel.append(dict(c, rank=step + 1, EIG=float(e), novelty=float(nov[i]), score=float(score[i]),
                        sd_after=np.sqrt(np.diag(Sk))))
    return sel, sd0, np.sqrt(np.diag(Sk))


def acquisition_map(cands, S, cost):
    return np.array([eig(c["J"], c["R"], S) / cost[c["type"]] if c.get("feasible", True) else np.nan for c in cands])


def plan_table(sel, run_info=None, sd0=None):
    rows = []
    for c in sel:
        if c["type"] == "RTD":
            what = f"RTD with screw ({c['screw']}) at n_screw = {c['n']:.2f} rpm"
            meas = "θm"
        elif c["type"] == "cake":
            what = (f"filter cake test: {c['shape']} particles, d50,3 ≈ {c['d50']:.0f} µm (σg ≈ {c['sigma_g']:.2f}), "
                    f"agglomeration degree Ag3 ≈ {c['Ag3']:.2f}")
            meas = "ε, α_FC, PSD"
        else:
            b = run_info["base"]
            xl, yl = AXES[run_info["xname"]], AXES[run_info["yname"]]
            fixed = {k: v for k, v in dict(Q=b.Q, n=b.n, dp=b.dp, T=b.T, ws=100 * b.ws).items()
                     if k not in (run_info["xname"], run_info["yname"])}
            what = (f"CVSF run: {xl[0]} = {c['x']:.3g} {xl[1]}, {yl[0]} = {c['y']:.3g} {yl[1]}; "
                    + ", ".join(f"{AXES[k][0]} = {v:.3g} {AXES[k][1]}" for k, v in fixed.items()))
            meas = f"φ_RM at outlet (predicted {100 * c['pred']:.1f} %), PSD"
        red = {C.SHORT[p]: 100 * (1 - c["sd_after"][j] / sd0[j]) for j, p in enumerate(P5)} if sd0 is not None else {}
        rows.append(dict(rank=c["rank"], type=c["type"], experiment=what, measure=meas, EIG_nat=round(c["EIG"], 3),
                         novelty=round(c["novelty"], 2),
                         **{f"SD↓ {k} / % (cum.)": round(v, 1) for k, v in red.items()}))
    return pd.DataFrame(rows)


def plan_template_rows(sel, run_info, material):
    """experiment plan as rows of the experimental-data template (measured columns empty)"""
    rows = []
    for c in sel:
        r = {k: None for k in C.COLS}
        r.update(ID=f"PLAN-{c['rank']:02d} {c['type']}", include=1)
        if c["type"] == "RTD":
            r.update(shape="bipyramidal", setup="current", screw=c["screw"], n_rpm=round(c["n"], 2),
                     note="planned: measure theta_m (RTD)")
        elif c["type"] == "cake":
            r.update(shape=c["shape"], Ag3=None, note=f"planned: filter cake test with PSD d50,3 ~ {c['d50']:.0f} µm, "
                                                      f"sigma_g ~ {c['sigma_g']:.2f}, Ag3 ~ {c['Ag3']:.2f}; enter PSD file, "
                                                      "porosity and alpha_FC")
        else:
            b = E.Inputs.from_json(run_info["base"].to_json())
            for nm, v in ((run_info["xname"], c["x"]), (run_info["yname"], c["y"])):
                setattr(b, AXES[nm][2], v * AXES[nm][3])
            r.update(shape=b.shape, setup="previous" if b.setup == "steenweg" else "current", screw=b.screw
                     if b.screw in cvsf.SCREWS else "a", Q_mL_min=round(b.Q, 1), w_solid_pct=round(100 * b.ws, 2),
                     n_rpm=round(b.n, 2), dp_mbar=round(b.dp, 0), T_C=round(b.T, 1),
                     note=f"planned: measure residual moisture at the outlet (predicted {100 * c['pred']:.1f} %) "
                          "and the PSD")
        rows.append(r)
    return C._types(pd.DataFrame(rows))
