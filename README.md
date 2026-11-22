# CVSF Process Simulator

Software for the mechanistic process model of the continuous vacuum screw filter (CVSF): simulation of cake
filtration, gas deliquoring, evaporation, and two-stage washing; experiment database with continuous Bayesian
calibration; Bayesian experimental design. **Private repository** – the model code itself is maintained and published
separately in [`mp-meier/CVSF_Model`](https://github.com/mp-meier/CVSF_Model) (citable version with the filtration and
washing studies).

> **User manual:** `docs/CVSF_Process_Simulator_Manual.pdf` (installation, modes Simulation, Calibration, and
> Experiment design, recommended procedure for continuous model improvement). Guide for entering experimental data:
> `docs/Guide_Experimental_Data_Template.pdf`. Both are also available as downloads in the interface.

## 1. Quick start

**Windows setup package (recommended):** run `python tools/build_windows_setup.py`; the folder
`dist/CVSF_Process_Simulator_<version>_Windows/` contains `Setup_CVSF_Process_Simulator.bat`, an uninstaller,
`LIESMICH.txt`, the documentation (manual, guide, Excel template, README) and the software and model state as git
bundles. The setup installs into `%LOCALAPPDATA%\Programs\CVSF Process Simulator` (program files, own Python
environment `env`), creates the desktop and start menu shortcuts without PowerShell (pylnk3), and keeps the user data
in `%LOCALAPPDATA%\CVSF_Process_Simulator`. Requirements: Python (e.g. Miniforge) and Git for Windows.

**From GitHub:**

1. Get the code **including the model** (git submodule):
   `git clone --recurse-submodules https://github.com/mp-meier/CVSF_Process_Simulator.git`
   (access to both private repositories required; a ZIP download from GitHub does not contain the model code).
2. Windows: double-click `install_desktop_app.bat` (Python, e.g. Miniforge, and git required; missing packages and a
   missing model folder are fetched), then start *CVSF Process Simulator* from the desktop icon. Alternatively:
   `pip install -r requirements.txt` and `streamlit run gui/app.py`.
3. Read `docs/CVSF_Process_Simulator_Manual.pdf`.

## 2. Structure and link to the model repository

```
cvsf_model/     model code = git submodule of mp-meier/CVSF_Model (model/, model_washing/, scripts/, out/, fig/),
                pinned to a released model version (tag V01, V02, ...)
gui/            interface (app.py, Streamlit), interface layer to the model (engine.py), desktop launcher (launcher.pyw),
                calibration and experiment database (calibration.py, database.py, calib_page.py), experiment design
                (design.py, design_page.py), reference uncertainties (data/calibration_reference.json)
tools/          model_update.py (model version, update), selftest.py (test of software + model),
                calib_reference.py (uncertainties of the reference parameter set)
docs/           user manual and guide for the experimental data (PDF/HTML, build scripts, screenshots in docs/img/),
                Excel template of the experimental data
assets/         logo and icons (gen_logo.py)
.github/workflows/update-model.yml   automatic take-over of new model versions
install_desktop_app.py/.bat, start_gui.bat/.sh, requirements.txt, .streamlit/config.toml
```

The software contains no copy of the model: `gui/engine.py` imports the model functions directly from
`cvsf_model/scripts/` (`cvsf.py`, `washing.py`). The model is changed only in `mp-meier/CVSF_Model`; a new model version
is released there as a git tag (`V02`, …).

**How model changes reach the software**

1. *GitHub (automatic):* the action `Update model version` runs daily (and on demand: *Actions → Update model version →
   Run workflow*). If `CVSF_Model` has a newer tag than the pinned one, it switches the submodule to that tag, runs
   `tools/selftest.py` (model functions, washing model, and the three modes of the interface), and commits the new
   model version only if the test passes. If the test fails, the software stays on the previous model version and
   GitHub reports the failed run by e-mail.
2. *Local installation (automatic):* the desktop launcher and the start scripts run `tools/model_update.py --auto`
   at every start, i.e. a `git pull` of the tested state of the software including its model version (silent, skipped
   offline; disable by creating the file `no_auto_update` in `%LOCALAPPDATA%\CVSF_Process_Simulator`).
3. *Interface:* tab *Model & references* shows the model version (tag, commit), checks for updates, and updates
   software and model (restart afterwards). The header shows the active model version.
4. *Manually:* `python tools/model_update.py` (status), `--update` (tested state), `--latest-model` (newest model
   tag, not yet tested), `--tag V01` (specific version).

Only released tags are taken over, so unfinished model changes on `main` of `CVSF_Model` do not reach the software.

**One-time setup on GitHub (as long as CVSF_Model is private):** create a fine-grained personal access token
(GitHub → *Settings → Developer settings → Fine-grained tokens*) with access to `mp-meier/CVSF_Model` only and the
permission *Contents: Read-only*; store it in this repository under *Settings → Secrets and variables → Actions* as
`MODEL_REPO_TOKEN`. After the publication of the model repository, the token is no longer required.

## 3. Interface and desktop application

The folder `gui/` contains an interactive interface for the complete model (filtration module and two-stage washing).
Start: double-click `start_gui.bat` (Windows) or `./start_gui.sh` (Linux/macOS), or manually

```
pip install -r requirements.txt
streamlit run gui/app.py
```

The interface opens in the web browser (local, http://localhost:8501; no data leave the computer).

**Desktop application.** `install_desktop_app.bat` (Windows; alternatively `python install_desktop_app.py` in the
Miniforge Prompt with the desired environment activated) installs missing packages and creates the shortcut
"CVSF Process Simulator" with the CVSF icon on the desktop and in the start menu. The shortcut starts
`gui/launcher.pyw`: the model server runs in the background without a console window, and the interface opens in its
own application window (Microsoft Edge or Google Chrome in app mode, no address bar). Closing the window stops the
server. The shortcut is bound to the Python environment used for the installation; after moving the package folder,
run the installation again. `python install_desktop_app.py --remove` removes the shortcuts. Logo and icons:
`assets/cvsf_icon.svg` (emblem), `assets/cvsf_icon_text.svg` and `assets/cvsf.ico` (desktop icon with lettering), `assets/cvsf_wordmark.svg` (generated by `assets/gen_logo.py`).

- **Inputs (sidebar):** particle system (shape; PSD as Excel file of the dynamic image analysis via example data,
  upload, or local path; alternatively log-normal PSD from d50,3 and σg, or from the characteristic diameters d10,3,
  d50,3, d90,3; sphericity as preset, effective value, or geometric value plus agglomeration degree), operating point
  (Q_susp, w_solid, n_screw or target filling degree, Δp, ϑ_susp), apparatus and screw design (current or previous
  module generation, screws (a)-(c), or custom), air drawn through the module, and model parameters (A, B, θm
  correlation). Input sets can be saved and loaded as JSON.
- **Outputs:** key figures (z_S1, φ_RM at the module outlet, θm, filling degree, ε, α_FC, minimum Δp); schematic of
  the filtration module in true dimensions over the axial coordinate z with filter cake, suspension, and z_S1; axial
  profiles of φ_RM(z) and h_c(z); PSD and filter cake properties; design studies (z_S1 over Δp, Q_susp at constant
  filling degree with and without particle backslip, ϑ_susp) and an operating window z_S1(Q_susp, n_screw) with
  the limit z_S1 = L_f and filling degree isolines; two-stage washing (wash curves X*(WR) of both washing steps,
  WR_crit,1, washing liquid flow rates, CVSF configuration); export of results (JSON) and profiles (CSV).
- **3D apparatus (tab):** animated three-dimensional view of the CVSF (three.js, runs locally in the application
  window; no internet connection needed). Details in section 3.1.
- `gui/engine.py` is the interface-independent layer between the GUI and the model code (`cvsf_model/scripts/cvsf.py`,
  `cvsf_model/scripts/washing.py`); it can also be used from Python scripts (`engine.Inputs`, `engine.run_filtration`,
  `engine.studies`, `engine.operating_window`, `engine.run_washing`).
- Required format of the PSD files: `PSDResults_*.xlsx` (and, for cuboid and needle-shaped particles,
  `ImageDescriptors_*.xlsx`) as exported by the dynamic image analysis, cf. the examples in `cvsf_model/model/PSDs/`.
- With characteristic diameters, a log-normal Q3 distribution is assumed; with only one of d10,3 or d90,3 given,
  σg is calculated from d50,3 and this value. The washing model is evaluated only if cake formation is completed on
  the filter medium (z_S1 ≤ L_f). Its correlations are based on bipyramidal particles; results for other particle
  shapes are extrapolations (a note is displayed).
- The GUI calls the same functions as the scripts: for an example PSD file with the previous module generation and
  the default operating point (OP 1), it returns exactly the value of the validation for this single PSD measurement
  (e.g. bipyramidal 355-560 µm: z_S1 = 0.360 cm, φ_RM = 17.79 %); `cvsf_model/scripts/verify_filtration_reference.py` reports the mean
  over all PSD measurements of each particle shape.

### 3.1 3D apparatus

The tab *3D apparatus* shows the CVSF as a running apparatus. It is configured from the inputs of the sidebar and
from the module configuration selected in the tab (F, F-W, F-W-W, F-W-W-D; F = filtration and deliquoring module with
feed, W = washing module, D = drying module, followed by the end piece with the discharge).

- **Geometry, true to scale:** taken from the Fusion 360 model of the CVSF (`CVSF_FWWD_F3D.f3d`, tessellated display
  mesh) and scaled to the design inputs. Double-walled borosilicate glass modules (inner tube with the bore D_i,
  outer jacket OD 41 mm with conical shoulders, necks OD 32 mm), frit at the bottom of the bore (starts 2.54 cm after
  the module start, length L_f, developed width b), couplings between the modules, GL 14 nozzles (feed inlet at the
  frit start of F1, dosing nozzles at the frit start and the frit centre of the washing modules, vacuum outlet below
  the frit centre), end piece with discharge, and drive. The glass module is L_f + 5 cm long; the couplings fill the
  remaining distance to the next module (pitch L_f + L_T). The CAD model has 11 cm glass modules with 4.4 cm couplings
  (pitch 15.4 cm, i.e. L_T = 9.4 cm); with the model value L_T = 8 cm, the couplings are drawn 3.0 cm long.
- **Screw:** white PTFE, built from the screw design of the simulation (d_i, P, number of flights N, flight width w;
  d_o = 25 mm). The handedness is taken from the CAD model (right-handed). The screw turns at the real rotational
  speed n_screw, counter-clockwise viewed from the feed/drive end, i.e. in the direction in which a right-handed
  screw conveys from the feed (left) to the discharge (right).
- **Particles and residence time:** the particles move with the axial particle velocity of the model,
  v_p,ax = P · n_screw / θm (slower than the flights for θm > 1), with a small random spread as a qualitative picture
  of axial dispersion. Up to z_S1, they are partly suspended in the supernatant suspension (level from the filling
  degree) and settle into the growing filter cake (h_c(z) of the model); after z_S1, they form the deliquored filter
  cake. At the discharge, they fall out of the apparatus. A gold tracer particle moves with the mean velocity and shows
  its position (z, module) and residence time; the info panel lists the mean residence times on a frit, per module,
  and from the feed to the discharge. The strip at the bottom shows the apparatus, z_S1, the pore liquid composition
  along z, and the tracer position.
- **Washing (colours):** particles and filter cake are coloured by the composition of the pore liquid: blue = mother
  liquor (impurity), red = wash liquid 1 (ethanol/water with a red optical tracer), colourless/white = wash liquid 2
  (ethanol); mixed colours correspond to mixtures. The composition follows from the washing model (tab *Washing*; if
  not run there, with its default parameters): in washing step 1, the wash ratio increases linearly from the dosing
  point (frit centre, 3 cm of frit remaining) over the frit length needed for WR₁, and the mother liquor fraction is
  X*(WR) of step 1. In washing step 2 (dosing at the frit start), the remaining mother liquor follows X*(WR) of
  step 2, and wash liquid 1 is displaced according to the ADE of step 2 with wash liquid 1 initially distributed
  uniformly in the pores (flowing and stagnant pore volume). If the wash liquid needs more frit length than available
  after the dosing point, only the corresponding fraction of WR is applied and a note is displayed. Dosing drops,
  the supernatant wash liquid on the cake, and filtrate drops below the frits are symbolic.
- **Controls:** play/pause; speed 1× (real time), 10×, 60×, 300× (above about two revolutions per second, the screw
  rotation is drawn slowed down, the conveying velocities remain true in time); reset; release tracer; views overview,
  close-ups of every module (F1, W1, W2, D1) and of the discharge, follow tracer; ◀ ▶ buttons, arrow keys or right
  mouse button move the view to the left and right; section view (front half of glass and couplings cut away); info panels on/off.
  Mouse: drag to rotate, scroll to zoom, right-drag to pan.
- **Limits:** the view is a qualitative representation of the model results. Particles are enlarged; the cake surface
  is drawn flat; the drying module D1 is shown without a model of its own (drying follows with model version V02).
  Files: `gui/apparatus3d.py` (scene data from the model results, CAD dimensions), `gui/apparatus3d.js` and
  `gui/apparatus3d.css` (scene and animation), `gui/vendor/three/` (three.js r147, MIT licence).

### 3.2 Experiments for this prediction

The tab *Experiments for this prediction* (mode Simulation) answers for the current inputs: which experiments, how
many and at which parameters are needed so that the prediction of θm, z_S1 and φ_RM comes as close as possible to
reality. Procedure (targeted Bayesian experimental design, `gui/design.py`: `target_jacobian`, `target_candidates`,
`relevance`, `target_plan`):

1. Sensitivities of the simulated quantities to the model parameters p = (μs, a, b, A, B) at the inputs (finite
   differences of the full simulation); with the covariance Σ of the selected model state, the parameter-related
   prediction uncertainty (95 % half-width) follows.
2. Candidate experiments around the simulated point: RTD measurements (simulated and standard screws, n_screw 1–5 rpm
   and the simulated speed), filter cake tests (simulated particle shape, d50,3 from half to twice the simulated value,
   Ag3 ± 0.15), CVSF runs (Q_susp ± 30 %, Δp ± 20 mbar). The measurement uncertainty of a candidate is increased with
   its distance d to the simulated conditions, R_eff = R (1 + 3 d²) (relevance for this prediction).
3. Sequential Bayesian optimization: each step selects the experiment with the largest expected reduction of the
   prediction variance of the quantities whose goal is not reached yet (per effort); Σ is updated; selecting a
   candidate again means a replicate. Goal: reduction of the 95 % half-width by the chosen percentage, but not below
   ± 1 % (θm), ± 2 % (z_S1), ± 0.5 pp (φ_RM) or one third of the 95 % scatter of a single measurement.
4. Result: number of experiments, plan table (type, parameters, replicates, quantity to measure, which prediction it
   mainly improves), uncertainty vs. number of experiments, Excel template of the plan, and a recommended validation
   at exactly the simulated inputs. For a well-calibrated system (e.g. the reference), the result can be that no
   further calibration experiments are needed.

### 3.3 Dark mode

Switch *Dark mode* below the logo in the sidebar; the setting is stored in `%LOCALAPPDATA%\CVSF_Process_Simulator\config.json`
and used at the next start. Streamlit theme, custom elements and all charts are adapted (`gui/theme.py`).

## 4. Calibration mode: experiment database and continuous Bayesian calibration

The GUI has three modes (switch at the top of the sidebar; the third mode, Experiment design, is described in section 5):

- **Simulation** (predictive): inputs → model outputs along the apparatus (section 3), with the selected
  **parameter set** (★ = current model state of the material system). If the set contains uncertainties, the 95 %
  interval of the residual moisture resulting from the uncertainty of B is shown.
- **Calibration**: experimental data of completed CVSF runs are collected in an experiment database, and the model is
  recalibrated with all active data (`gui/database.py`, `gui/calibration.py`, `gui/calib_page.py`). Tabs:
  1. **Add data** – Excel template (`CVSF_experimental_data_template.xlsx`: sheets Instructions, Experiments,
     Example, Material system) and the guide with screenshots (`docs/Guide_Experimental_Data_Template.pdf`) as
     downloads; upload of the filled template and of the PSD files; editable table with status per row (usable
     for which stage, missing information, plausibility/unit check); dataset information (material system, name,
     operator, date, description); *Add dataset to the experiment database* (PSD files are copied into the database).
  2. **Experiment database** – all datasets added since model version V01, each dataset and each experiment with an
     *active* checkbox and a reason for deactivation; only active experiments of active datasets enter the
     calibration; change log (time, user, action, reason); export and deletion of datasets; configurable storage
     folder (e.g. a shared network folder of the working group).
  3. **Recalibrate model** – status of the current model state (up to date / outdated), Bayesian recalibration with
     all active experiments of the material system, results, and *Adopt as current model state*.
  4. **Model states & parameter sets** – history of all model states with provenance; use in simulation, set as
     current, export/import (JSON).

| Stage | Parameters | Experimental data |
|---|---|---|
| 1 | μs, a, b (θm correlation, Fit 1) | dimensionless mean solids residence time θm (RTD); screw, n_screw |
| 2 | A (sphericity correction, Fit F1) | filter cake porosity and/or specific cake resistance; PSD (file, or d-values + Ag3) |
| 3 | B (equilibrium saturation factor, Fit F2) | residual moisture at the outlet of the filtration module; PSD; operating point |

- **Continuous improvement with retroactive exclusion:** every recalibration starts again from the reference
  parameter set of the filtration study (prior; for other material systems with 5 × the uncertainty) and uses *all
  currently active* experiments of the material system. Deactivating a dataset or experiment therefore removes its
  influence completely at the next recalibration. The 33 data of the filtration study are contained in the
  reference set and are not stored in the database again (no double counting).
- **Model states** are versioned parameter sets with provenance (datasets, experiments, data fingerprint, prior,
  user); a new model state becomes the current model only after the results have been checked and adopted.
- **Bayesian method:** Gaussian likelihood (relative for θm and ε, logarithmic for α_FC, absolute for φ_RM);
  posterior of stage 1 by adaptive Metropolis MCMC, stages 2 and 3 on a parameter grid; in stage 3 the residual
  moisture of each experiment is evaluated with the complete filtration module on a B grid and interpolated
  (approx. 6 s per experiment); later stages use the posterior means of earlier stages; leave-one-out predictions
  (Q²_LOO); warnings if the data hardly inform a parameter.
- **Reference set:** values of Fits 1, F1, F2; uncertainties and default measurement/model scatter from
  `tools/calib_reference.py` → `gui/data/calibration_reference.json` (calibration with the 33 data of the filtration
  study and weakly informative priors: μs = 0.992, a = 0.121, b = −0.179, A = 3.09, B = 2.31; Q²_LOO = 0.93 (θm),
  0.87 (ε), 0.87 (ln α_FC), 0.58 (φ_RM); the deviations from the least-squares fits result from the different
  weighting of the data).
- **Storage** (default `%LOCALAPPDATA%\CVSF_Process_Simulator`, configurable): `experiment_database.json`,
  `experiment_files/<dataset>/`, `experiment_database_log.csv`, `current_model.json`, `parameter_sets/`.
- **Guide:** `docs/Guide_Experimental_Data_Template.pdf` (10 pages, screenshots of the template and of every step in
  the interface); rebuilt with `python docs/build_guide.py` from `docs/img/`.
- Limitations of this version: liquid density and viscosity are those of the L-alanine/water mother liquor (solid
  density and surface tension are part of the material system); the washing model is not calibrated. The reference
  results of both studies are not affected.

## 5. Experiment design mode (Bayesian experimental design)

The third mode of the GUI, **Experiment design** (`gui/design.py`, `gui/design_page.py`), plans the experiments that
improve the current model most. Basis is the selected model state (default: current model state ★, i.e. the posterior
of the latest Bayesian calibration with all active experiments) with the covariance Σ of p = (μs, a, b, A, B).

- **Candidates:** RTD measurements (screw (a)/(b)/(c) × n_screw → θm), filter cake tests (log-normal PSD: d50,3 ×
  agglomeration degree Ag3 → ε, α_FC), and CVSF runs (grid over two of Q_susp, n_screw, Δp, ϑ_susp, w_solid at fixed
  other conditions → residual moisture at the outlet; operating points with z_S1 > L_f are excluded). Design spaces,
  particle system, setup, screw, and relative effort (cost) per experiment type are set in the interface.
- **Expected information gain** of each candidate from the linearized model (Jacobian J of the measured quantities
  with respect to p; measurement/model uncertainty R as in the calibration): EIG = ½ ln det(I + R⁻¹ J Σ Jᵀ) (D-optimal
  Bayesian design).
- **Sequential batch Bayesian optimization:** the plan of the next k experiments maximizes the acquisition function
  EIG/cost (normalized) + w · novelty; after each selection Σ is updated (Σ' = Σ − ΣJᵀ(JΣJᵀ+R)⁻¹JΣ). The novelty term
  (distance to existing and planned experiments in the normalized design space, weight w) adds exploration of regions
  without data.
- **Outputs:** expected reduction of the parameter uncertainties, plan table (rank, experiment settings, measured
  quantities, EIG, novelty, cumulative SD reduction), the plan as pre-filled Excel template of the experimental data
  (measured columns empty – fill in after the experiments and upload in the mode Calibration), and maps of the
  acquisition function with existing experiments (reference data and active database) and recommendations: CVSF runs
  (with predicted residual moisture and the limit z_S1 = L_f), RTD measurements (EIG over n_screw per screw), filter
  cake tests (EIG over d50,3 and Ag3).
- Run time: RTD and filter cake candidates < 2 s; CVSF runs approx. 0.6 s per grid point (two evaluations of the
  filtration module, parallelized with up to 4 processes).

**Procedure (step by step):**
1. Choose the current knowledge: model state ★ (default) or another parameter set.
2. Choose the experiment types and their relative effort (cost): RTD measurement (informs μs, a, b), filter cake test
   (informs A), CVSF run with residual moisture measurement (informs B).
3. Define the design spaces: n_screw range (RTD); particle shape, σg, d50,3 and Ag3 ranges (filter cake tests); two
   operating parameters as axes with ranges, grid resolution, and fixed conditions (CVSF runs).
4. Set the number of planned experiments k and the exploration weight w; click *Compute experiment plan*.
5. Evaluate the plan (expected reduction of the parameter uncertainties, ranked experiments, maps) and download it as
   Excel template (settings filled in, measured columns empty).
6. Carry out the experiments, fill in the measured values and PSD files, upload the file in the mode Calibration,
   recalibrate, check, and adopt the new model state ★.
7. Repeat: the next plan starts from the improved knowledge; the decreasing expected uncertainty reduction is a
   natural stopping criterion.

**Example (reference model state, k = 5, w = 0.3, cost RTD 1 / filter cake test 0.5 / CVSF run 2):** three filter cake
tests with strongly agglomerated particle systems (Ag3 ≈ 0.75 at different d50,3) and RTD measurements at n_screw =
5 rpm with screws (b) and (c); expected reduction of the parameter uncertainties A ≈ −39 %, a ≈ −32 %, b ≈ −14 %,
μs ≈ −5 %, B ≈ 0 %. CVSF runs are hardly selected because the residual moisture scatters by approx. 3.6 %-pts. around
the model (measurement and model deviation), so that one additional value reduces the uncertainty of B only slightly;
replicates, different particle systems, and operating points close to the deliquoring equilibrium are more effective.
The map of the CVSF runs nevertheless shows the most informative operating points.
- Limits: the EIG refers to the parameters of the existing model structure (local linearization); systematic model
  deviations are addressed by the exploration term and by checking new data in the calibration. Candidates outside
  the validated ranges are extrapolations.


## 6. Validity and limitations

Model parameters fitted for l-alanine/water (bipyramidal, cuboid, and needle-shaped particles) and ethanol/water
washing liquids; liquid density and viscosity are those of the l-alanine/water mother liquor; the washing
correlations are based on eight wash curves of bipyramidal particles. Axial profiles are model predictions (no
spatially resolved sampling in the enclosed modules). Candidates of the experiment design outside the validated ranges
are extrapolations.

## 7. Version history

- 1.2.1 (23.11.2026): 3D view – screw through the end piece up to the discharge, toned-down PTFE colour, wash
  liquid line only at the used dosing nozzle (W2 dosing exactly at the nozzle), close-ups of every module and the
  discharge, moving the view left/right (buttons, arrow keys); module D = drying module.
- 1.2 (22.11.2026): tab *Experiments for this prediction* (targeted Bayesian experimental design for the
  current simulation); dark mode; new logo.
- 1.1 (22.11.2026): Windows setup package (installation folder, own Python environment, shortcuts without
  PowerShell, uninstaller); tab *3D apparatus* – CAD-based, to-scale, animated 3D view of the CVSF with screw rotation at
  the real speed, particle transport and residence time, cake formation, and washing colours from the model.
- 1.0 (22.11.2026): interface with the modes Simulation, Calibration (experiment database, continuous Bayesian
  calibration, versioned model states), and Experiment design (Bayesian experimental design); desktop launcher and
  installer; user manual and guide; model code CVSF_Model as git submodule (V01) with automatic, tested take-over of
  new model versions.
