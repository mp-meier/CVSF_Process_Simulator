"""Builds the Windows setup folder dist/CVSF_Process_Simulator_<version>_Windows/:
Setup and uninstall scripts, documentation (PDF manual, guide, Excel template, README) and the software and model
state as git bundles (installation without GitHub access).   Usage: python tools/build_windows_setup.py [version]"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def version():
    m = re.search(r'SW_VERSION = "([^"]+)"', open(os.path.join(ROOT, "gui", "app.py"), encoding="utf-8").read())
    return m.group(1) if m else "x"


def main():
    ver = sys.argv[1] if len(sys.argv) > 1 else version()
    out = os.path.join(ROOT, "dist", f"CVSF_Process_Simulator_{ver}_Windows")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(os.path.join(out, "Dokumentation")); os.makedirs(os.path.join(out, "Daten"))
    for f in ("Setup_CVSF_Process_Simulator.bat", "Deinstallieren_CVSF_Process_Simulator.bat", "LIESMICH.txt"):
        shutil.copy(os.path.join(ROOT, "windows_setup", f), out)
    for f in ("docs/CVSF_Process_Simulator_Manual.pdf", "docs/Guide_Experimental_Data_Template.pdf",
              "docs/CVSF_experimental_data_template.xlsx", "README.md"):
        shutil.copy(os.path.join(ROOT, f), os.path.join(out, "Dokumentation"))
    subprocess.check_call(["git", "-C", ROOT, "bundle", "create",
                           os.path.join(out, "Daten", "CVSF_Process_Simulator.bundle"), "HEAD", "main"])
    model = os.path.join(ROOT, "cvsf_model")
    head = subprocess.check_output(["git", "-C", model, "rev-parse", "HEAD"], text=True).strip()
    subprocess.check_call(["git", "-C", model, "branch", "-f", "bundle-main", head])
    tags = subprocess.check_output(["git", "-C", model, "tag", "--points-at", head], text=True).split()
    subprocess.check_call(["git", "-C", model, "bundle", "create", os.path.join(out, "Daten", "CVSF_Model.bundle"),
                           "bundle-main", *tags])
    print("written:", out)


if __name__ == "__main__":
    main()
