"""Builds the user manual of the CVSF Process Simulator (HTML and PDF) from docs/img/ and docs/img/manual/.

python docs/build_manual.py     (PDF via Playwright/Chromium: pip install playwright && playwright install chromium)
"""
import base64
import os

D = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(D)
_fig = [0]


def img(name, caption, width="100%"):
    p = os.path.join(D, "img", "manual", name)
    if not os.path.exists(p):
        p = os.path.join(D, "img", name)
    b = base64.b64encode(open(p, "rb").read()).decode()
    _fig[0] += 1
    return (f'<figure><img src="data:image/png;base64,{b}" style="width:{width}"/>'
            f'<figcaption>Figure {_fig[0]}: {caption}</figcaption></figure>')


def icon():
    b = base64.b64encode(open(os.path.join(ROOT, "assets", "cvsf_icon.svg"), "rb").read()).decode()
    return f'<img class="logo" src="data:image/svg+xml;base64,{b}"/>'


LOOP_SVG = """<svg viewBox="0 0 760 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:560px">
<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
<path d="M0,0 L10,5 L0,10 z" fill="#16395F"/></marker></defs>
<g font-family="Segoe UI, Helvetica, Arial" font-size="13" text-anchor="middle">
<rect x="20" y="20" width="200" height="74" rx="12" fill="#16395F"/><text x="120" y="50" fill="#fff" font-weight="700">1 · Simulation</text>
<text x="120" y="72" fill="#BFD3E6" font-size="11.5">predict the process</text>
<rect x="280" y="20" width="200" height="74" rx="12" fill="#1F4E79"/><text x="380" y="50" fill="#fff" font-weight="700">2 · Experiment design</text>
<text x="380" y="72" fill="#BFD3E6" font-size="11.5">plan informative experiments</text>
<rect x="540" y="20" width="200" height="74" rx="12" fill="#E6AF2D"/><text x="640" y="50" fill="#1E1E1E" font-weight="700">3 · Experiments</text>
<text x="640" y="72" fill="#1E1E1E" font-size="11.5">CVSF runs, RTD, filter cakes</text>
<rect x="540" y="156" width="200" height="74" rx="12" fill="#2E8B57"/><text x="640" y="186" fill="#fff" font-weight="700">4 · Calibration: add data</text>
<text x="640" y="208" fill="#E1F2E8" font-size="11.5">template, database, checkboxes</text>
<rect x="280" y="156" width="200" height="74" rx="12" fill="#2E8B57"/><text x="380" y="186" fill="#fff" font-weight="700">5 · Recalibrate</text>
<text x="380" y="208" fill="#E1F2E8" font-size="11.5">Bayesian, all active data</text>
<rect x="20" y="156" width="200" height="74" rx="12" fill="#16395F"/><text x="120" y="186" fill="#fff" font-weight="700">6 · Adopt model state ★</text>
<text x="120" y="208" fill="#BFD3E6" font-size="11.5">checked and versioned</text>
</g>
<g stroke="#16395F" stroke-width="2.5" fill="none" marker-end="url(#ar)">
<path d="M220,57 L276,57"/><path d="M480,57 L536,57"/><path d="M640,94 L640,152"/>
<path d="M540,193 L484,193"/><path d="M280,193 L224,193"/><path d="M120,156 L120,98"/></g></svg>"""

CSS = """
@page { size: A4; margin: 15mm 14mm 15mm 14mm; }
body { font-family: 'Segoe UI', 'Source Sans Pro', Helvetica, Arial, sans-serif; font-size: 10.3pt; color: #1E1E1E;
       line-height: 1.42; }
.title { display:flex; align-items:center; gap:18px; padding:20px 22px; border-radius:14px; color:#fff;
         background: linear-gradient(110deg, #0A1E33 0%, #16395F 60%, #1F4E79 100%); margin-bottom: 14px; }
.title .logo { width:84px; height:84px; border-radius:16px; }
.title h1 { margin:0; font-size:23pt; } .title p { margin:4px 0 0 0; color:#BFD3E6; font-size:10.5pt; }
h2 { color:#16395F; border-bottom: 2px solid #16395F; padding-bottom: 3px; margin-top: 22px; font-size: 14.5pt;
     page-break-after: avoid; }
h3 { color:#1F4E79; margin: 14px 0 4px 0; font-size: 11.5pt; page-break-after: avoid; }
.chap { page-break-before: always; }
figure { margin: 8px 0 14px 0; page-break-inside: avoid; text-align:center; }
figure img { border:1px solid #C9D2DC; border-radius:6px; }
figcaption { font-size: 8.7pt; color:#5A6573; margin-top: 3px; text-align:left; }
table { border-collapse: collapse; width:100%; font-size: 8.9pt; margin: 6px 0 12px 0; }
th { background:#16395F; color:#fff; padding:4px 6px; text-align:left; }
td { border-bottom:1px solid #DCE3EB; padding:3px 6px; vertical-align: top; }
code { background:#F3F6FA; padding:0 3px; border-radius:3px; font-size: 9pt; }
pre { background:#F3F6FA; padding:8px 10px; border-radius:6px; font-size:8.8pt; }
.box { border-left: 5px solid #1F4E79; background:#F3F6FA; padding:8px 12px; margin:10px 0; page-break-inside: avoid; }
.warn { border-left-color:#C00000; background:#FDF1F1; } .ok { border-left-color:#2E8B57; background:#F0F8F3; }
.gold { border-left-color:#E6AF2D; background:#FFF8E6; }
.two { display:flex; gap:14px; align-items:flex-start; } .two > div { flex:1; }
.toc li { margin-bottom: 1px; }
ol li, ul li { margin-bottom: 2px; }
.eq { font-family: 'Cambria Math', 'STIX Two Math', serif; font-size: 10.5pt; text-align:center; margin: 6px 0; }
"""


def build():
    H = []
    H.append(f"""<div class="title">{icon()}<div><h1>CVSF Process Simulator</h1>
<p>User manual · simulation, Bayesian calibration with the experiment database, and Bayesian experimental design<br/>
Model code CVSF_Model_Filtration_Deliquoring_Washing_V01 · M.P. Meier, M. Vogel, L. Ohm · TU Dortmund University</p></div></div>
<p>The CVSF Process Simulator is the graphical interface of the mechanistic model of the continuous vacuum screw filter
(CVSF): cake filtration, gas deliquoring, and evaporation in the filtration module as well as two-stage displacement
washing. Besides predictive simulation, it collects experimental data of completed CVSF runs, improves the model
parameters continuously by Bayesian calibration, and plans the experiments that improve the model most.</p>
<h3>Contents</h3><ol class="toc"><li>Overview: three modes and the improvement loop</li><li>Installation and start</li>
<li>Mode Simulation</li><li>Mode Calibration (experiment database and Bayesian recalibration)</li>
<li>Mode Experiment design (Bayesian experimental design)</li><li>Recommended procedure for continuous model improvement</li>
<li>Validity, limitations, files, and troubleshooting</li></ol>

<h2>1 · Overview: three modes and the improvement loop</h2>
<table><tr><th>Mode</th><th>Question</th><th>Result</th></tr>
<tr><td><b>Simulation</b></td><td>How does the CVSF behave for given particles, operating point, and apparatus?</td>
<td>end of cake formation z_S1, residual moisture along the apparatus and at the outlet, residence time, filling degree,
filter cake properties, design maps, wash curves</td></tr>
<tr><td><b>Calibration</b></td><td>How do new experimental data change the model parameters?</td>
<td>experiment database with activation checkboxes, Bayesian recalibration, versioned model states</td></tr>
<tr><td><b>Experiment design</b></td><td>Which experiment improves the model most?</td>
<td>ranked plan of the next experiments, maps of the information gain, plan as Excel template</td></tr></table>
<p>The three modes form a loop (Figure 1): the current model state is used for simulation and for planning experiments;
the measured data are added to the experiment database, the model is recalibrated with all active data, and the checked
new model state becomes the current model for simulation and the next planning round.</p>
<figure>{LOOP_SVG}<figcaption>Figure 1: Continuous model improvement with the CVSF Process Simulator.</figcaption></figure>
""")
    _fig[0] = 1
    H.append(f"""<h2>2 · Installation and start</h2>
<h3>Requirements</h3>
<p>Python ≥ 3.11 (e.g. Miniforge) with the packages of <code>requirements.txt</code> (numpy, scipy, pandas, openpyxl,
matplotlib, SALib, streamlit, plotly). Microsoft Edge or Google Chrome for the application window.</p>
<h3>Desktop application (recommended, Windows)</h3>
<ol><li>Copy the package folder <code>CVSF_Model_Filtration_Deliquoring_Washing_V01</code> to a permanent location.</li>
<li>Double-click <code>install_desktop_app.bat</code> (or, in the Miniforge Prompt with the desired environment
activated: <code>python install_desktop_app.py</code>). Missing packages are installed, and the shortcut
<b>CVSF Process Simulator</b> with the CVSF icon is created on the desktop and in the start menu.</li>
<li>Double-click the desktop icon: the model runs in the background (no console window), and the interface opens in its
own application window (Figure 2). Closing the window stops the model.</li></ol>
<p>Alternatives: <code>start_gui.bat</code> / <code>start_gui.sh</code> or <code>streamlit run gui/app.py</code> (opens in
the web browser). Everything runs locally; no data leave the computer. After moving the package folder, run the
installation again; <code>python install_desktop_app.py --remove</code> removes the shortcuts.</p>
{img("desktop_window.png", "Application window of the CVSF Process Simulator (mode Simulation).")}
<h3>Storage folder</h3>
<p>The experiment database, the change log, and the parameter sets / model states are stored in
<code>%LOCALAPPDATA%\\CVSF_Process_Simulator</code>. The folder can be changed in the mode Calibration (tab
<i>Experiment database</i>) – e.g. to a shared network folder, so that the whole working group uses the same data and
model states.</p>
""")
    H.append(f"""<h2>3 · Mode Simulation</h2>
<div class="two"><div>
<p>The sidebar (Figure 3) contains, from top to bottom:</p>
<ul><li><b>Mode</b> switch (Simulation, Calibration, Experiment design).</li>
<li><b>Model parameter set</b>: ★ marks the current model state of the material system (after the first adopted
recalibration; before, the reference set of the filtration study). Other sets can be selected for comparison.</li>
<li><b>Particle system</b>: particle shape; PSD as Excel file of the dynamic image analysis (example data, upload, or
path), as log-normal distribution (d50,3, σg), or from the characteristic diameters d10,3/d50,3/d90,3; sphericity.</li>
<li><b>Operating point</b>: Q_susp, w_solid, n_screw (or target filling degree), Δp, ϑ_susp.</li>
<li><b>Apparatus and screw design</b>: current or previous module generation, screws (a)–(c) or custom.</li>
<li><b>Air flow</b> through the module (evaporation) and <b>model parameters</b> (advanced).</li>
<li><b>Run simulation</b>. Input sets can be saved and loaded as JSON.</li></ul>
<p>The key figures (Figure 4, top) summarize the result: end of cake formation z_S1 compared with the filter length,
residual moisture at the outlet with its 95 % interval from the uncertainty of B, θm and residence times, filling
degree, porosity and cake resistance, and the minimum Δp for complete cake formation on the filter medium.</p>
</div><div style="flex:0 0 24%">{img("sim_sidebar.png", "Sidebar of the mode Simulation (upper part).")}</div></div>
{img("sim_overview.png", "Mode Simulation: key figures and tab Filtration module – schematic of the module in true dimensions "
                         "over the axial coordinate z (filter cake, suspension, z_S1), residual moisture φ_RM(z), and "
                         "filter cake height h_c(z).")}
<div class="box">Axial profiles are model predictions: the enclosed module does not allow spatially resolved sampling;
experimentally, the residual moisture is accessible only at the module outlet.</div>
<h3>Further tabs</h3>
{img("sim_particles.png", "Tab Particles &amp; filter cake: PSD (model input and measured points) and filter cake properties.")}
{img("sim_process.png", "Tab Process design: z_S1 over Δp, over Q_susp at constant filling degree (with and without particle "
                        "backslip), and over ϑ_susp; operating window z_S1(Q_susp, n_screw) with the limit z_S1 = L_f "
                        "(red) and filling degree isolines.")}
{img("sim_washing.png", "Tab Washing: two-stage displacement washing coupled to the filtration module – wash curves X*(WR), "
                        "critical wash ratio, washing liquid flow rates, and CVSF configuration FWW.")}
<h3>3D apparatus</h3>
<p>The tab <b>3D apparatus</b> shows the CVSF as a running apparatus, configured from the inputs of the sidebar and the
module configuration selected in the tab (F, F-W, F-W-W, F-W-W-D). The geometry is taken from the Fusion 360 model of
the CVSF and scaled to the design inputs (L_f, L_T, D_i, screw): double-walled borosilicate glass modules, frit at the
bottom of the bore, couplings, GL 14 nozzles (feed, dosing, vacuum outlet), end piece with discharge, and drive. The
white PTFE screw is built from the screw design of the simulation, is right-handed as in the CAD model, and turns at
the real rotational speed counter-clockwise viewed from the feed end, so that it conveys from left to right.</p>
<ul><li><b>Motion and residence time:</b> particles move with v_p,ax = P·n_screw/θm, settle from the supernatant
suspension into the growing filter cake up to z_S1 (h_c(z) of the model), and fall out at the discharge. A gold tracer
particle shows position and residence time; the info panel lists the mean residence times per frit, per module, and
from the feed to the discharge.</li>
<li><b>Washing colours:</b> blue = mother liquor (impurity), red = wash liquid 1 (ethanol/water with red optical
tracer), colourless/white = wash liquid 2 (ethanol); mixed colours from the washing model X*(WR) of both steps
(legend in the view). A note appears if the wash liquid needs more frit length than available.</li>
<li><b>Controls:</b> play/pause, 1× real time, 10×, 60×, 300×, reset, release tracer, views (overview, F1 close-up,
washing, follow tracer), section view, info panels on/off; drag to rotate, scroll to zoom, right-drag to pan.</li></ul>
{img("sim_3d_overview.png", "Tab 3D apparatus, overview (configuration F-W-W-D): glass modules, PTFE screw, filter cake "
                            "coloured by the pore liquid, tracer particle, info panel, legend, and strip with z_S1, "
                            "pore liquid composition, and tracer position.")}
{img("sim_3d_closeup.png", "F1 close-up in section view: feed, supernatant suspension, cake formation up to z_S1, "
                           "frit, and tracer particle.")}
{img("sim_3d_washing.png", "Washing view: mother liquor (blue) is displaced by wash liquid 1 (red) from the dosing "
                           "point in W1 and by ethanol (white) in W2.")}
<div class="box">The 3D view is a qualitative representation of the model results; particles are enlarged and the
drops are symbolic. At high speed-up, the screw rotation is drawn slowed down, while the conveying velocities remain
true in time.</div>
<p>Tab <b>Export</b> provides the results (JSON), the residual moisture profile (CSV), and the inputs (JSON); tab
<b>Model &amp; references</b> summarizes the model structure, validity ranges, and references.</p>
""")
    H.append(f"""<h2 class="chap">4 · Mode Calibration (experiment database and Bayesian recalibration)</h2>
<p>The detailed, screenshot-based guide for the Excel template is
<code>docs/Guide_Experimental_Data_Template.pdf</code> (also downloadable in the interface). In short:</p>
<ol><li><b>Add data</b>: download the Excel template, fill in the material system and one row per experiment (RTD →
θm; filter cake test → ε, α_FC; CVSF run → residual moisture at the outlet with PSD and operating point), upload it
together with the PSD files, check the status of every row (usable for, missing information, plausibility/units), and
add the data as a dataset with name, operator, date, and description.</li>
<li><b>Experiment database</b>: each dataset and each experiment has an <i>active</i> checkbox; deactivation requires a
reason and is logged (figure below). Deactivated data stay stored and can be reactivated at any time.</li>
<li><b>Recalibrate model</b>: Bayesian recalibration with all active experiments of the material system, starting
again from the reference parameter set of the filtration study – deactivated data therefore have no influence on the
new model state (figure below).</li>
<li><b>Adopt</b> the checked result as the current model state ★; earlier model states remain available.</li></ol>
{img("gui_database.png", "Experiment database: datasets and experiments with activation checkboxes and reasons for deactivation.")}
{img("gui_result.png", "Result of a recalibration: posterior parameters with uncertainty, notes on poorly informed parameters, "
                       "prior and posterior distributions.")}
<table><tr><th>Stage</th><th>Parameters</th><th>Experimental data</th></tr>
<tr><td>1</td><td>μs, a, b (θm correlation, Fit 1)</td><td>θm from RTD measurements; screw, n_screw</td></tr>
<tr><td>2</td><td>A (sphericity correction, Fit F1)</td><td>filter cake porosity and/or specific cake resistance; PSD</td></tr>
<tr><td>3</td><td>B (equilibrium saturation factor, Fit F2)</td><td>residual moisture at the outlet; PSD; operating point</td></tr></table>
""")
    H.append(f"""<h2 class="chap">5 · Mode Experiment design (Bayesian experimental design)</h2>
<p>The mode answers the question <i>which experiments would make the model better and more accurate?</i> It uses the
current knowledge of the model – the selected model state, i.e. the posterior of the latest Bayesian calibration with all
active experiments – and evaluates candidate experiments by the information they are expected to provide about the
model parameters.</p>
<h3>5.1 Procedure</h3>
<ol><li><b>Choose the current knowledge</b>: model state ★ (default) or another parameter set.</li>
<li><b>Choose the experiment types and their relative effort (cost)</b>: RTD measurement (informs μs, a, b), filter cake
test (informs A), CVSF run with residual moisture measurement (informs B). The cost weights trade off information
against effort, e.g. a CVSF run with 2 against a filter cake test with 0.5.</li>
<li><b>Define the design spaces</b> (figure below): range of n_screw for the RTD measurements; particle shape, σg,
d50,3 range, and agglomeration degree range for the filter cake tests; for the CVSF runs two operating parameters as
axes (from Q_susp, n_screw, Δp, ϑ_susp, w_solid) with ranges, the grid resolution, and the fixed conditions
(particle system, setup, screw, remaining operating parameters).</li>
<li><b>Set the number of planned experiments k and the exploration weight w</b>.</li>
<li><b>Compute experiment plan</b>. RTD and filter cake candidates take less than 2 s; each grid point of the CVSF runs
requires two evaluations of the filtration module (approx. 0.6 s per point, parallelized).</li>
<li><b>Evaluate the result</b> (section 5.3) and <b>download the plan as Excel template</b>: the settings of the
planned experiments are filled in, the measured columns are empty.</li>
<li><b>Carry out the experiments</b>, fill in the measured values (and PSD files), and <b>upload the file in the mode
Calibration</b>; recalibrate and adopt the new model state. The next planning round then starts from the improved
knowledge.</li></ol>
{img("doe_settings.png", "Settings of the experiment design: current knowledge, number of experiments, exploration weight, "
                         "experiment types with cost, and the three design spaces.")}
<h3>5.2 Method</h3>
{img("doe_method.png", "Method summary in the interface (expander Method).")}
<ul><li><b>Current knowledge</b>: parameter vector p = (μs, a, b, A, B) with mean and covariance Σ of the model state.</li>
<li><b>Linearization</b>: for each candidate experiment x the model calculates the measured quantities y(x) and their
sensitivities J = ∂y/∂p at the current parameters. R is the measurement/model uncertainty of the measured quantities
(same values as in the calibration).</li>
<li><b>Expected information gain</b> (D-optimal Bayesian design, in nat):</li></ul>
<p class="eq">EIG(x) = ½ · ln det( I + R⁻¹ J Σ Jᵀ ) &nbsp;&nbsp;&nbsp; Σ′ = Σ − Σ Jᵀ (J Σ Jᵀ + R)⁻¹ J Σ</p>
<ul><li><b>Sequential batch Bayesian optimization</b>: the plan is built step by step; in each step the candidate with
the largest acquisition value</li></ul>
<p class="eq">a(x) = EIG(x | Σ<sub>k</sub>) / cost (normalized) + w · novelty(x)</p>
<ul><li>is selected; then Σ is updated with Σ′ (as if the experiment had been carried out), so that the next selection
accounts for the information already planned. The <b>novelty</b> term (distance to existing and planned experiments in
the normalized design space) adds exploration: experiments in regions without data also test the model structure,
which the parameter information alone does not capture. w = 0 gives pure information gain; larger w favors new
regions.</li>
<li>Existing experiments are the data of the filtration study (13 RTD values, 8 filter cakes, 12 residual moistures)
and all active experiments of the material system in the experiment database.</li></ul>
<h3>5.3 Results and their interpretation</h3>
{img("doe_plan.png", "Recommended plan: expected reduction of the parameter uncertainties (top) and ranked experiments with "
                     "settings, measured quantities, information gain (EIG), novelty, and cumulative reduction of the "
                     "parameter standard deviations (SD↓); download of the plan as Excel template.")}
<table><tr><th>Element</th><th>Meaning</th></tr>
<tr><td>key figures per parameter</td><td>expected reduction of the standard deviation of μs, a, b, A, B after all planned
experiments (green: ≥ 10 %)</td></tr>
<tr><td>rank, type, experiment</td><td>order of the plan and settings of each experiment</td></tr>
<tr><td>measure</td><td>quantities to be measured (θm; ε, α_FC, PSD; residual moisture at the outlet, PSD)</td></tr>
<tr><td>EIG_nat</td><td>information gain of the experiment given the experiments planned before it</td></tr>
<tr><td>novelty</td><td>0 = close to existing data, 1 = far from existing data</td></tr>
<tr><td>SD↓ … (cum.)</td><td>expected cumulative reduction of the parameter standard deviation up to this rank</td></tr></table>
{img("doe_uncertainty.png", "Expected standard deviations of the parameters after the planned experiments relative to the current model state.")}
{img("doe_runs.png", "CVSF runs: information gain per cost over two operating parameters (left; white: infeasible, cake formation "
                     "not completed on the filter medium; red dashed: z_S1 = L_f) and predicted residual moisture (right). "
                     "Gold stars: the three most informative CVSF runs; red stars with #: CVSF runs of the overall plan; ×: "
                     "existing experiments.")}
{img("doe_rtd.png", "RTD measurements: information gain of one measurement over n_screw for the screws (a), (b), (c); triangles: "
                    "existing RTD measurements; red stars: RTD measurements of the plan.")}
{img("doe_cakes.png", "Filter cake tests: information gain over d50,3 and agglomeration degree Ag3; ×: existing filter cakes; stars: "
                      "recommended tests.")}
<div class="box gold"><b>Example – current reference model state</b> (5 experiments, w = 0.3, cost RTD 1 / cake 0.5 /
CVSF run 2): the plan consists of three filter cake tests with strongly agglomerated particle systems (Ag3 ≈ 0.75 at
different d50,3) and RTD measurements at n_screw = 5 rpm with the screws (b) and (c). Expected reduction of the
parameter uncertainties: A ≈ −39 %, a ≈ −32 %, b ≈ −14 %, μs ≈ −5 %, B ≈ 0 %.<br/>
<b>Why are CVSF runs hardly selected?</b> The residual moisture scatters by approx. 3.6 %-pts. around the model
(measurement and model deviation of the filtration study). One additional value therefore reduces the uncertainty of B
only slightly; replicates, different particle systems, and operating points close to the deliquoring equilibrium are
more effective. The map of the CVSF runs nevertheless shows the most informative operating points.</div>
<div class="box warn"><b>Limits.</b> The EIG refers to the parameters of the existing model structure and is based on a
local linearization at the current parameters. Systematic model deviations (e.g. a missing physical effect) are not
captured by the information gain; they are addressed by the exploration term and by checking the new data in the
calibration (parity plots, leave-one-out Q²). Candidates outside the validated ranges (e.g. n_screw &gt; 5 rpm,
other material systems) are extrapolations of the model. The washing model is not part of the experiment design in
this version.</div>
""")
    H.append("""<h2 class="chap">6 · Recommended procedure for continuous model improvement</h2>
<ol><li><b>Plan</b> (mode Experiment design): select the current model state ★, the experiment types and costs, and the
design spaces that are technically feasible; compute the plan; check that the recommended settings can be realized;
download the plan.</li>
<li><b>Experiment</b>: carry out the planned experiments; measure PSD, θm, porosity/cake resistance, and residual
moisture as listed in the plan; document deviations.</li>
<li><b>Add data</b> (mode Calibration, tab Add data): fill in the measured values in the downloaded plan, upload it with
the PSD files, check the row status, and add the dataset.</li>
<li><b>Quality control</b> (tab Experiment database): deactivate non-representative experiments or datasets with a
reason (e.g. disturbed run, deviating material); deactivation can be undone and is logged.</li>
<li><b>Recalibrate</b> (tab Recalibrate model): check parity plots, leave-one-out Q², and warnings; look for outliers
(possible deactivation candidates).</li>
<li><b>Adopt</b> the new model state ★; the simulation and the next experiment design use it automatically.</li>
<li><b>Repeat</b>: the next plan starts from the improved knowledge; the expected uncertainty reduction decreases as the
model becomes better informed – a natural stopping criterion.</li></ol>
<div class="box ok">Every model state stores its provenance (datasets, experiments, data fingerprint, prior, user).
Model states can be exported and imported as JSON, so that results remain traceable. The reference results of the
filtration and washing studies are not affected by any calibration.</div>

<h2>7 · Validity, limitations, files, and troubleshooting</h2>
<h3>Validity of the model parameters</h3>
<p>Parameters fitted for l-alanine/water (bipyramidal, cuboid, and needle-shaped particles) and ethanol/water washing
liquids; sensitivity analysis ranges of the filtration study: d50,3 20–100 µm, σg 0.3–0.9, ψ 0.3–0.9, ϑ 10–50 °C,
Δp 40–200 mbar, Q_susp 20–100 mL/min, n_screw 1–5 rpm, w_solid 2–10 wt.-%. Liquid density and viscosity are those of
the l-alanine/water mother liquor. The washing correlations are based on eight wash curves of bipyramidal particles.</p>
<h3>Files of the package</h3>
<table><tr><th>File / folder</th><th>Content</th></tr>
<tr><td><code>gui/app.py</code></td><td>interface (Streamlit); modes Simulation, Calibration, Experiment design</td></tr>
<tr><td><code>gui/engine.py</code></td><td>interface layer to the model code (<code>scripts/cvsf.py</code>, <code>scripts/washing.py</code>)</td></tr>
<tr><td><code>gui/calibration.py</code>, <code>gui/database.py</code>, <code>gui/calib_page.py</code></td><td>Bayesian calibration, experiment database, mode Calibration</td></tr>
<tr><td><code>gui/design.py</code>, <code>gui/design_page.py</code></td><td>Bayesian experimental design, mode Experiment design</td></tr>
<tr><td><code>gui/launcher.pyw</code>, <code>install_desktop_app.py/.bat</code></td><td>desktop application and installer</td></tr>
<tr><td><code>docs/</code></td><td>this manual, guide and Excel template for the experimental data</td></tr>
<tr><td><code>README.md</code></td><td>technical documentation of the model code and of all scripts</td></tr></table>
<h3>Troubleshooting</h3>
<table><tr><th>Observation</th><th>Remedy</th></tr>
<tr><td>Desktop icon does not start</td><td>Run <code>install_desktop_app.bat</code> again; see the log file
<code>%LOCALAPPDATA%\\CVSF_Process_Simulator\\server.log</code>.</td></tr>
<tr><td>“Cake formation not completed on the filter medium”</td><td>Increase Δp, reduce Q_susp, or adjust n_screw (tab Process design).</td></tr>
<tr><td>Washing not evaluated</td><td>Requires z_S1 ≤ L_f in the filtration module.</td></tr>
<tr><td>Calibration status “outdated”</td><td>Data were added or (de)activated – recalibrate and adopt.</td></tr>
<tr><td>Experiment plan: no CVSF runs</td><td>Their information gain about B is small (see section 5.3); reduce the cost of
CVSF runs or increase w to explore new operating points.</td></tr>
<tr><td>Experiment design slow</td><td>Reduce the grid points per axis of the CVSF runs.</td></tr></table>
<p style="font-size:8.5pt;color:#6B7684">References: M.P. Meier, M. Vogel, L. Ohm, Mechanistic Modeling of Filtration and
Deliquoring within the Continuous Vacuum Screw Filter; M.P. Meier, L. Ohm, Mechanistic Modeling of Two-Stage Washing
within the Continuous Vacuum Screw Filter; M.P. Meier, M. Vogel, L. Ohm, CVSF_Model_Filtration_Deliquoring_Washing_V01,
TUDOdata (2026). Screenshots: reference model state of the filtration study; example values are illustrations.</p>""")
    html = (f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>CVSF Process Simulator – User manual</title>'
            f'<style>{CSS}</style></head><body>' + "\n".join(H) + "</body></html>")
    h = os.path.join(D, "CVSF_Process_Simulator_Manual.html")
    open(h, "w", encoding="utf-8").write(html)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.goto("file://" + h)
            pg.wait_for_timeout(600)
            pg.pdf(path=os.path.join(D, "CVSF_Process_Simulator_Manual.pdf"), format="A4", print_background=True,
                   margin=dict(top="13mm", bottom="14mm", left="12mm", right="12mm"), display_header_footer=True,
                   header_template="<span></span>",
                   footer_template='<div style="font-size:7pt;color:#7A8694;width:100%;text-align:center">'
                                   'CVSF Process Simulator – User manual · page <span class="pageNumber"></span>/'
                                   '<span class="totalPages"></span></div>')
            b.close()
    except Exception as ex:                                    # noqa: BLE001
        print("PDF not created:", ex)
    print("written:", h)


if __name__ == "__main__":
    build()
