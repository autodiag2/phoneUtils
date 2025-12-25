import os, tkinter as tk
from tkinter import ttk
from phoneutils.android.lib.lib import *
import subprocess
import zipfile
from phoneutils.android.lib.FileExplorer import FileExplorer
from phoneutils.android.lib.BinaryFileViewer import BinaryFileViewer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_APKS = os.path.join(BASE_DIR, "data", "apk")

def adb_pull_apk(package_name, dst):
    apk_path = adb_apk_location_from(package_name)
    if apk_path == None:
        return False
    r2 = subprocess.run(["adb", "pull", apk_path, dst], capture_output=True)
    return r2.returncode == 0

class ApkTreeViewer(tk.Toplevel):
    def __init__(self, root_folder):
        super().__init__()
        self.title(f"APK Explorer: {os.path.basename(root_folder)}")
        paned = tk.PanedWindow(self, orient='horizontal')
        paned.pack(fill='both', expand=True)
        nav_frame = FileExplorer(paned, self.on_file_selected, connector_type="filesystem", root_path=root_folder)
        paned.add(nav_frame)
        self.readFileFrame = BinaryFileViewer(paned, connector_type="filesystem")

    def on_file_selected(self, path):
        self.readFileFrame.on_file_selected(path)

class ApkDownloadTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tk.Label(scroll_frame, text="Package name:").pack(padx=5, pady=10, anchor="w")
        self.apk_entry = tk.Entry(scroll_frame, width=40)
        self.apk_entry.pack(padx=5, pady=2, anchor="w")
        tk.Button(scroll_frame, text="Download APK", command=self.download_apk_gui).pack(padx=5, pady=10, anchor="w")
        self.apk_status_label = tk.Label(scroll_frame, text="")
        self.apk_status_label.pack(padx=5, pady=2, anchor="w")

        self.packages_frame = ttk.LabelFrame(scroll_frame, text="Installed Packages")
        self.packages_frame.pack(fill="both", expand=True, padx=5, pady=10)

        search_frame = tk.Frame(self.packages_frame)
        search_frame.pack(fill="x", padx=5, pady=5)
        self.search_entry = tk.Entry(search_frame, width=30)
        self.search_entry.pack(side="left", padx=(0, 5))
        self.search_entry.bind("<Return>", lambda e: self.find_next_package())
        self.find_button = tk.Button(search_frame, text="Find", command=self.find_next_package)
        self.find_button.pack(side="left")

        self.packages_listbox = tk.Listbox(self.packages_frame, width=70, exportselection=False)
        self.packages_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.packages_listbox.bind("<<ListboxSelect>>", self.on_package_select)

        self.apks_frame = ttk.LabelFrame(scroll_frame, text="Downloaded APKs")
        self.apks_frame.pack(fill="both", expand=True, padx=5, pady=10)

        search_apk_frame = tk.Frame(self.apks_frame)
        search_apk_frame.pack(fill="x", padx=5, pady=(5, 0))
        tk.Label(search_apk_frame, text="Search downloaded:").pack(side="left")
        self.apk_search_entry = tk.Entry(search_apk_frame, width=30)
        self.apk_search_entry.pack(side="left", padx=(5, 0))
        self.apk_search_entry.bind("<Return>", lambda e: self.find_next_downloaded_apk())
        self.apk_find_button = tk.Button(search_apk_frame, text="Find", command=self.find_next_downloaded_apk)
        self.apk_find_button.pack(side="left", padx=(5, 0))

        self.apks_listbox = tk.Listbox(self.apks_frame, width=70, exportselection=False)
        self.apks_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.apks_listbox.bind("<<ListboxSelect>>", self.on_apk_select)
        self.no_apk_label = tk.Label(self.apks_frame, text="No Apk downloaded")
        self.no_apk_label.place(relx=0.5, rely=0.5, anchor="center")

        self.open_button = tk.Button(self.apks_frame, text="Open", command=self.open_apk_in_finder)
        self.decompress_button = tk.Button(self.apks_frame, text="Decompress && Open", command=self.decompress_selected_apk)

        self.search_index = 0
        self.downloaded_apks = []
        self.downloaded_search_index = 0

        self.packages = []
        self.refresh_package_list()
        self.refresh_apk_list()

        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    def decompress_selected_apk(self):
        selection = self.apks_listbox.curselection()
        if not selection:
            return
        apk_name = self.apks_listbox.get(selection[0])
        apk_path = os.path.join(LOCAL_APKS, apk_name)
        out_dir = os.path.join(LOCAL_APKS, apk_name[:-4])
        os.makedirs(out_dir, exist_ok=True)
        with zipfile.ZipFile(apk_path, 'r') as zip_ref:
            zip_ref.extractall(out_dir)
        ApkTreeViewer(out_dir)

    def list_installed_packages(self):
        r = subprocess.run(["adb", "shell", "pm", "list", "packages"], capture_output=True, text=True)
        if r.returncode != 0:
            return []
        return [line.split("package:")[-1].strip() for line in r.stdout.splitlines() if line.startswith("package:")]

    def refresh_package_list(self):
        self.packages = sorted(self.list_installed_packages())
        self.packages_listbox.delete(0, tk.END)
        for p in self.packages:
            self.packages_listbox.insert(tk.END, p)
        self.search_index = 0

    def on_package_select(self, event):
        if self.packages_listbox.curselection():
            pkg = self.packages_listbox.get(self.packages_listbox.curselection()[0])
            self.apk_entry.delete(0, tk.END)
            self.apk_entry.insert(0, pkg)

    def download_apk_gui(self):
        package_name = self.apk_entry.get()
        os.makedirs(LOCAL_APKS, exist_ok=True)
        dst = os.path.join(LOCAL_APKS, f"{package_name}.apk")
        ok = adb_pull_apk(package_name, dst)
        if ok and os.path.isfile(dst):
            self.apk_status_label.config(text=f"apk downloaded to {dst}")
        else:
            self.apk_status_label.config(text="failed to download apk")
        self.refresh_apk_list()

    def refresh_apk_list(self):
        os.makedirs(LOCAL_APKS, exist_ok=True)
        self.downloaded_apks = sorted([f for f in os.listdir(LOCAL_APKS) if f.lower().endswith(".apk")])
        self.apks_listbox.delete(0, tk.END)
        if not self.downloaded_apks:
            self.apks_listbox.pack_forget()
            self.no_apk_label.place(relx=0.5, rely=0.5, anchor="center")
            self.open_button.pack_forget()
        else:
            self.no_apk_label.place_forget()
            self.apks_listbox.pack(fill="both", expand=True, padx=5, pady=5)
            for f in self.downloaded_apks:
                self.apks_listbox.insert(tk.END, f)
            self.open_button.pack_forget()
        self.downloaded_search_index = 0

    def on_apk_select(self, event):
        selection = self.apks_listbox.curselection()
        for btn in [self.open_button, self.decompress_button]:
            btn.pack_forget()
        if selection:
            self.open_button.pack(side="left", padx=5, pady=5)
            self.decompress_button.pack(side="left", padx=5, pady=5)

    def open_apk_in_finder(self):
        selection = self.apks_listbox.curselection()
        if not selection:
            return
        apk_name = self.apks_listbox.get(selection[0])
        apk_path = os.path.join(LOCAL_APKS, apk_name)
        subprocess.run(["open", "-R", apk_path])

    def find_next_package(self):
        keyword = self.search_entry.get().strip().lower()
        if not keyword or not self.packages:
            return
        for i in range(self.search_index, len(self.packages)):
            if keyword in self.packages[i].lower():
                self.packages_listbox.selection_clear(0, tk.END)
                self.packages_listbox.selection_set(i)
                self.packages_listbox.see(i)
                self.search_index = i + 1
                return
        self.search_index = 0

    def find_next_downloaded_apk(self):
        keyword = self.apk_search_entry.get().strip().lower()
        if not keyword or not self.downloaded_apks:
            return
        for i in range(self.downloaded_search_index, len(self.downloaded_apks)):
            if keyword in self.downloaded_apks[i].lower():
                self.apks_listbox.selection_clear(0, tk.END)
                self.apks_listbox.selection_set(i)
                self.apks_listbox.see(i)
                self.downloaded_search_index = i + 1
                return
        self.downloaded_search_index = 0
