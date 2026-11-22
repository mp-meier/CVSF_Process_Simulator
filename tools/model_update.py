"""Model version of the CVSF Process Simulator: the model code is the git submodule cvsf_model/ (mp-meier/CVSF_Model).

The software follows the released model versions (git tags V01, V02, ...). On GitHub, the action
.github/workflows/update-model.yml takes over a new model tag only after the self test (tools/selftest.py) has passed.
Locally, an update therefore pulls the tested state of the software repository including the model version:
    python tools/model_update.py                 show the current model version and the newest released one
    python tools/model_update.py --update        update software and model to the tested state on GitHub (git pull)
    python tools/model_update.py --auto          like --update, silent and without error if offline (start scripts)
    python tools/model_update.py --latest-model  switch the model directly to the newest tag (not yet tested)
    python tools/model_update.py --tag V01       switch the model to a specific version
After an update, restart the interface (the model is loaded at start).
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(ROOT, "cvsf_model")
TAG_PATTERN = re.compile(r"^V\d+(\.\d+)*$")


def _git(*args, timeout=60):
    return subprocess.run(["git", "-C", MODEL, *args], capture_output=True, text=True, timeout=timeout)


def _key(tag):
    return tuple(int(x) for x in tag[1:].split("."))


def available():
    return os.path.isdir(os.path.join(MODEL, "scripts"))


def current():
    """current model version: tag (if the checkout is exactly at a tag) and commit"""
    if not available():
        return dict(tag=None, commit=None, ok=False)
    try:
        c = _git("rev-parse", "--short", "HEAD").stdout.strip() or None
        t = _git("describe", "--tags", "--exact-match").stdout.strip() or None
        return dict(tag=t, commit=c, ok=True)
    except (OSError, subprocess.SubprocessError):
        return dict(tag=None, commit=None, ok=True)


def tags(fetch=True):
    if fetch:
        _git("fetch", "--tags", "--quiet", "origin", timeout=30)
    out = _git("tag", "-l").stdout.split()
    return sorted([t for t in out if TAG_PATTERN.match(t)], key=_key)


def newest(fetch=True):
    t = tags(fetch)
    return t[-1] if t else None


def switch(tag):
    r = _git("checkout", "--quiet", tag)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return current()


def init_submodule():
    """fill an empty cvsf_model/ (e.g. after cloning without --recurse-submodules)"""
    return subprocess.run(["git", "-C", ROOT, "submodule", "update", "--init", "cvsf_model"], capture_output=True,
                          text=True, timeout=600)


def update_software():
    """git pull of the software repository and checkout of the model version recorded there (tested state)"""
    r = subprocess.run(["git", "-C", ROOT, "pull", "--ff-only", "--quiet"], capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or "git pull failed")
    r = subprocess.run(["git", "-C", ROOT, "submodule", "update", "--init", "cvsf_model"], capture_output=True,
                       text=True, timeout=600)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or "submodule update failed")
    return current()


def main(argv):
    if not available():
        r = init_submodule()
        if not available():
            sys.exit("The model code (folder cvsf_model) is missing. Clone with: git clone --recurse-submodules "
                     "https://github.com/mp-meier/CVSF_Process_Simulator.git\n" + r.stderr)
    auto = "--auto" in argv
    try:
        cur = current()
        if "--tag" in argv:
            t = argv[argv.index("--tag") + 1]
            print("switched to", switch(t))
            return
        if "--update" in argv or auto:
            after = update_software()
            if after["commit"] != cur["commit"]:
                print(f"model updated: {cur['tag'] or cur['commit']} -> {after['tag'] or after['commit']}")
            elif not auto:
                print(f"software and model are up to date (model {cur['tag'] or cur['commit']})")
            return
        new = newest()
        if "--latest-model" in argv:
            if new and new != cur["tag"]:
                switch(new)
                print(f"model switched to {new} (not yet tested with this software version)")
            else:
                print(f"model is the newest version ({new})")
            return
        print(f"current model version: {cur['tag'] or '-'} ({cur['commit']}); newest released: {new}")
    except Exception as ex:                                    # noqa: BLE001
        if not auto:
            sys.exit(f"model update not possible: {ex}")


if __name__ == "__main__":
    main(sys.argv[1:])
