import tkinter as tk
from phoneutils.android.lib.lib import *
import threading

def add_ios_tab(root, content_frame, device_udid):
    ios_tab_frame = tk.Frame(content_frame)
    ios_tab_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    tabs = {}

    network_tab = tk.Frame(ios_tab_frame)
    text_output = tk.Text(network_tab)
    text_output.pack(fill="both", expand=True)
    capture_proc = {"proc": None}

    def toggle_capture(btn):
        if btn["text"] == "Start Capture":
            subprocess.run(["rvictl", "-s", device_udid])
            capture_proc["proc"] = subprocess.Popen(["tcpdump", "-i", "rvi0", "-l"], stdout=subprocess.PIPE, text=True)
            def read_output():
                for line in capture_proc["proc"].stdout:
                    text_output.insert("end", line)
                    text_output.see("end")
            threading.Thread(target=read_output, daemon=True).start()
            btn.config(text="Stop Capture")
        else:
            if capture_proc["proc"]:
                capture_proc["proc"].terminate()
                capture_proc["proc"].wait()
                capture_proc["proc"] = None
            subprocess.run(["rvictl", "-x", device_udid])
            btn.config(text="Start Capture")

    btn_capture = tk.Button(network_tab, text="Start Capture", command=lambda: toggle_capture(btn_capture))
    btn_capture.pack()

    tabs["Network Capture"] = network_tab

    tab_buttons_frame = tk.Frame(ios_tab_frame)
    tab_buttons_frame.pack(side="top", fill="x")

    current_tab = {"frame": None}

    def show_tab(tab_name):
        if current_tab["frame"]:
            current_tab["frame"].pack_forget()
        current_tab["frame"] = tabs[tab_name]
        current_tab["frame"].pack(fill="both", expand=True)

    for name in tabs:
        btn = tk.Button(tab_buttons_frame, text=name, command=lambda n=name: show_tab(n))
        btn.pack(side="left")

    show_tab("Network Capture")