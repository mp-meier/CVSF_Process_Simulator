"""Uncertainties of the reference parameter set for the Bayesian calibration of the GUI (gui/calibration.py).

Calibrates mu_s, a, b, A, and B with the experimental data of the filtration study (12 RTD values, 8 filter cakes,
12 residual moistures at OP 1) and weakly informative priors. The measurement/model uncertainties are set to the
root-mean-square residuals of a first pass (empirical Bayes); the posterior standard deviations of the second pass are
stored as uncertainties of the reference set (gui/data/calibration_reference.json). The posterior means are consistent
with the least-squares fits of the filtration study but not identical (different weighting of the data)."""
import os, sys, json
import numpy as np
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "gui"))
import calibration as C  # noqa: E402

df = C.reference_dataset()
ref = C.reference_set()
wide = {"mu_s": (ref["params"]["mu_s"], 1.0), "a_rtd": (ref["params"]["a_rtd"], 1.0),
        "b_rtd": (ref["params"]["b_rtd"], 1.0), "A": (ref["params"]["A"], 20.0), "B": (ref["params"]["B"], 20.0)}
noise = dict(theta_rel=0.05, eps_rel=0.05, alpha_log=0.42, phi_abs=0.02)
for it in range(2):
    r = C.calibrate(df, ref, prior_override=wide, noise=noise, progress=lambda f, t: print(f"  {100*f:5.1f} % {t}"))
    s1, s2, s3 = r["stages"]["theta"], r["stages"]["A"], r["stages"]["B"]
    new = dict(theta_rel=float(np.sqrt(np.mean(((s1["pred_post"] - s1["y"]) / s1["y"]) ** 2))),
               eps_rel=float(np.sqrt(np.mean(((s2["eps_post"] - s2["y_eps"]) / s2["y_eps"]) ** 2))),
               alpha_log=float(np.sqrt(np.mean((np.log(s2["alpha_post"]) - np.log(s2["y_alpha"])) ** 2))),
               phi_abs=float(np.sqrt(np.mean((s3["pred_post"] - s3["y"]) ** 2))))
    print("pass", it + 1, "posterior", {k: round(v, 4) for k, v in r["post"].items()},
          "sd", {k: round(v, 4) for k, v in r["post_sd"].items()}, "RMS residuals", {k: round(v, 4) for k, v in new.items()})
    if it == 0:
        noise = new
out = dict(post_mean=r["post"], std=r["post_sd"], noise=noise, corr_theta=s1["corr"],
           q2=dict(theta=s1["q2"], eps=s2["q2_eps"], alpha=s2["q2_alpha"], phi=s3["q2"]),
           reference_fit=ref["params"], n=dict(theta=s1["n"], cakes=s2["n"], phi=s3["n"]))
json.dump(out, open(os.path.join(_ROOT, "gui", "data", "calibration_reference.json"), "w"), indent=1, default=float)
print(json.dumps({k: out[k] for k in ("std", "noise", "q2")}, indent=1, default=float))
