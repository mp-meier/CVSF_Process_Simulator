"""Smoke test of the CVSF Process Simulator with the current model version (used by the GitHub Action before a
model update is taken over): model functions, washing model, and the three modes of the interface."""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "gui"))


def main():
    import engine as E
    ok = True
    for name in E.EXAMPLES:
        inp = E.Inputs()
        inp.shape, inp.psd_results, inp.psd_descriptors = E.example_paths(name)
        inp.psd_mode = "file"
        r = E.run_filtration(inp)
        k = r["kpi"]
        good = np.isfinite(k["z_S1"]) and 0 < k["eps"] < 1 and (not k["finished"] or 0 < k["phi_end"] < 1)
        print(f"filtration  {name:28s} z_S1 = {k['z_S1']:.3f} cm  phi_RM = {100 * k['phi_end']:.2f} %  "
              f"{'ok' if good else 'FAILED'}")
        ok &= bool(good)
    inp = E.Inputs()
    inp.shape, inp.psd_results, inp.psd_descriptors = E.example_paths(list(E.EXAMPLES)[0])
    inp.psd_mode = "file"
    w = E.run_washing(E.run_filtration(inp))
    good = np.isfinite(w["X1_end"]) and 0 <= w["X1_end"] <= 1
    print(f"washing     WR_crit,1 = {w['WR_crit1']:.3f}  {'ok' if good else 'FAILED'}")
    ok &= bool(good)
    import calibration as C
    import design as G
    import copy
    s = copy.deepcopy(C.reference_set())
    s["std"] = {k: 5 * v for k, v in s["std"].items()}; s["corr_theta"] = None     # new material system
    C.apply_set(inp, s)
    kp = E.run_filtration(inp)["kpi"]
    y0, Jt, keep, fin = G.target_jacobian(inp)
    cands, info = G.target_candidates(s, inp, kp)
    cands = G.relevance(cands, inp, kp)
    S = G.covariance(s)
    ci0 = G._ci(S, y0, Jt, keep)
    fl = G.floors(s)
    sel, hist, reached = G.target_plan(cands, S, y0, Jt, keep, {k: max(0.5 * v, fl[k]) for k, v in ci0.items()})
    good = len(sel) > 0 and all(hist[-1][k] <= ci0[k] + 1e-9 for k in ci0)
    print(f"target plan {len(sel)} experiments, goal {'reached' if reached else 'not reached'}  {'ok' if good else 'FAILED'}")
    ok &= bool(good)
    from streamlit.testing.v1 import AppTest
    for mode in ("Simulation", "Calibration", "Experiment design"):
        at = AppTest.from_file(os.path.join(ROOT, "gui", "app.py"), default_timeout=600)
        at.session_state["mode"] = mode
        at.run()
        if mode == "Simulation":                              # experiments for this prediction + dark mode
            [b for b in at.button if "Plan experiments for this simulation" in b.label][0].click().run(timeout=600)
            at.session_state["dark_mode"] = not bool(at.session_state["dark_mode"])
            at.run()
            at.session_state["dark_mode"] = not bool(at.session_state["dark_mode"])
            at.run()
        errs = [str(e.value)[:200] for e in at.exception] + [e.value for e in at.error]
        print(f"interface   {mode:18s} {'ok' if not errs else 'FAILED ' + str(errs)}")
        ok &= not errs
    print("SELFTEST", "PASSED" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
