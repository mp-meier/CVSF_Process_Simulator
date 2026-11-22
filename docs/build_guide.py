"""Builds the guide 'Entering experimental data for the Bayesian calibration' (HTML and PDF) from docs/img/.

python docs/build_guide.py      (PDF via Playwright/Chromium: pip install playwright && playwright install chromium)
"""
import base64
import os

D = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(D, "img")
ROOT = os.path.dirname(D)


def img(name, caption, width="100%"):
    b = base64.b64encode(open(os.path.join(IMG, name), "rb").read()).decode()
    return (f'<figure><img src="data:image/png;base64,{b}" style="width:{width}"/>'
            f'<figcaption>{caption}</figcaption></figure>')


def icon():
    b = base64.b64encode(open(os.path.join(ROOT, "assets", "cvsf_icon.svg"), "rb").read()).decode()
    return f'<img class="logo" src="data:image/svg+xml;base64,{b}"/>'


R, O, X = '<td class="r">●</td>', '<td class="o">○</td>', '<td class="x">–</td>'
MATRIX = [  # column, unit, theta_m, cake, phi, remark
    ("ID", "text", R, R, R, "unique name of the experiment (e.g. run number)"),
    ("include", "1 / 0", R, R, R, "1 = use, 0 = store only; can be changed later in the database"),
    ("shape", "bipyramidal / cuboid / needle", X, R, R, "particle shape; selects the PSD and packing routines"),
    ("psd_results", "file name or path", X, R, R, "PSDResults_*.xlsx of the dynamic image analysis <b>or</b> d10/d50/d90"),
    ("psd_descriptors", "file name or path", X, R, R, "ImageDescriptors_*.xlsx – only cuboid and needle-shaped particles"),
    ("d10_um, d50_um, d90_um", "µm", X, O, O, "only without PSD file (log-normal PSD); at least d50 + one of d10/d90"),
    ("psi_eff", "-", X, O, O, "only without PSD file; empty = preset of the particle shape"),
    ("Ag3", "-", X, O, O, "only without PSD file; <b>required</b> for porosity/cake resistance (otherwise A is not informed)"),
    ("setup", "current / previous", X, X, R, "module generation (frit 6 cm / 4.5 cm)"),
    ("screw", "a / b / c", R, X, R, "screw design of the run"),
    ("Q_mL_min", "mL/min", O, X, R, "suspension volume flow rate"),
    ("w_solid_pct", "wt.-%", X, X, R, "solid mass fraction of the suspension, in % (6, not 0.06)"),
    ("n_rpm", "rpm", R, X, R, "rotational screw speed"),
    ("dp_mbar", "mbar", X, X, R, "pressure difference of the filtration module, in mbar (not Pa)"),
    ("T_C", "°C", X, X, R, "suspension temperature"),
    ("theta_m_meas", "-", R, X, X, "measured θm = τm / τhy (RTD)"),
    ("eps_meas_pct", "%", X, R, X, "measured porosity in % – porosity and/or cake resistance"),
    ("alpha_FC_meas", "m/kg", X, R, X, "measured specific cake resistance – porosity and/or cake resistance"),
    ("phi_RM_meas_pct", "%", X, X, R, "measured residual moisture at the outlet of the filtration module (wet basis) in %"),
    ("note", "text", O, O, O, "free text (not used by the model)"),
]

CSS = """
@page { size: A4; margin: 16mm 15mm 16mm 15mm; }
body { font-family: 'Segoe UI', 'Source Sans Pro', Helvetica, Arial, sans-serif; font-size: 10.5pt; color: #1E1E1E;
       line-height: 1.42; }
.title { display:flex; align-items:center; gap:16px; padding:14px 18px; border-radius:12px; color:#fff;
         background: linear-gradient(110deg, #0A1E33 0%, #16395F 60%, #1F4E79 100%); margin-bottom: 14px; }
.title .logo { width:64px; height:64px; border-radius:12px; }
.title h1 { margin:0; font-size:19pt; } .title p { margin:3px 0 0 0; color:#BFD3E6; font-size:10pt; }
h2 { color:#16395F; border-bottom: 2px solid #16395F; padding-bottom: 3px; margin-top: 22px; font-size: 14pt;
     page-break-after: avoid; }
h3 { color:#1F4E79; margin-bottom: 4px; font-size: 11.5pt; page-break-after: avoid; }
.step { display:inline-block; background:#E6AF2D; color:#1E1E1E; font-weight:700; border-radius:999px;
        padding:1px 10px; margin-right:6px; }
figure { margin: 8px 0 14px 0; page-break-inside: avoid; }
figure img { border:1px solid #C9D2DC; border-radius:6px; }
figcaption { font-size: 8.8pt; color:#5A6573; margin-top: 3px; }
table { border-collapse: collapse; width:100%; font-size: 8.8pt; margin: 6px 0 12px 0; page-break-inside: auto; }
th { background:#16395F; color:#fff; padding:4px 6px; text-align:left; }
td { border-bottom:1px solid #DCE3EB; padding:3px 6px; vertical-align: top; }
td.r { color:#2E8B57; text-align:center; font-weight:700; } td.o { color:#1F4E79; text-align:center; }
td.x { color:#9AA5B1; text-align:center; }
code { background:#F3F6FA; padding:0 3px; border-radius:3px; font-size: 9pt; }
.box { border-left: 5px solid #1F4E79; background:#F3F6FA; padding:8px 12px; margin:10px 0; page-break-inside: avoid; }
.warn { border-left-color:#C00000; background:#FDF1F1; }
.ok { border-left-color:#2E8B57; background:#F0F8F3; }
.flow { display:flex; gap:6px; margin: 8px 0 12px 0; }
.flow div { flex:1; background:#F3F6FA; border:1px solid #C9D2DC; border-radius:8px; padding:6px 8px; font-size:9pt; }
.flow b { color:#16395F; }
.pb { page-break-before: always; }
ul { margin-top: 3px; } li { margin-bottom: 2px; }
"""


def build():
    rows = "".join(f"<tr><td><code>{c}</code></td><td>{u}</td>{a}{b}{p}<td>{rem}</td></tr>"
                   for c, u, a, b, p, rem in MATRIX)
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>CVSF Process Simulator – Guide experimental data</title>
<style>{CSS}</style></head><body>
<div class="title">{icon()}<div><h1>Entering experimental data for the Bayesian calibration</h1>
<p>CVSF Process Simulator · Model V01 · guide to the Excel template, the experiment database, and the recalibration</p></div></div>

<p>This guide describes how experimental data of completed CVSF runs are transferred to the CVSF Process Simulator so that
the model parameters can be improved continuously by Bayesian calibration. Follow the five steps; every step shows
the corresponding screenshot.</p>
<div class="flow">
<div><b>1 Template</b><br/>download the Excel template</div>
<div><b>2 Fill in</b><br/>material system and one row per experiment</div>
<div><b>3 Upload &amp; check</b><br/>template + PSD files, check every row, add as dataset</div>
<div><b>4 Database</b><br/>activate / deactivate datasets and experiments</div>
<div><b>5 Recalibrate</b><br/>check the results, adopt the new model state</div>
</div>

<h2>Which data improve which model parameters?</h2>
<table><tr><th>Measured quantity (column)</th><th>Typical experiment</th><th>Updated parameters</th></tr>
<tr><td>θm (<code>theta_m_meas</code>)</td><td>residence time distribution (RTD) of the solids</td>
<td>μs, a, b – residence time correlation (Fit 1)</td></tr>
<tr><td>ε, α_FC (<code>eps_meas_pct</code>, <code>alpha_FC_meas</code>)</td><td>filter cake test, e.g. pressure
filtration cell (VDI 2762), with the PSD of the same particles</td><td>A – sphericity correction (Fit F1)</td></tr>
<tr><td>φ_RM (<code>phi_RM_meas_pct</code>)</td><td>CVSF run: residual moisture of the product at the outlet of the
filtration module, with PSD and complete operating point</td><td>B – equilibrium saturation factor (Fit F2)</td></tr>
</table>
<div class="box">One row may contain several measured quantities of the same run (e.g. θm and φ_RM). Rows are used
wherever they are complete; incomplete rows are stored but ignored by the calibration until they are completed.</div>

<h2><span class="step">Step 1</span>Download the Excel template</h2>
<div style="display:flex; gap:14px; align-items:flex-start">
<div style="flex:1"><p>Start the CVSF Process Simulator (desktop icon or <code>start_gui.bat</code>), switch to the
mode <b>Calibration</b> in the sidebar (Figure 1), open tab <b>1 · Add data</b>, and click <b>Excel template</b>
(Figure 2). This guide can be downloaded next to it; <b>Show example rows</b> displays three complete example rows in
the interface.</p>
<p>The sidebar summarizes the calibration workflow: add data → activate/deactivate in the experiment database →
recalibrate → adopt the new model state.</p></div>
<div style="width:30%">{img("gui_sidebar.png", "Figure 1: Mode switch and calibration workflow.")}</div></div>
{img("gui_add_template.png", "Figure 2: Tab 1 · Add data – download of the Excel template and of this guide.")}
<p>The template contains four sheets:</p>
<ul><li><b>Instructions</b> – short version of this guide, required columns, definitions.</li>
<li><b>Experiments</b> – the sheet to be filled in (row 1: column names, row 2: units, data from row 3).</li>
<li><b>Example</b> – three complete example rows (one per measured quantity), colored by column group.</li>
<li><b>Material system</b> – name of the material system, solid density, surface tension of the liquid.</li></ul>

<h2><span class="step">Step 2</span>Fill in the template</h2>
<h3>2a · Sheet “Material system”</h3>
{img("xl_material.png", "Figure 3: Sheet Material system (yellow cells are filled in).")}
<div class="box warn"><b>Use exactly the same name</b> for all datasets of one material system (e.g.
<code>L-alanine / water</code>). Datasets with the same name are calibrated together; a different spelling creates a
new material system with a weakly informative prior.</div>

<h3>2b · Sheet “Experiments” – one row per experiment</h3>
<p>The sheet <b>Example</b> shows how complete rows look. The colors mark the column groups: grey = identification,
orange = particle system (PSD), green = apparatus and operating point, yellow = measured quantities. Hovering over a
column name in Excel shows its unit and description.</p>
{img("xl_example_part1.png", "Figure 4a: Sheet Example, columns A–L (identification, particle system, setup, screw).")}
{img("xl_example_part2.png", "Figure 4b: Sheet Example, columns M–V (operating point, measured quantities, note).")}
<p>Fill in the sheet <b>Experiments</b> in the same way, starting in row 3. Only the columns required for the measured
quantity of the row are needed; leave all other cells empty (do not enter 0):</p>
<table><tr><th>Column</th><th>Unit</th><th>θm (RTD)</th><th>ε / α_FC (filter cake)</th><th>φ_RM (CVSF run)</th>
<th>Remark</th></tr>{rows}</table>
<p style="font-size:8.8pt">● required · ○ optional / alternative · – not used</p>
{img("xl_exp_part1.png", "Figure 5a: Filled sheet Experiments, columns A–L (three rows: RTD, filter cake test, CVSF run).")}
{img("xl_exp_part2.png", "Figure 5b: Filled sheet Experiments, columns M–V.")}

<h3>2c · Definitions</h3>
<table><tr><th>Quantity</th><th>Definition</th></tr>
<tr><td><code>theta_m_meas</code></td><td>θm = τm / τhy: mean solids residence time τm from the RTD divided by the
residence time of ideal screw conveying τhy = L / (P · n_screw) over the same conveying length L (P: pitch)</td></tr>
<tr><td><code>eps_meas_pct</code></td><td>filter cake porosity = void volume / cake volume, in %</td></tr>
<tr><td><code>alpha_FC_meas</code></td><td>mass-related specific filter cake resistance in m/kg</td></tr>
<tr><td><code>phi_RM_meas_pct</code></td><td>residual moisture of the product at the outlet of the filtration module,
wet basis: m_liquid / (m_liquid + m_solid), in %</td></tr>
<tr><td><code>w_solid_pct</code></td><td>solid mass fraction of the suspension in wt.-%</td></tr>
<tr><td><code>setup</code></td><td><code>current</code>: frit 6 cm, transport zone 8 cm, module 14 cm;
<code>previous</code>: frit 4.5 cm, module 13 cm</td></tr>
<tr><td><code>screw</code></td><td>(a) one flight, P = 12 mm, d_i = 16 mm; (b) one flight, P = 23 mm, d_i = 21 mm;
(c) two flights, P = 24 mm, d_i = 21 mm</td></tr>
<tr><td>PSD files</td><td><code>PSDResults_*.xlsx</code> (PSD and agglomeration degree) and, for cuboid and needle-shaped
particles, <code>ImageDescriptors_*.xlsx</code> (minimum/maximum Feret diameters), exported by the dynamic image
analysis. Enter the <b>file name</b> and upload the file together with the template, or enter the full path.</td></tr>
</table>
<div class="box warn"><b>Common mistakes</b><ul>
<li>Fractions instead of percent (0.21 instead of 21 for φ_RM; 0.06 instead of 6 for w_solid).</li>
<li>Pressure difference in Pa or bar instead of mbar.</li>
<li>Residual moisture on dry basis instead of wet basis.</li>
<li>θm entered as τm in minutes instead of the dimensionless ratio.</li>
<li>Rows with ID starting with <code>EXAMPLE</code> are ignored – rename copied example rows.</li>
<li>PSD file name in the template differs from the uploaded file name.</li></ul>
The interface checks the plausibility of all values and points out values that look like wrong units.</div>

<h2><span class="step">Step 3</span>Upload, check, and add as dataset</h2>
<p>In tab <b>1 · Add data</b>, upload the filled template (left) and all PSD files referenced in it (right; several
files at once). The experiments appear in an editable table; values can still be corrected there. Below the table,
the status of every row is shown:</p>
{img("gui_add_check.png", "Figure 6: Uploaded template and PSD file, editable table, and status of every row.")}
<ul><li><b>usable for</b> – which calibration stage the row informs (θm, ε/α_FC, φ_RM).</li>
<li><b>missing information</b> – what is missing (e.g. PSD file not uploaded, operating point incomplete).</li>
<li><b>plausibility check</b> – values outside the usual range (often a unit error).</li></ul>
<p>Then enter the dataset information (material system, dataset name, operator, date of the experiments, description
of special features) and click <b>Add dataset to the experiment database</b>. The PSD files are copied into the
database folder, so the dataset remains complete even if the original files are moved.</p>
{img("gui_add_dataset.png", "Figure 7: Dataset information and adding the dataset to the experiment database.")}

<h2><span class="step">Step 4</span>Experiment database: activate and deactivate</h2>
<p>Tab <b>2 · Experiment database</b> lists all datasets added since model version V01. Each dataset and each single
experiment has an <b>active</b> checkbox. Only active experiments of active datasets enter the calibration.</p>
{img("gui_database.png", "Figure 8: Experiment database – datasets (top) and experiments of the selected dataset (bottom); "
                         "experiment DS0001-008 is deactivated with a reason.")}
<ul><li>To exclude data (e.g. a run turns out to be not representative), uncheck <b>active</b>, enter the
<b>reason for deactivation</b>, and click <b>Save … changes</b>. Deactivated data stay in the database and can be
reactivated at any time.</li>
<li>Every change is written to the <b>change log</b> (time, user, action, reason).</li>
<li>Deleting a dataset is possible in its details, but deactivation is usually sufficient and keeps the history.</li>
<li>The storage folder can be changed (e.g. to a shared network folder of the working group) – all users then work
with the same experiment database and model states.</li></ul>
<div class="box">The 33 data of the filtration study (13 RTD values, 8 filter cakes, 12 residual moistures) are
already contained in the reference parameter set and are therefore <b>not</b> stored in the database again.</div>

<h2><span class="step">Step 5</span>Recalibrate the model and adopt the model state</h2>
<p>Tab <b>3 · Recalibrate model</b> shows for the selected material system the current model state, whether it is
<b>outdated</b> (active data changed since), and the number of active experiments. Click <b>Recalibrate model with
all active experiments</b>.</p>
{img("gui_recalibrate.png", "Figure 9: Status of the current model state and start of the recalibration.")}
<p>Each recalibration starts again from the reference parameter set of the filtration study (prior) and uses all
active experiments. Deactivated data therefore have no influence on the new model state.</p>
{img("gui_result.png", "Figure 10: Result of a recalibration – parameter values with uncertainty, notes on poorly "
                       "informed parameters, and prior/posterior distributions.")}
<div class="box ok"><b>Before adopting, check:</b><ul>
<li>Do the model-vs-experiment plots improve, and are there outliers (possibly a deactivation candidate)?</li>
<li>Leave-one-out Q²: values near 1 mean good prediction of experiments not used for the calibration.</li>
<li>Notes “data hardly inform this parameter”: the parameter remains close to the prior – collect more or more
varied data (e.g. different rotational screw speeds and screws for θm, different PSDs for A, different operating
points for B).</li></ul></div>
<p>Click <b>Adopt as current model state</b>. The model state is stored with its provenance (datasets, experiments,
data fingerprint) and is marked with ★ in the parameter-set selection of the mode <b>Simulation</b>. Earlier model
states remain available in tab <b>4 · Model states &amp; parameter sets</b> and can be reactivated at any time.</p>

<h2>Troubleshooting</h2>
<table><tr><th>Message</th><th>Cause and remedy</th></tr>
<tr><td>PSD file '…' not found</td><td>Upload the file together with the template, or enter the full path; the file name
must match exactly (incl. extension).</td></tr>
<tr><td>ImageDescriptors file missing</td><td>Cuboid and needle-shaped particles require the ImageDescriptors file in
addition to the PSDResults file.</td></tr>
<tr><td>φ_RM: … missing</td><td>The residual moisture requires the complete operating point (setup, screw, Q, w_solid,
n, Δp, ϑ).</td></tr>
<tr><td>cake formation not completed (z_S1 &gt; L_f)</td><td>For this operating point the model predicts incomplete cake
formation on the filter medium; the residual moisture cannot be used for B. Check Δp, Q, and n.</td></tr>
<tr><td>plausibility check …</td><td>Value outside the usual range – check the unit (%, mbar, rpm).</td></tr>
<tr><td>Status “outdated”</td><td>Datasets were added or (de)activated since the current model state – recalibrate.</td></tr>
</table>
<p style="font-size:8.5pt;color:#6B7684">CVSF Process Simulator · model code CVSF_Model_Filtration_Deliquoring_Washing_V01
· M.P. Meier, M. Vogel, L. Ohm · TU Dortmund University, Laboratory of Plant and Process Design. The example values are
taken from the filtration study and serve as illustration only.</p>
</body></html>"""
    h = os.path.join(D, "Guide_Experimental_Data_Template.html")
    open(h, "w", encoding="utf-8").write(html)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.goto("file://" + h)
            pg.wait_for_timeout(500)
            pg.pdf(path=os.path.join(D, "Guide_Experimental_Data_Template.pdf"), format="A4", print_background=True,
                   margin=dict(top="14mm", bottom="14mm", left="13mm", right="13mm"),
                   display_header_footer=True, header_template="<span></span>",
                   footer_template='<div style="font-size:7pt;color:#7A8694;width:100%;text-align:center">'
                                   'CVSF Process Simulator – Guide experimental data · page '
                                   '<span class="pageNumber"></span>/<span class="totalPages"></span></div>')
            b.close()
    except Exception as ex:                                    # noqa: BLE001
        print("PDF not created:", ex)
    print("written:", h)


if __name__ == "__main__":
    build()
