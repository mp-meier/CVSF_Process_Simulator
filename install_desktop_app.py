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


def known_folder(name):
    """Desktop / start menu folder of the user (also when redirected, e.g. to OneDrive)"""
    ids = {"Desktop": "B4BFCC3A-DB2C-424C-B029-7FE99A87C641", "Programs": "A77F5D77-2E2B-44C3-A6A2-ABA601054A51"}
    fallback = {"Desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
                "Programs": os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu",
                                         "Programs")}
    try:
        import ctypes
        import uuid
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                        ("Data4", ctypes.c_ubyte * 8)]
        u = uuid.UUID(ids[name])
        g = GUID(u.time_low, u.time_mid, u.time_hi_version, (ctypes.c_ubyte * 8)(*u.bytes[8:]))
        out = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(out)) == 0:
            path = out.value
            ctypes.windll.ole32.CoTaskMemFree(out)
            if path and os.path.isdir(path):
                return path
    except Exception:                                          # noqa: BLE001
        pass
    return fallback[name]


def windows(remove=False):
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    for f in (known_folder("Desktop"), known_folder("Programs")):
        if not f or not os.path.isdir(f):
            continue
        lnk = os.path.join(f, NAME + ".lnk")
        if remove:
            if os.path.exists(lnk):
                os.remove(lnk); print("removed", lnk)
            continue
        try:
            import pylnk3                                      # pure-Python writer for Windows shortcuts
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "pylnk3"])
            import pylnk3
        pylnk3.for_file(pyw, lnk, arguments=f'"{LAUNCHER}"', description=f"{NAME} - continuous vacuum screw filter",
                        icon_file=ICO, icon_index=0, work_dir=ROOT)
        print(("created " if os.path.exists(lnk) else "FAILED ") + lnk)


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
