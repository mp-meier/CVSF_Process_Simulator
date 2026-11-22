"""Experiment database of the CVSF Process Simulator: experimental data added after model version V01.

Every upload of a filled Excel template becomes a *dataset* (with name, operator, date, material system, source file);
its experiments are stored row by row. Datasets and single experiments can be activated or deactivated at any time
(checkboxes in the GUI, with a reason for the deactivation); only active data enter the Bayesian calibration.
Every change is written to a change log (who, when, what, why).

Continuous model improvement: each recalibration starts again from the reference parameter set of the filtration
study (prior; its data are therefore not stored here, to avoid double counting) and uses *all currently active*
experiments of the material system. Deactivating a dataset later thus removes its influence completely at the next
recalibration. The result is stored as a versioned *model state* with full provenance (which datasets and
experiments, data fingerprint) and can be adopted as the current model of the material system.

Storage (folder configurable, e.g. a shared network folder; default: local application data):
  experiment_database.json      datasets and experiments
  experiment_files/<dataset>/   copies of the PSD files referenced by the experiments
  experiment_database_log.csv   change log
  current_model.json            current model state per material system
  parameter_sets/               parameter sets and model states (JSON)
"""
from __future__ import annotations

import csv
import datetime as _dt
import getpass
import hashlib
import json
import os
import shutil

import pandas as pd

import calibration as C

DB_VERSION = 1
META = ["dataset_id", "dataset", "row_id", "active", "exclusion_reason"]


def _root():
    r = C.storage_root()
    os.makedirs(r, exist_ok=True)
    return r


def _p(name):
    return os.path.join(_root(), name)


def _now():
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _user():
    try:
        return getpass.getuser()
    except Exception:                                          # noqa: BLE001
        return "unknown"


# ---------------------------------------------------------------------------------------------------------------
# storage
# ---------------------------------------------------------------------------------------------------------------
def load():
    p = _p("experiment_database.json")
    if not os.path.exists(p):
        return dict(version=DB_VERSION, created=_now(), datasets=[])
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(db):
    p = _p("experiment_database.json")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=1, default=_jsonable, ensure_ascii=False)
    os.replace(tmp, p)


def _jsonable(v):
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(v, "item"):
        return v.item()
    return str(v)


def log(action, dataset="", row="", details=""):
    p = _p("experiment_database_log.csv")
    new = not os.path.exists(p)
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        if new:
            w.writerow(["timestamp", "user", "action", "dataset", "experiment", "details"])
        w.writerow([_now(), _user(), action, dataset, row, details])


def read_log(n=200):
    p = _p("experiment_database_log.csv")
    if not os.path.exists(p):
        return pd.DataFrame(columns=["timestamp", "user", "action", "dataset", "experiment", "details"])
    return pd.read_csv(p, sep=";").tail(n).iloc[::-1].reset_index(drop=True)


# ---------------------------------------------------------------------------------------------------------------
# datasets
# ---------------------------------------------------------------------------------------------------------------
def add_dataset(df, material, name, operator="", date="", description="", source_file="", uploads=None):
    """stores a checked experiment table as a new dataset; PSD files are copied into the database folder"""
    uploads = uploads or {}
    db = load()
    k = len(db["datasets"]) + 1
    ds_id = f"DS{k:04d}"
    while any(d["id"] == ds_id for d in db["datasets"]):
        k += 1
        ds_id = f"DS{k:04d}"
    fdir = os.path.join("experiment_files", ds_id)
    os.makedirs(_p(fdir), exist_ok=True)
    rows = []
    df = C._types(df)
    for i, r in df.iterrows():
        row = {c: _jsonable(r[c]) for c in C.COLS}
        for col in ("psd_results", "psd_descriptors"):
            src = C._resolve(r[col], uploads) if r[col] else None
            if src:
                dst = os.path.join(fdir, os.path.basename(src))
                if not os.path.exists(_p(dst)):
                    shutil.copy2(src, _p(dst))
                row[col] = dst.replace("\\", "/")
        row["row_id"] = f"{ds_id}-{i + 1:03d}"
        row["active"] = bool(int(r["include"] or 0) == 1)
        row["exclusion_reason"] = "" if row["active"] else "excluded in the uploaded template (include = 0)"
        rows.append(row)
    ds = dict(id=ds_id, name=name or ds_id, material=dict(name=material["name"], rhos=float(material["rhos"]),
                                                          sigma=float(material["sigma"])),
              added=_now(), added_by=_user(), operator=operator, experiment_date=str(date or ""),
              description=description, source_file=source_file, active=True, exclusion_reason="", rows=rows)
    db["datasets"].append(ds)
    save(db)
    log("dataset added", ds_id, "", f"{name}; {len(rows)} experiments; material {material['name']}; "
                                    f"source {source_file}")
    return ds_id


def delete_dataset(ds_id):
    db = load()
    db["datasets"] = [d for d in db["datasets"] if d["id"] != ds_id]
    save(db)
    shutil.rmtree(_p(os.path.join("experiment_files", ds_id)), ignore_errors=True)
    log("dataset deleted", ds_id)


def set_dataset_active(ds_id, active, reason=""):
    db = load()
    for d in db["datasets"]:
        if d["id"] == ds_id and (bool(d.get("active", True)) != bool(active) or d.get("exclusion_reason") != reason):
            d["active"] = bool(active)
            d["exclusion_reason"] = "" if active else reason
            log("dataset activated" if active else "dataset deactivated", ds_id, "", reason)
    save(db)


def set_rows_active(ds_id, changes):
    """changes: {row_id: (active, reason)}"""
    db = load()
    for d in db["datasets"]:
        if d["id"] != ds_id:
            continue
        for r in d["rows"]:
            if r["row_id"] in changes:
                a, why = changes[r["row_id"]]
                if bool(r.get("active", True)) != bool(a) or (r.get("exclusion_reason") or "") != (why or ""):
                    r["active"] = bool(a)
                    r["exclusion_reason"] = "" if a else (why or "")
                    log("experiment activated" if a else "experiment deactivated", ds_id, r["row_id"],
                        f"{r.get('ID', '')}: {why}" if not a else str(r.get("ID", "")))
    save(db)


def materials(db=None):
    db = db or load()
    out = {}
    for d in db["datasets"]:
        out[d["material"]["name"]] = d["material"]
    return out


def datasets_table(db=None, material=None):
    db = db or load()
    rows = []
    for d in db["datasets"]:
        if material and d["material"]["name"] != material:
            continue
        df = rows_frame(d)
        act = df[df["active"]] if len(df) else df
        rows.append(dict(active=bool(d.get("active", True)), dataset_id=d["id"], dataset=d["name"],
                         material=d["material"]["name"], experiments=len(df), active_experiments=len(act),
                         theta_m=int(act["theta_m_meas"].notna().sum()) if len(act) else 0,
                         cakes=int((act["eps_meas_pct"].notna() | act["alpha_FC_meas"].notna()).sum()) if len(act) else 0,
                         phi_RM=int(act["phi_RM_meas_pct"].notna().sum()) if len(act) else 0,
                         experiment_date=d.get("experiment_date", ""), operator=d.get("operator", ""),
                         added=d.get("added", ""), source_file=d.get("source_file", ""),
                         exclusion_reason=d.get("exclusion_reason", ""), description=d.get("description", "")))
    return pd.DataFrame(rows)


def rows_frame(d):
    df = pd.DataFrame(d["rows"])
    if not len(df):
        return pd.DataFrame(columns=C.COLS + META)
    df["dataset_id"], df["dataset"] = d["id"], d["name"]
    df["active"] = df["active"].astype(bool)
    df["exclusion_reason"] = df["exclusion_reason"].fillna("")
    t = C._types(df[C.COLS].copy())
    for c in META:
        t[c] = df[c].values
    return t


def active_data(material, db=None):
    """all experiments of the material system that are active (dataset and experiment) -> calibration table"""
    db = db or load()
    parts = []
    for d in db["datasets"]:
        if d["material"]["name"] != material or not d.get("active", True):
            continue
        df = rows_frame(d)
        df = df[df["active"]]
        if len(df):
            parts.append(df)
    if not parts:
        return pd.DataFrame(columns=C.COLS + META)
    df = pd.concat(parts, ignore_index=True)
    df["include"] = 1
    return df


def fingerprint(df):
    """hash of the active data (ids and values) -> provenance of model states"""
    if not len(df):
        return "no-data"
    cols = ["row_id"] + [c for c in C.COLS if c not in ("note", "include")]
    txt = df[cols].astype(str).sort_values("row_id").to_csv(index=False)
    return hashlib.sha256(txt.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------------------------------------------
# model states (current model per material system)
# ---------------------------------------------------------------------------------------------------------------
def _cur():
    p = _p("current_model.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except ValueError:
            pass
    return {}


def current_state(material):
    return _cur().get(material)


def set_current_state(material, set_name):
    c = _cur()
    c[material] = set_name
    json.dump(c, open(_p("current_model.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    log("current model state set", "", "", f"{material}: {set_name}")


def all_current():
    return _cur()


def model_state(res, material, active_df, prior_info):
    """parameter set of a recalibration with provenance"""
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    name = f"{material} – model state {ts}"
    s = C.new_set(res, name, base=prior_info.get("base"))
    ds = sorted(set(active_df["dataset_id"])) if len(active_df) else []
    s.update(kind="model_state", material_system=material,
             provenance=dict(datasets=ds, experiments=list(active_df["row_id"]) if len(active_df) else [],
                             fingerprint=fingerprint(active_df), n_experiments=int(len(active_df)),
                             created_by=_user(), prior=prior_info),
             description=f"Recalibration with all active experiments of {material}: {len(active_df)} experiments "
                         f"from {len(ds)} datasets ({', '.join(ds) or '–'}); prior: {prior_info.get('base')} "
                         f"(uncertainty × {prior_info.get('scale', 1):g}).")
    return s


def is_outdated(material, sets):
    """True if the active data differ from the data of the current model state"""
    cur = current_state(material)
    fp = fingerprint(active_data(material))
    if not cur or cur not in sets:
        return fp != "no-data"
    prov = sets[cur].get("provenance")
    if not prov:                                               # reference set: up to date if no active data
        return fp != "no-data"
    return prov.get("fingerprint") != fp
