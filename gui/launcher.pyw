"""CVSF Process Simulator – desktop launcher.

Starts the Streamlit server of the GUI in the background (no console window) and opens the interface in its own
application window (Microsoft Edge or Google Chrome in app mode). Closing the window stops the server.
If neither browser is found, the default browser is opened and a small control window stops the server on closing.

Usage: pythonw gui/launcher.pyw        (desktop shortcut created by install_desktop_app.py)
       python  gui/launcher.pyw --selftest   (starts the server, checks the response, stops it)
"""
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "gui", "app.py")
ICON_PNG = os.path.join(ROOT, "assets", "cvsf_icon_256.png")
TITLE = "CVSF Process Simulator"
WIN = sys.platform.startswith("win")
DATA = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share"),
                    "CVSF_Process_Simulator")
os.makedirs(DATA, exist_ok=True)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def python_console():
    """python executable for the server (python.exe next to pythonw.exe on Windows)"""
    exe = sys.executable
    if WIN and os.path.basename(exe).lower() == "pythonw.exe":
        cand = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.exists(cand):
            return cand
    return exe


def server_env():
    env = dict(os.environ)
    if WIN:  # conda/Miniforge environments: make the DLL folders available without "conda activate"
        p = os.path.dirname(sys.executable)
        extra = [p, os.path.join(p, "Library", "mingw-w64", "bin"), os.path.join(p, "Library", "usr", "bin"),
                 os.path.join(p, "Library", "bin"), os.path.join(p, "Scripts"), os.path.join(p, "bin")]
        env["PATH"] = os.pathsep.join([e for e in extra if os.path.isdir(e)] + [env.get("PATH", "")])
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    return env


def start_server(port):
    log = open(os.path.join(DATA, "server.log"), "w")
    cmd = [python_console(), "-m", "streamlit", "run", APP, "--server.headless", "true", "--server.port", str(port),
           "--server.address", "127.0.0.1", "--browser.gatherUsageStats", "false"]
    flags = 0x08000000 if WIN else 0                          # CREATE_NO_WINDOW
    return subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=server_env(),
                            creationflags=flags)


def wait_ready(port, proc, timeout=120):
    url = f"http://127.0.0.1:{port}/_stcore/health"
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except OSError:
            time.sleep(0.4)
    return False


def find_app_browser():
    cands = []
    if WIN:
        pf = [os.environ.get(k, "") for k in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")]
        for base in pf:
            cands += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                      os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
    elif sys.platform == "darwin":
        cands += ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    else:
        cands += [shutil.which(n) or "" for n in ("microsoft-edge", "google-chrome", "chromium", "chromium-browser")]
    return next((c for c in cands if c and os.path.exists(c)), None)


def splash():
    """small start window with the logo while the server starts (optional, needs tkinter)"""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.overrideredirect(True)
        root.configure(bg="#0A1E33")
        w, h = 420, 300
        root.geometry(f"{w}x{h}+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 2}")
        try:
            img = tk.PhotoImage(file=ICON_PNG).subsample(2, 2)
            tk.Label(root, image=img, bg="#0A1E33").pack(pady=(28, 10))
            root._img = img
        except tk.TclError:
            pass
        tk.Label(root, text="CVSF Process Simulator", fg="white", bg="#0A1E33",
                 font=("Segoe UI", 16, "bold")).pack()
        tk.Label(root, text="starting model …", fg="#BFD3E6", bg="#0A1E33", font=("Segoe UI", 10)).pack(pady=6)
        root.update()
        return root
    except Exception:                                          # noqa: BLE001
        return None


def control_window(url, proc):
    """fallback: default browser + small window that stops the server when closed"""
    webbrowser.open(url)
    try:
        import tkinter as tk
        root = tk.Tk()
        root.title(TITLE)
        root.geometry("380x150")
        try:
            root.iconphoto(True, tk.PhotoImage(file=ICON_PNG))
        except tk.TclError:
            pass
        tk.Label(root, text="CVSF Process Simulator is running.", font=("Segoe UI", 11, "bold")).pack(pady=(18, 4))
        tk.Label(root, text="Close this window to stop the simulator.").pack()
        tk.Button(root, text="Open interface again", command=lambda: webbrowser.open(url)).pack(pady=10)
        root.mainloop()
    except Exception:                                          # noqa: BLE001
        proc.wait()


def auto_update():
    """tested state of software and model from GitHub (silent; skipped offline or without git);
    disable with the file no_auto_update in the data folder"""
    if os.path.exists(os.path.join(DATA, "no_auto_update")) or not os.path.isdir(os.path.join(ROOT, ".git")):
        return
    try:
        subprocess.run([python_console(), os.path.join(ROOT, "tools", "model_update.py"), "--auto"], cwd=ROOT,
                       capture_output=True, timeout=90, env=server_env(), creationflags=0x08000000 if WIN else 0)
    except Exception:                                          # noqa: BLE001
        pass


def main():
    if "--selftest" not in sys.argv:
        auto_update()
    port = free_port()
    proc = start_server(port)
    url = f"http://127.0.0.1:{port}"
    if "--selftest" in sys.argv:
        ok = wait_ready(port, proc)
        html = urllib.request.urlopen(url, timeout=5).read().decode() if ok else ""
        print("server ready:", ok, "| page served:", "<html" in html.lower(), "| browser:", find_app_browser())
        proc.terminate()
        return
    sp = splash()
    ok = wait_ready(port, proc)
    if sp is not None:
        sp.destroy()
    if not ok:
        try:
            import tkinter.messagebox as mb
            mb.showerror(TITLE, "The simulator could not be started.\nSee log file:\n" +
                         os.path.join(DATA, "server.log"))
        except Exception:                                      # noqa: BLE001
            print("Start failed, see", os.path.join(DATA, "server.log"))
        proc.terminate()
        return
    try:
        br = find_app_browser()
        if br:
            # own temporary profile per start: the window is an independent process that ends when it is closed
            prof = os.path.join(DATA, f"window_{port}")
            subprocess.Popen([br, f"--app={url}", f"--user-data-dir={prof}", "--window-size=1600,1000",
                              "--no-first-run", "--no-default-browser-check", "--disable-features=Translate"]).wait()
            shutil.rmtree(prof, ignore_errors=True)
        else:
            control_window(url, proc)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
