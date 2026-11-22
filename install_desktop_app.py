"""Installs the CVSF Process Simulator as a desktop application (shortcut with icon on the desktop and in the start menu).

Run once with the Python environment that should execute the model, e.g. in the Miniforge Prompt:
    conda activate <env>
    python install_desktop_app.py            (install / update)
    python install_desktop_app.py --remove   (remove the shortcuts)
Missing packages (requirements.txt) are installed into this environment.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
NAME = "CVSF Process Simulator"
LAUNCHER = os.path.join(ROOT, "gui", "launcher.pyw")
ICO = os.path.join(ROOT, "assets", "cvsf.ico")
PNG = os.path.join(ROOT, "assets", "cvsf_icon_256.png")


def ensure_packages():
    try:
        import streamlit, plotly, numpy, scipy, pandas, openpyxl  # noqa: F401,E401
    except ImportError:
        print("Installing required packages (requirements.txt) ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", os.path.join(ROOT, "requirements.txt")])


def ps(cmd):
    return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                          capture_output=True, text=True)


def windows(remove=False):
    folders = [ps("[Environment]::GetFolderPath('Desktop')").stdout.strip(),
               ps("[Environment]::GetFolderPath('Programs')").stdout.strip()]
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    for f in folders:
        if not f:
            continue
        lnk = os.path.join(f, NAME + ".lnk")
        if remove:
            if os.path.exists(lnk):
                os.remove(lnk); print("removed", lnk)
            continue
        q = lambda x: x.replace("'", "''")                      # noqa: E731  (PowerShell single quotes)
        cmd = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{q(lnk)}');"
               f"$s.TargetPath='{q(pyw)}';$s.Arguments='\"{q(LAUNCHER)}\"';$s.WorkingDirectory='{q(ROOT)}';"
               f"$s.IconLocation='{q(ICO)},0';$s.Description='{NAME} - continuous vacuum screw filter model';$s.Save()")
        r = ps(cmd)
        print(("created " + lnk) if r.returncode == 0 and os.path.exists(lnk) else f"failed: {lnk}\n{r.stderr}")


def linux(remove=False):
    entry = (f"[Desktop Entry]\nType=Application\nName={NAME}\nComment=Continuous vacuum screw filter model\n"
             f"Exec=\"{sys.executable}\" \"{LAUNCHER}\"\nIcon={PNG}\nTerminal=false\nCategories=Science;Education;\n")
    targets = [os.path.expanduser("~/.local/share/applications/cvsf-process-simulator.desktop")]
    desk = os.path.expanduser("~/Desktop")
    if os.path.isdir(desk):
        targets.append(os.path.join(desk, "cvsf-process-simulator.desktop"))
    for t in targets:
        if remove:
            if os.path.exists(t):
                os.remove(t); print("removed", t)
            continue
        os.makedirs(os.path.dirname(t), exist_ok=True)
        with open(t, "w") as f:
            f.write(entry)
        os.chmod(t, 0o755)
        print("created", t)


def macos(remove=False):
    app = os.path.expanduser(f"~/Desktop/{NAME}.command")
    if remove:
        if os.path.exists(app):
            os.remove(app); print("removed", app)
        return
    with open(app, "w") as f:
        f.write(f"#!/bin/bash\n\"{sys.executable}\" \"{LAUNCHER}\"\n")
    os.chmod(app, 0o755)
    print("created", app, "(double-click to start; the icon can be set via Finder > Get Info)")


def ensure_model():
    """model code = git submodule cvsf_model/ (mp-meier/CVSF_Model)"""
    if os.path.isdir(os.path.join(ROOT, "cvsf_model", "scripts")):
        return
    print("Model code missing (folder cvsf_model) - fetching it with git ...")
    subprocess.call(["git", "-C", ROOT, "submodule", "update", "--init", "cvsf_model"])
    if not os.path.isdir(os.path.join(ROOT, "cvsf_model", "scripts")):
        sys.exit("The model code could not be fetched. Clone the software with\n"
                 "  git clone --recurse-submodules https://github.com/mp-meier/CVSF_Process_Simulator.git\n"
                 "(access to mp-meier/CVSF_Model required).")


if __name__ == "__main__":
    rm = "--remove" in sys.argv
    if not rm:
        ensure_model()
        ensure_packages()
    if sys.platform.startswith("win"):
        windows(rm)
    elif sys.platform == "darwin":
        macos(rm)
    else:
        linux(rm)
    if not rm:
        print(f"\n{NAME} installed. Start it via the desktop icon (Python environment: {sys.executable}).")
