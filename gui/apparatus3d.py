"""3D apparatus view of the CVSF (three.js, embedded as HTML component).

Geometry of glass modules, couplings, nozzles, frit, end piece and screw is taken from the Fusion 360 model
CVSF_FWWD_F3D.f3d (tessellated display mesh, units cm) and scaled to the design inputs of the simulation:

    glass module (double-walled):    length L_f + 5.0 cm (CAD: 11.0 cm with a 6 cm frit)
        inner tube                   bore D_i, wall 1 mm
        outer jacket                 OD 41 mm, wall 1 mm, conical shoulders of 0.9 cm to the necks (OD 32 mm)
        frit                         starts 2.54 cm after the module start, length L_f, width b, bottom of the bore
    couplings between modules        2 halves, OD 40 mm, total length L_T - 5.0 cm (CAD: 4.4 cm -> L_T = 9.4 cm)
    nozzles (GL 14)                  OD 13.8 mm; top nozzles 1.04 ... 3.25 cm above the axis, vacuum outlet below
                                     the frit centre down to -3.95 cm
        F module                     feed inlet at the frit start, two top nozzles (frit centre, + 2.4 cm)
        W modules                    top nozzles at frit start + 0.6 cm and at the frit centre
        D module                     top nozzles at frit start + 0.6 / centre / + 2.4 cm
    end piece                        glass, 7.0 cm, discharge below at 3.5 cm, screw ends 0.75 cm before it
    screw (CAD)                      right-handed, d_o = 25 mm, d_i = 16 mm, P = 11 mm, w = 1 mm (screw a)

The screw in the view uses the screw design of the simulation (d_i, P, N, w) with the handedness of the CAD
(right-handed). A right-handed screw conveys from the feed (left) to the discharge (right) when it turns
counter-clockwise viewed from the feed/drive end; the animation uses exactly this sense of rotation and the real
rotational speed n_screw.

The particle motion is a qualitative visualisation of the model: axial velocity v_p,ax = P n / theta_m, end of cake
formation z_S1, cake height h_c(z), wash liquid distribution and X*(WR) of both washing steps. Particles are
enlarged for visibility.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "vendor", "three")

CAD = dict(
    glass_extra=5.0,        # glass length - L_f
    frit_start=2.54,        # frit start after module start
    r_jacket=2.05, r_jacket_in=1.95, r_neck=1.6, shoulder=0.9,
    r_coupling=2.0, coupling_ref=4.4, LT_ref=9.4,
    r_nozzle=0.69, r_nozzle_in=0.5, nozzle_top=3.25, nozzle_bottom=-3.95,
    end_piece=7.0, discharge_rel=3.5, screw_end_gap=0.75, lead_in=2.2,
    screw_cad=dict(d_o=0.025, d_i=0.016, P=0.011, w=0.001, hand="right"),
)

CONFIGS = {
    "F": ["F"],
    "F-W": ["F", "W"],
    "F-W-W": ["F", "W", "W"],
    "F-W-W-D": ["F", "W", "W", "D"],
}


def _segment_height(R, A):
    """height h of a circular segment (radius R) with area A"""
    A = min(max(A, 0.0), math.pi * R * R * 0.999)
    lo, hi = 0.0, 2 * R
    for _ in range(60):
        h = 0.5 * (lo + hi)
        a = R * R * math.acos((R - h) / R) - (R - h) * math.sqrt(max(2 * R * h - h * h, 0.0))
        lo, hi = (h, hi) if a < A else (lo, h)
    return 0.5 * (lo + hi)


def scene_data(R, W=None, config="F-W-W-D", wash_on=True):
    inp, K, res = R["inp"], R["kpi"], R["res"]
    mods = CONFIGS.get(config, CONFIGS["F-W-W-D"])
    Lf, LT = float(inp.L_f), float(inp.L_T)
    glass = Lf + CAD["glass_extra"]
    coupling = max(LT - CAD["glass_extra"], 0.6)
    pitch = glass + coupling
    Rb = 50.0 * inp.D_i                              # bore radius / cm
    r_core = 50.0 * inp.d_i
    r_screw = min(1.25, Rb - 0.01)
    # scene x of z = 0 (start of the frit of F1) -> first glass module starts at lead_in
    x_mod0 = CAD["lead_in"]
    z0 = x_mod0 + CAD["frit_start"]
    modules, counts = [], {}
    for i, t in enumerate(mods):
        counts[t] = counts.get(t, 0) + 1
        x0 = x_mod0 + i * pitch
        modules.append(dict(type=t, name=f"{t}{counts[t]}", x0=x0, frit0=x0 + CAD["frit_start"], frit1=x0 + CAD["frit_start"] + Lf))
    x_end = x_mod0 + len(mods) * pitch               # start of the end piece
    x_dis = x_end + CAD["discharge_rel"]
    screw = dict(x0=-0.23, x1=x_end - CAD["screw_end_gap"], r_core=r_core, r_out=r_screw, P=100 * inp.P,
                 N=int(inp.N), w=100 * inp.w, hand="right")
    # --- operating point
    th = float(K["theta_m"]); v_ax = float(K["v_ax"]) * 100      # cm/s
    zS1 = float(K["z_S1"]); finished = bool(K["finished"])
    hc_end = 100 * float(K["h_c"])
    zc = np.asarray(R["hc_z"], float); hc = 100 * np.asarray(R["hc"], float)
    # suspension level at the feed from the filling degree (DIN 15261: suspension volume / free screw volume)
    A_free = math.pi * (Rb ** 2 - r_core ** 2)
    h0 = min(_segment_height(Rb, float(K["alpha"]) * A_free), 1.9 * Rb)
    h0 = max(h0, hc_end * 1.3)
    zS_vis = min(zS1, (len(mods) * pitch - CAD["frit_start"]))
    zg = np.round(np.arange(-CAD["frit_start"] - CAD["lead_in"], x_end + CAD["end_piece"] - z0 + 0.05, 0.05), 3)
    cake = np.interp(zg, zc, hc, left=0.0, right=hc_end)
    cake = np.where(zg > zS_vis, hc_end, cake)
    top = np.where(zg <= 0, h0, np.where(zg < zS_vis, cake + (h0 - hc_end) * np.clip(1 - zg / max(zS_vis, 1e-6), 0, 1),
                                         cake))
    top = np.maximum(top, cake)
    # --- composition of the pore liquid (fractions mother liquor / wash liquid 1 / ethanol)
    ML = np.ones_like(zg); RW = np.zeros_like(zg)
    wash = dict(on=False, msg="")
    wmods = [m for m in modules if m["type"] == "W"]
    if wash_on and W is not None and finished and wmods:
        Wg = np.asarray(W["W"]); X1 = np.asarray(W["X1"]); X2 = np.asarray(W["X2"])
        WR1, WR2 = float(W["WR1"]), float(W["WR2"])
        X1e = float(W["X1_end"])
        X20 = max(float(X2[0]), 1e-12)
        rest1, rest2 = float(W["rest"]["W1"]), float(W["rest"]["W2"])
        zw1 = float(W["z_wash1"]); zw2 = float(W.get("z_wash2", zw1 * WR2 / max(WR1, 1e-9)))
        st = []
        m1 = wmods[0]
        d1 = m1["frit1"] - min(rest1, Lf)                       # dosing W1: rest_W1 of the frit remaining
        L1 = min(zw1, m1["frit1"] - d1)
        st.append(dict(name=m1["name"], x_dose=d1, x_end=d1 + L1, need=zw1, avail=m1["frit1"] - d1, WR=WR1,
                       liquid="EtOH/water (red tracer)", color="red"))
        xg = zg + z0
        # wash ratio received along the frit: linear from the dosing point; if the wash liquid needs more frit
        # length than available, only the corresponding fraction of WR is applied
        f1 = np.clip((np.minimum(xg, m1["frit1"]) - d1) / max(zw1, 1e-6), 0, 1)
        ML = np.where(xg >= d1, np.interp(f1 * WR1, Wg, X1), 1.0)
        RW = 1.0 - ML
        st[0]["WR_applied"] = float(WR1 * min(1.0, (m1["frit1"] - d1) / max(zw1, 1e-6)))
        if len(wmods) > 1:
            m2 = wmods[1]
            d2 = m2["frit1"] - min(rest2, Lf)
            L2 = min(zw2, m2["frit1"] - d2)
            st.append(dict(name=m2["name"], x_dose=d2, x_end=d2 + L2, need=zw2, avail=m2["frit1"] - d2, WR=WR2,
                           liquid="ethanol (colourless)", color="clear",
                           WR_applied=float(WR2 * min(1.0, (m2["frit1"] - d2) / max(zw2, 1e-6)))))
            f2 = np.clip((np.minimum(xg, m2["frit1"]) - d2) / max(zw2, 1e-6), 0, 1)
            g = np.interp(f2 * WR2, Wg, X2) / X20                   # displacement curve of washing step 2
            ML_in = float(np.interp(d2, xg, ML))
            ML = np.where(xg >= d2, ML_in * g, ML)
            gtr = np.interp(f2 * WR2, Wg, np.asarray(W["X2_tracer"])) if "X2_tracer" in W else g
            RW = np.where(xg >= d2, (1 - ML_in) * gtr, RW)
        wash = dict(on=True, steps=st, X1_end=X1e, X2_end=float(W["X2_end"]) if len(wmods) > 1 else None)
    elif wash_on and wmods and not finished:
        wash["msg"] = "Washing not shown: cake formation is not completed on the frit of F1 (z_S1 > L_f)."
    elif wash_on and wmods and W is None:
        wash["msg"] = "Washing not shown: washing model not evaluated."
    ML = np.clip(ML, 0, 1); RW = np.clip(RW, 0, 1 - ML)
    # thin the profile arrays (0.05 cm grid)
    prof = dict(z=zg.tolist(), cake=np.round(cake, 4).tolist(), top=np.round(top, 4).tolist(),
                ML=np.round(ML, 5).tolist(), RW=np.round(RW, 5).tolist())
    tau = dict(frit=Lf / v_ax / 60 if v_ax > 0 else None, module=pitch / v_ax / 60 if v_ax > 0 else None,
               total=(x_dis - z0) / v_ax / 60 if v_ax > 0 else None)
    d50 = float(K["d50"])
    data = dict(
        geom=dict(Rb=Rb, r_tube=Rb + 0.1, b=100 * inp.b, Lf=Lf, LT=LT, glass=glass, coupling=coupling, pitch=pitch,
                  z0=z0, x_end=x_end, x_dis=x_dis, **{k: v for k, v in CAD.items() if not isinstance(v, dict)}),
        modules=modules, screw=screw,
        op=dict(n=float(inp.n), v_ax=v_ax, theta=th, zS1=zS1, finished=finished, hc=hc_end, alpha=float(K["alpha"]),
                h0=h0, Q=float(inp.Q), dp=float(inp.dp), tau=tau, d50=d50,
                phi_end=float(K["phi_end"]) if finished else None, P_mm=1e3 * inp.P, N=int(inp.N)),
        prof=prof, wash=wash, config=config,
        particle=dict(r_vis=float(np.clip(0.045 + d50 * 1.6e-4, 0.05, 0.11))),
    )
    return data


def _vendor(name):
    with open(os.path.join(VENDOR, name), encoding="utf-8") as fh:
        return fh.read()


_JS_CACHE = {}


def html(data, height=700):
    if not _JS_CACHE:
        _JS_CACHE["three"] = _vendor("three.min.js")
        _JS_CACHE["orbit"] = _vendor("OrbitControls.js")
        _JS_CACHE["room"] = _vendor("RoomEnvironment.js")
        with open(os.path.join(HERE, "apparatus3d.js"), encoding="utf-8") as fh:
            _JS_CACHE["app"] = fh.read()
        with open(os.path.join(HERE, "apparatus3d.css"), encoding="utf-8") as fh:
            _JS_CACHE["css"] = fh.read()
    J = _JS_CACHE
    payload = json.dumps(data, separators=(",", ":"), default=float)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{J['css']}</style></head>
<body><div id="wrap" style="height:{height}px">
<canvas id="c"></canvas>
<div id="hud"></div><div id="legend"></div><div id="msg"></div>
<div id="strip"><canvas id="stripc"></canvas></div>
<div id="bar"></div>
</div>
<script>{J['three']}</script>
<script>{J['orbit']}</script>
<script>{J['room']}</script>
<script>window.CVSF_DATA = {payload};</script>
<script>{J['app']}</script>
</body></html>"""
