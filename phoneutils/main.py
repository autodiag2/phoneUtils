import subprocess, os, sys, io
from PIL import Image, ImageTk
from phoneutils.android.tabs.BootAnimationTab import BootAnimationTab
from phoneutils.android.tabs.ApkDownloadTab import ApkDownloadTab
from phoneutils.android.tabs.BinaryFileViewerTab import BinaryViewerTab
from phoneutils.android.tabs.CheatsTab import CheatsTab
from phoneutils.android.tabs.IntentAnalyzerTab import IntentAnalyzerTab
from phoneutils.android.lib.lib import *
from phoneutils.ios.main import add_ios_tab
import tkinter as tk
import subprocess, sys, os, threading
from phoneutils.android.lib.lib import *

def _mirror_screen():
    try:
        subprocess.run(["scrcpy"])
        return
    except Exception:
        pass
    mirror_window = tk.Toplevel()
    mirror_window.title("ADB Screen Mirroring (Slow)")
    mirror_window.minsize(500, 500)
    mirror_window.geometry("500x500")
    lbl = tk.Label(mirror_window, bg="black")
    lbl.place(relx=0.5, rely=0.5, anchor="center")

    max_w = [1200]
    max_h = [600]

    def on_resize(event):
        max_w[0] = event.width
        max_h[0] = event.height

    mirror_window.bind("<Configure>", on_resize)

    def update_frame():
        try:
            result = subprocess.run(
                ["adb", "exec-out", "screencap", "-p"], capture_output=True, timeout=5
            )
            if result.returncode == 0 and result.stdout:
                img = Image.open(io.BytesIO(result.stdout))
                w, h = img.size
                scale = min(max_w[0] / w, max_h[0] / h, 1.0)
                new_size = (int(w * scale), int(h * scale))
                img = img.resize(new_size, Image.LANCZOS)
                imgtk = ImageTk.PhotoImage(img)
                lbl.imgtk = imgtk
                lbl.config(image=imgtk)
            else:
                lbl.config(text="Error")
        except Exception:
            lbl.config(text="Error")
        mirror_window.after(1000, update_frame)

    update_frame()

def mirror_screen():
    t = threading.Thread(target=_mirror_screen)
    t.start()

def get_connected_devices():
    devices = {"android": [], "ios": []}
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        lines = result.stdout.strip().splitlines()[1:]
        devices["android"] = [line.split()[0] for line in lines if "device" in line]
    except Exception:
        pass
    try:
        result = subprocess.run(["idevice_id", "-l"], capture_output=True, text=True)
        devices["ios"] = result.stdout.strip().splitlines()
    except Exception:
        pass
    return devices

def choose_device(devices):
    sel_win = tk.Toplevel()
    sel_win.title("Select Device")
    sel_win.geometry("400x200")
    var = tk.StringVar()
    row = 0
    for dtype, devlist in devices.items():
        for d in devlist:
            tk.Radiobutton(sel_win, text=f"{dtype.upper()}: {d}", variable=var, value=f"{dtype}:{d}").grid(row=row, sticky="w")
            row += 1
    def confirm():
        sel_win.destroy()
    tk.Button(sel_win, text="Confirm", command=confirm).grid(row=row, pady=10)
    sel_win.wait_window()
    return var.get()

def window_ensure_show_and_focus(root):
    root.lift()             # bring window to front
    root.focus_force()      # force keyboard focus
    root.attributes("-topmost", True)
    root.after(0, lambda: root.attributes("-topmost", False))  # optionally release always-on-top

def main():
    root = tk.Tk()
    root.title("APK Downloader & Bootanimation Viewer")
    root.geometry("950x700")
    window_ensure_show_and_focus(root)

    # detect devices
    devices = get_connected_devices()
    if sum(len(v) for v in devices.values()) == 0:
        tk.messagebox.showerror("Error", "No devices detected")
        root.destroy()
        return
    elif sum(len(v) for v in devices.values()) == 1:
        dtype, did = next((k, v[0]) for k,v in devices.items() if v)
    else:
        sel = choose_device(devices)
        dtype, did = sel.split(":")

    if dtype == "ios":
        content_frame = tk.Frame(root)
        content_frame.pack(fill="both", expand=True)
        add_ios_tab(root, content_frame, did)
    else:
        top_frame = tk.Frame(root)
        top_frame.pack(side="top", fill="x", padx=10, pady=5)
        mirror_btn = tk.Button(top_frame, text="Mirror Screen", command=mirror_screen)
        mirror_btn.pack(side="right")
        switch_frame = tk.Frame(top_frame)
        switch_frame.pack(side="left")
        content_frame = tk.Frame(root)
        content_frame.pack(fill="both", expand=True)

        apk_tab = ApkDownloadTab(content_frame)
        boot_tab = BootAnimationTab(content_frame)
        bin_tab = BinaryViewerTab(content_frame)
        cheats_tab = CheatsTab(content_frame)
        intent_analyzer_tab = IntentAnalyzerTab(content_frame)
        tabs = (apk_tab, boot_tab, bin_tab, cheats_tab, intent_analyzer_tab)
        for tab in tabs:
            tab.place(relx=0, rely=0, relwidth=1, relheight=1)

        def show_tab(t):
            for tab in tabs:
                tab.lower()
            t.lift()

        tk.Button(switch_frame, text="APK Download", command=lambda: show_tab(apk_tab)).pack(side="left", padx=2)
        tk.Button(switch_frame, text="Bootanimation Viewer", command=lambda: show_tab(boot_tab)).pack(side="left", padx=2)
        tk.Button(switch_frame, text="Binary Viewer", command=lambda: show_tab(bin_tab)).pack(side="left", padx=2)
        tk.Button(switch_frame, text="Cheats", command=lambda: show_tab(cheats_tab)).pack(side="left", padx=2)
        tk.Button(switch_frame, text="Intent analyzer", command=lambda: show_tab(intent_analyzer_tab)).pack(side="left", padx=2)

        show_tab(apk_tab)

        if len(sys.argv) > 1:
            preload_path = sys.argv[1]
            if os.path.isfile(preload_path):
                boot_tab.boot_path.set(preload_path)
                boot_tab.start_animation(preload_path)

    root.mainloop()


if __name__ == "__main__":
    main()
