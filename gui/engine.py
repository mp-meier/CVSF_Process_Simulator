"""Calculation layer of the CVSF graphical user interface.

Thin wrapper around the model code in ../scripts (cvsf.py: filtration module, washing.py: two-stage washing).
No model equation is re-implemented here; all results are identical to the scripts of the filtration and
washing studies. The functions only collect user inputs, call the model, and post-process the results."""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from dataclasses import dataclass, field, asdict

import matplotlib
matplotlib.use("Agg")                               # model routines create (unused) figures: no GUI backend
import matplotlib.pyplot as _plt                    # noqa: E402
import numpy as np                                  # noqa: E402
from scipy import special                           # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_ROOT = os.path.join(ROOT, "cvsf_model")          # model code CVSF_Model (git submodule)
sys.path.insert(0, os.path.join(MODEL_ROOT, "scripts"))
with contextlib.redirect_stdout(io.StringIO()):
    import cvsf                                     # noqa: E402  (sets the model path)
    import Filtration                               # noqa: E402
    import PSDFit_OtherShape                        # noqa: E402
    import Porosity_OtherShape                      # noqa: E402
    import CakeResistance_OtherShape                # noqa: E402
    import Sphericity_Bipyramidal                   # noqa: E402

Z90 = float(np.sqrt(2) * special.erfinv(0.8))       # 1.2816 (10 %/90 % quantile of the standard normal distribution)

# ---------------------------------------------------------------------------------------------------------------
# presets
# ---------------------------------------------------------------------------------------------------------------
SHAPES = {
    # effective (agglomeration-corrected) sphericities of the sensitivity analysis of the filtration study
    "bipyramidal": dict(label="Bipyramidal", psi_eff=0.76, psi_geo=0.876),
    "cuboid": dict(label="Cuboid", psi_eff=0.68, psi_geo=None),
    "needle": dict(label="Needle-shaped", psi_eff=0.54, psi_geo=None),
}
SETUPS = {
    "current": dict(label="Current CVSF (14 cm modules: 4 cm + 6 cm frit + 4 cm)", **cvsf.GEO_CVSF),
    "steenweg": dict(label="Previous module generation (13 cm modules, 4.5 cm frit)", **cvsf.GEO_STEENWEG),
}
SCREWS = {
    "a": dict(label="(a) one flight, P = 12 mm, d_i = 16 mm", **cvsf.SCREWS["a"]),
    "b": dict(label="(b) one flight, P = 23 mm, d_i = 21 mm", **cvsf.SCREWS["b"]),
    "c": dict(label="(c) two flights, P = 24 mm, d_i = 21 mm", **cvsf.SCREWS["c"]),
}
# ranges covered by the sensitivity analysis / data basis of the filtration study (validity hints)
RANGES = dict(d50=(20, 560, "µm"), sigma_g=(0.15, 0.9, "-"), psi=(0.3, 0.9, "-"), T=(10, 50, "°C"),
              dp=(40, 200, "mbar"), Q=(5, 100, "mL/min"), n=(0.5, 5, "rpm"), ws=(0.02, 0.10, "-"),
              R_m=(1e8, 1e9, "1/m"), P=(6.5, 24, "mm"))
EXAMPLES = {
    "Bipyramidal 355-560 µm (OP 1 validation)": dict(shape="bipyramidal",
                                                    results="PSDs/Experiments/PSDResults_Videos_BP355560_1.xlsx"),
    "Bipyramidal 160-355 µm": dict(shape="bipyramidal", results="PSDs/Experiments/PSDResults_Videos_BP160355_1.xlsx"),
    "Cuboid 93-364 µm (OP 1 validation)": dict(
        shape="cuboid", results="PSDs/DataJH/PSDResults_Videos_CuboidsJH_FK1_0104_1.xlsx",
        descriptors="PSDs/DataJH/ImageDescriptors_Videos_CuboidsJH_FK1_0104_1.xlsx"),
    "Needle-shaped 39-199 µm (OP 1 validation)": dict(
        shape="needle", results="PSDs/DataJH/PSDResults_Videos_NeedlesJH_FK1_1.xlsx",
        descriptors="PSDs/DataJH/ImageDescriptors_Videos_NeedlesJH_FK1_1.xlsx"),
}


def example_paths(name):
    e = EXAMPLES[name]
    res = os.path.join(cvsf.MODEL_DIR, e["results"])
    desc = os.path.join(cvsf.MODEL_DIR, e["descriptors"]) if e.get("descriptors") else None
    return e["shape"], res, desc


# ---------------------------------------------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------------------------------------------
@dataclass
class Inputs:
    # particle system
    shape: str = "bipyramidal"
    psd_mode: str = "lognormal"            # "file" | "lognormal" | "characteristic"
    psd_results: str | None = None         # PSDResults_*.xlsx (dynamic image analysis, Heisel et al.)
    psd_descriptors: str | None = None     # ImageDescriptors_*.xlsx (cuboid/needle)
    d50: float = 60.0                      # µm
    sigma_g: float = 0.7
    d10: float | None = None               # µm
    d90: float | None = None               # µm
    psi_mode: str = "preset"               # "preset" | "effective" | "geometric"
    psi_eff: float = 0.76
    psi_geo: float = 0.876
    Ag3: float | None = None               # override of the agglomeration degree (file) or input (geometric)
    rhos: float = 1420.0
    sigma: float = 72.25e-3
    # operation
    Q: float = 60.0                        # mL/min
    ws: float = 0.06                       # kg/kg
    n: float = 3.0                         # rpm
    n_mode: str = "set"                    # "set" | "alpha" (n_screw from target filling degree)
    alpha_target: float = 0.5
    dp: float = 80.0                       # mbar
    T: float = 21.0                        # °C
    # design
    setup: str = "current"
    L_f: float = 6.0                       # cm
    L_T: float = 8.0                       # cm
    D_i: float = 0.0252                    # m
    b: float = 0.025                       # m (width of the filter medium)
    screw: str = "a"
    d_i: float = 0.016                     # m
    P: float = 0.012                       # m
    N: int = 1
    w: float = 0.001                       # m
    R_m: float = 5e8                       # 1/m
    # air (evaporation)
    t_air: float = 25.0
    RH: float = 0.5
    Q_air: float = 4.0                     # L/min
    # model parameters
    A: float = cvsf.A_FIT
    B: float = 2.25
    use_theta: bool = True
    mu_s: float = cvsf.MU_S
    a_rtd: float = cvsf.A_RTD
    b_rtd: float = cvsf.B_RTD
    inc3: int = 1000                       # bins of the synthetic log-normal PSD
    param_set: str = "L-alanine / water – reference (filtration study)"   # name of the model parameter set

    def to_json(self):
        return json.dumps(asdict(self), indent=1)

    @staticmethod
    def from_json(s):
        d = json.loads(s)
        known = {k: v for k, v in d.items() if k in Inputs.__dataclass_fields__}
        return Inputs(**known)


# ---------------------------------------------------------------------------------------------------------------
# PSD
# ---------------------------------------------------------------------------------------------------------------
def lognormal_from_characteristics(d10=None, d50=None, d90=None):
    """median d50,3 and geometric standard deviation sigma_g of a log-normal Q3 from characteristic diameters"""
    notes = []
    if d50 and d10 and d90:
        s_lo, s_hi = np.log(d50 / d10) / Z90, np.log(d90 / d50) / Z90
        s = np.log(d90 / d10) / (2 * Z90)
        if abs(s_lo - s_hi) > 0.15 * s:
            notes.append(f"d10/d50/d90 are not consistent with a log-normal distribution (sigma_g from d10: {s_lo:.2f}, "
                         f"from d90: {s_hi:.2f}); the mean value {s:.2f} is used.")
        return float(d50), float(s), notes
    if d50 and d90:
        return float(d50), float(np.log(d90 / d50) / Z90), notes
    if d50 and d10:
        return float(d50), float(np.log(d50 / d10) / Z90), notes
    if d10 and d90:
        d50 = float(np.sqrt(d10 * d90))
        notes.append(f"d50,3 = {d50:.1f} µm estimated as geometric mean of d10,3 and d90,3.")
        return d50, float(np.log(d90 / d10) / (2 * Z90)), notes
    raise ValueError("At least two characteristic diameters (incl. d50,3 or d10,3 and d90,3) are required.")


def _quiet(f, *a, **k):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return f(*a, **k)
    finally:
        _plt.close("all")                           # figures created inside the model routines


def prepare_particles(inp: Inputs):
    """returns dict with PSD arrays (centers, Q3, dQ3), characteristic diameters, sphericity, porosity, alpha_s"""
    notes = []
    out = dict(meas_x=None, meas_Q3=None)
    if inp.psd_mode == "file":
        if not inp.psd_results or not os.path.exists(inp.psd_results):
            raise FileNotFoundError("PSDResults file not found. Please upload or select a PSD file.")
        Ag = inp.Ag3 if inp.Ag3 is not None else float(cvsf.agglomeration(inp.psd_results))
        if inp.shape == "bipyramidal":
            P = _quiet(cvsf.psd_from_file, inp.psd_results, 200)
            psi0 = np.float64(_quiet(Sphericity_Bipyramidal.sphericity, P).psi)
            psi = psi0 * (1 - Ag / inp.A)
            eps = cvsf.porosity_yu(P, psi)
            a_s = cvsf.cake_resistance(eps, P, inp.rhos, psi)
            centers, dQ3 = np.asarray(P[1]), np.asarray(P[0])
            d10, d90, d50, sg = float(P[9]), float(P[10]), float(P[11]), float(P[8])
            out.update(meas_x=np.asarray(P[6], float), meas_Q3=np.asarray(P[7], float))
        else:
            if not inp.psd_descriptors or not os.path.exists(inp.psd_descriptors):
                raise FileNotFoundError("For cuboid and needle-shaped particles, the ImageDescriptors file "
                                        "(minimum/maximum Feret diameters) is required in addition.")
            P = _quiet(PSDFit_OtherShape.PSDfit, inp.psd_descriptors, 200)
            psi0 = np.asarray(P[2], float)
            psi = psi0 * (1 - Ag / inp.A)
            eps = float(_quiet(Porosity_OtherShape.porosity, P, psi, 200))
            a_s = float(_quiet(CakeResistance_OtherShape.alpha, eps, P, inp.rhos, 200))
            centers, dQ3 = np.asarray(P[1]), np.asarray(P[0])
            d10, d90, d50 = float(P[5]), float(P[6]), float(P[7])
            sg = float(np.log(d90 / d10) / (2 * Z90))
        out.update(Ag3=float(Ag), psi_geo=float(np.mean(psi0)), psi_eff=float(np.mean(psi)))
    else:
        if inp.psd_mode == "characteristic":
            d50, sg, n2 = lognormal_from_characteristics(inp.d10, inp.d50, inp.d90)
            notes += n2
        else:
            d50, sg = float(inp.d50), float(inp.sigma_g)
        if inp.psi_mode == "preset":
            psi_eff = SHAPES[inp.shape]["psi_eff"]; Ag = None; psi_geo = None
        elif inp.psi_mode == "geometric":
            Ag = float(inp.Ag3 or 0.0); psi_geo = float(inp.psi_geo); psi_eff = psi_geo * (1 - Ag / inp.A)
        else:
            psi_eff = float(inp.psi_eff); Ag = None; psi_geo = None
        P = cvsf.psd_lognormal(d50, sg, inc3=inp.inc3)
        eps, a_s, _ = _quiet(cvsf.cake_properties_bp, P, 0.0, inp.A, inp.rhos, psi_eff)
        centers, dQ3 = np.asarray(P[1]), np.asarray(P[0])
        d10 = d50 * np.exp(-Z90 * sg); d90 = d50 * np.exp(Z90 * sg)
        out.update(Ag3=Ag, psi_geo=psi_geo, psi_eff=float(psi_eff))
        if inp.shape != "bipyramidal":
            notes.append("Log-normal input: the particle shape enters via the effective sphericity only "
                         "(approach of the sensitivity analysis of the filtration study).")
    Q3 = np.cumsum(dQ3)
    out.update(P=P, centers=centers, dQ3=dQ3, Q3=Q3, d10=float(d10), d50=float(d50), d90=float(d90),
               sigma_g=float(sg), eps=float(eps), alpha_s=float(a_s), notes=notes)
    return out


# ---------------------------------------------------------------------------------------------------------------
# filtration module
# ---------------------------------------------------------------------------------------------------------------
def _op(inp: Inputs):
    # module length through which the air is drawn (free air cross-section of the evaporation submodel)
    L_air = 130.0 if inp.setup == "steenweg" else 10 * (inp.L_f + 8.0)
    # screw geometry of the interface (preset or custom) as an additional entry of the screw table of the model
    cvsf.SCREWS["_gui"] = dict(cvsf.SCREWS["a"], d_i=inp.d_i, P=inp.P, N=int(inp.N), w=inp.w)
    return dict(T=inp.T, Q=inp.Q, ws=inp.ws, n=inp.n, dp=inp.dp, R=inp.R_m, b=inp.b, screw="_gui",
                d_i=inp.d_i, P=inp.P, N=int(inp.N), sigma=inp.sigma, rhos=inp.rhos, t_air=inp.t_air,
                p_amb=1.013e5, RH=inp.RH, Q_air=inp.Q_air, L_f=inp.L_f, L_T=inp.L_T, L_mod=inp.L_f + inp.L_T,
                D_i=inp.D_i, L_air_mm=L_air)


def _set_rtd(inp: Inputs):
    cvsf.MU_S, cvsf.A_RTD, cvsf.B_RTD = inp.mu_s, inp.a_rtd, inp.b_rtd
    cvsf.theta_m.__defaults__ = (inp.mu_s, inp.a_rtd, inp.b_rtd)


def cake_height_profile(z_cm, eps, a_s, inp: Inputs, theta):
    """filter cake height h_c(z) during cake formation (eq. of the filtration study), constant after z_S1"""
    rhol = cvsf.rho_ML(inp.T); eta = cvsf.eta_ML(inp.T)
    v = inp.P * inp.n / 60 / theta
    nf = 1 + rhol / inp.rhos * eps / (1 - eps)
    cf = rhol * inp.ws / (1 - nf * inp.ws)
    z = np.asarray(z_cm) / 100
    r = inp.R_m / a_s
    return (-r + np.sqrt(r ** 2 + 2 * cf * inp.dp * 100 * z / (eta * a_s * v))) / (inp.rhos * (1 - eps))


def n_for_filling_degree(inp: Inputs, eps, alpha_target):
    """rotational screw speed [rpm] that realizes the filling degree alpha_target (alpha ~ 1/n_screw)"""
    a1 = cvsf.filling_degree(inp.Q * 1e-6 / 60, inp.ws, 1.0 / 60, eps, inp.rhos, cvsf.rho_ML(inp.T), inp.D_i,
                             inp.d_i, inp.P, int(inp.N), inp.w)
    return float(a1 / alpha_target)


def run_filtration(inp: Inputs):
    _set_rtd(inp)
    part = prepare_particles(inp)
    if inp.n_mode == "alpha":
        inp.n = n_for_filling_degree(inp, part["eps"], inp.alpha_target)
    op = _op(inp)
    res = _quiet(cvsf.module, part["eps"], part["alpha_s"], op=op, B=inp.B, use_theta=inp.use_theta)
    th = res["theta_m"]
    rhol = cvsf.rho_ML(inp.T)
    Qs = inp.Q * 1e-6 / 60
    m_s = Qs / (1 / inp.rhos + (1 - inp.ws) / inp.ws / rhol)
    v_ax = inp.P * inp.n / 60 / th                          # m/s
    tau_f = inp.L_f / 100 / v_ax / 60                       # min on the filter medium
    tau_T = inp.L_T / 100 / v_ax / 60
    zS1 = res["z_S1"]
    dp_req = inp.dp * zS1 / inp.L_f                         # z_S1 ~ 1/dp (eq. for z_S1)
    zs = np.linspace(0, min(zS1, inp.L_f + inp.L_T), 120)
    hc = cake_height_profile(zs, part["eps"], part["alpha_s"], inp, th)
    warn = validity(inp, part, res)
    phi_at_Lf = float(np.interp(inp.L_f, res["z"], res["phi_evap"])) if res["finished"] else np.nan
    S_end = None
    if res["finished"]:
        phi = res["phi_evap_end"]
        S_end = inp.rhos / rhol * (1 - part["eps"]) / part["eps"] * phi / (1 - phi)
    kpi = dict(z_S1=zS1, finished=bool(res["finished"]), theta_m=th, alpha=res["alpha"], h_c=res["h_c"],
               eps=part["eps"], alpha_s=part["alpha_s"], psi_eff=part["psi_eff"], phi_S1=res["phi_S1"],
               phi_Lf=phi_at_Lf, phi_end=res["phi_evap_end"], phi_end_noevap=res["phi_end"],
               dphi_evap=res["phi_end"] - res["phi_evap_end"], S_end=S_end, v_ax=v_ax, tau_f=tau_f, tau_T=tau_T,
               dp_req=dp_req, m_s=m_s * 3600, d10=part["d10"], d50=part["d50"], d90=part["d90"],
               sigma_g=part["sigma_g"], Ag3=part["Ag3"], evap_ok=res.get("evap_ok", True),
               mu_star_hint=None)
    return dict(inp=inp, part=part, res=res, kpi=kpi, hc_z=zs, hc=hc, warnings=warn + part["notes"])


def validity(inp: Inputs, part, res):
    w = []
    chk = dict(d50=part["d50"], sigma_g=part["sigma_g"], psi=part["psi_eff"], T=inp.T, dp=inp.dp, Q=inp.Q, n=inp.n,
               ws=inp.ws, R_m=inp.R_m, P=inp.P * 1e3)
    for k, v in chk.items():
        lo, hi, u = RANGES[k]
        if v < lo or v > hi:
            w.append(f"{k} = {v:.3g} {u} lies outside the range covered by the filtration study ({lo:g} - {hi:g} {u}); "
                     f"the result is an extrapolation.")
    if res["alpha"] > 1.0:
        w.append(f"Filling degree {100 * res['alpha']:.0f} % > 100 %: the screw is overfilled (reduce Q_susp or "
                 f"increase n_screw / pitch).")
    elif res["alpha"] < 0.3:
        w.append(f"Filling degree {100 * res['alpha']:.0f} % < 30 %: risk of particle slip between screw and module "
                 f"wall; a filling degree of approx. 50 % is recommended.")
    if not res["finished"]:
        w.append("Cake formation is NOT completed on the filter medium (z_S1 > L_f): supernatant mother liquor "
                 "reaches the transport zone.")
    if not res.get("evap_ok", True):
        w.append("Evaporation submodel not evaluable for this geometry; evaporation neglected.")
    if inp.T <= 0:
        w.append("Temperature must be > 0 °C (viscosity correlation).")
    return w


# ---------------------------------------------------------------------------------------------------------------
# parameter studies (fast: z_S1 analytically via Filtration.filtration)
# ---------------------------------------------------------------------------------------------------------------
def zS1_only(inp: Inputs, eps, a_s, **over):
    o = dict(_op(inp)); o.update(over)
    th = cvsf.theta_m(inp.d_i, 0.025, inp.P, o["n"], int(inp.N)) if inp.use_theta else 1.0
    T = o["T"]
    _, zS1, Hc, _ = _quiet(Filtration.filtration, o["Q"] * 1e-6 / 60, o["ws"], o["n"] / 60 / th, o["dp"] * 100, T,
                           inp.b, inp.P, inp.rhos, cvsf.rho_ML(T), eps, a_s, inp.R_m, 100, o["L_mod"] / 100, o["L_f"])
    alpha = cvsf.filling_degree(o["Q"] * 1e-6 / 60, o["ws"], o["n"] / 60, eps, inp.rhos, cvsf.rho_ML(T), inp.D_i,
                                inp.d_i, inp.P, int(inp.N), inp.w)
    return zS1 * 100, alpha, th


def studies(run):
    inp, e, a = run["inp"], run["part"]["eps"], run["part"]["alpha_s"]
    _set_rtd(inp)
    dps = np.linspace(20, 200, 19)
    z_dp = [zS1_only(inp, e, a, dp=x)[0] for x in dps]
    Ts = np.linspace(10, 50, 9)
    z_T = [zS1_only(inp, e, a, T=x)[0] for x in Ts]
    # constant filling degree: Q/n = const
    ratio = inp.Q / inp.n
    ns = np.linspace(0.5, 5.0, 10)
    zq, zq_id = [], []
    for nn in ns:
        zq.append(zS1_only(inp, e, a, Q=ratio * nn, n=nn)[0])
    use = inp.use_theta
    inp.use_theta = False
    for nn in ns:
        zq_id.append(zS1_only(inp, e, a, Q=ratio * nn, n=nn)[0])
    inp.use_theta = use
    # maximum suspension volume flow rate at constant filling degree for which z_S1 = L_f
    Qmax = np.interp(inp.L_f, zq, ratio * ns) if zq[-1] > inp.L_f > zq[0] else (np.inf if zq[-1] <= inp.L_f else 0.0)
    return dict(dp=dps, z_dp=np.array(z_dp), T=Ts, z_T=np.array(z_T), n=ns, Q=ratio * ns, z_Q=np.array(zq),
                z_Q_ideal=np.array(zq_id), Qmax=float(Qmax))


def operating_window(run, Q=(10.0, 150.0), n=(0.5, 5.0), nQ=29, nn=19):
    """z_S1 and filling degree over suspension volume flow rate and rotational screw speed (other inputs fixed)"""
    inp, e, a = run["inp"], run["part"]["eps"], run["part"]["alpha_s"]
    _set_rtd(inp)
    Qs, ns = np.linspace(*Q, nQ), np.linspace(*n, nn)
    Z, A = np.zeros((nn, nQ)), np.zeros((nn, nQ))
    for i, nv in enumerate(ns):
        for j, qv in enumerate(Qs):
            Z[i, j], A[i, j], _ = zS1_only(inp, e, a, Q=qv, n=nv)
    return dict(Q=Qs, n=ns, z=Z, alpha=A)


# ---------------------------------------------------------------------------------------------------------------
# washing (two-stage), washing study
# ---------------------------------------------------------------------------------------------------------------
_WM = None


def _wm():
    global _WM
    if _WM is None:
        with contextlib.redirect_stdout(io.StringIO()):
            import washing as wm
        R = wm.load_fits()
        _WM = (wm, R)
    return _WM


def run_washing(run, dp_wash=100.0, Psi1=4.0, WR1=None, WR2=4.5, WR_max=40.0, X_star=3e-4, r_imp=0.6e-9, c_imp_0=1.0,
                rest_W1=3.0, rest_W2=6.0):
    wm, R = _wm()
    inp, part = run["inp"], run["part"]
    gam, bD = R["gamma"], R["b_D"]
    sc = dict(d_i=inp.d_i, d_o=0.025, P=inp.P, N=int(inp.N), w=inp.w)
    rhoML = cvsf.rho_ML(inp.T)
    Q = inp.Q * 1e-6 / 60; n_s = inp.n / 60
    alpha = run["res"]["alpha"]; th = run["res"]["theta_m"]
    h_c = run["res"]["h_c"]; zS1 = run["res"]["z_S1"]
    L_seg = wm.overflow_length(alpha, sc, inp.D_i)
    psi = part["psi_eff"]
    with contextlib.redirect_stdout(io.StringIO()):
        if inp.psd_mode == "file" and inp.shape == "bipyramidal":
            S_v, _ = wm.Sv_calculation(inp.psd_results, psi)
            span, d10, d50, d90 = wm.span_calculation(inp.psd_results)
            d50 = d50 * 1e-6
        else:
            Pln = cvsf.psd_lognormal(part["d50"], part["sigma_g"], inc3=1000)
            S_v, _ = wm.Sv_calculation_SenAn_PSD(Pln, psi)
            span = (part["d90"] - part["d10"]) / part["d50"]; d50 = part["d50"] * 1e-6
    pres = []
    for Psi in (Psi1, 1e8):
        lq = wm.liquids(inp.T, Psi)
        pres.append(wm._assemble(part["eps"], part["alpha_s"], psi, alpha, th, sc, Q, inp.ws, n_s, dp_wash, inp.T,
                                 r_imp, c_imp_0, inp.rhos, rhoML, L_seg, L_seg, h_c, zS1, S_v, span, d50, lq, Psi))
    p1, p2 = pres
    f1, ka1, f2, ka2 = wm.f_corr(p1), wm.ka_corr(p1), wm.f_corr(p2), wm.ka_corr(p2)
    Wg = np.linspace(0, WR_max, 801)
    X1 = wm.run_ade(p1, f1, ka1, gam, bD, Wg)[0]
    target = X_star                                             # relative impurity loading X* (0.03 %, washing study)
    wrc1 = wm.WR_crit(p1, gam, bD, X_star=X_star, WR_max=WR_max, n=801, f=f1, ka=ka1)
    WR1 = (wrc1 if np.isfinite(wrc1) else WR_max) if WR1 is None else WR1
    X1e, _, We1, cf, cs = wm.run_ade(p1, f1, ka1, gam, bD, np.array([WR1]), return_state=True)
    c0f, c0s = wm.init_second_wash(f1, f2, cf[-1], cs[-1])
    X2 = wm.run_ade(p2, f2, ka2, gam, bD, Wg, c0_flow=c0f, c0_stag=c0s)[0]
    X2a, _, We2, _, _ = wm.run_ade(p2, f2, ka2, gam, bD, np.array([WR2]), c0_flow=c0f, c0_stag=c0s,
                                   return_state=True)
    X2e = X2a[0]
    t1 = We1[0] * p1["h_FC"] * p1["epsilon"] / p1["u_Darcy"]
    z1 = t1 * p1["v_FC"] * 100                                  # cm of filter length needed for the wash liquid
    Xtr = wm.run_ade(p2, f2, ka2, gam, bD, Wg)[0]                 # wash liquid 1 uniformly in the pores (tracer)
    Xtr = Xtr / max(Xtr[0], 1e-30)
    t2 = We2[0] * p2["h_FC"] * p2["epsilon"] / p2["u_Darcy"]
    z2 = t2 * p2["v_FC"] * 100                                  # same for washing step 2 (3D apparatus view)
    rest = dict(W1=rest_W1, W2=rest_W2)
    return dict(W=Wg, X1=X1, X2=X2, target=target, WR_crit1=wrc1, WR1=WR1, WR2=WR2, X1_end=float(X1e[0]),
                X2_end=float(X2e), X1_abs=float(X1e[0]) * p1["X_0"], X2_abs=float(X2e) * p1["X_0"],
                X_0=p1["X_0"], f1=f1, f2=f2, ka1=ka1, ka2=ka2, Q_pore=p1["Q_pore"] * 6e7,
                Q_WL1=WR1 * p1["Q_pore"] * 6e7, Q_WL2=WR2 * p2["Q_pore"] * 6e7,
                z_wash1=z1, z_wash2=z2, X2_tracer=Xtr, rest=rest, gamma=gam, b_D=bD, L_seg=L_seg, pre1=p1)
