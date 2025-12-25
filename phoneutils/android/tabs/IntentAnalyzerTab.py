import os, tkinter as tk
from tkinter import ttk
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from androguard.core.axml import AXMLPrinter

LOCAL_APKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "apk")

class IntentAnalyzerTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        control_frame = tk.Frame(self)
        control_frame.pack(fill='x', padx=5, pady=5)

        tk.Label(control_frame, text="Target packages (space-separated):").pack(anchor='w')
        self.pkg_entry = tk.Entry(control_frame)
        self.pkg_entry.pack(fill='x', pady=(0, 5))

        btn_frame = tk.Frame(control_frame)
        btn_frame.pack(fill='x')

        self.load_btn = tk.Button(btn_frame, text="Download Intents", command=self.load_selected_packages)
        self.load_btn.pack(side='left')

        self.load_all_btn = tk.Button(btn_frame, text="Download All", command=self.load_all_apks)
        self.load_all_btn.pack(side='left', padx=10)

        tk.Label(self, text="Search:").pack(anchor='w', padx=5)
        self.search_entry = tk.Entry(self)
        self.search_entry.pack(fill='x', padx=5)
        self.search_entry.bind('<KeyRelease>', self.update_filter)

        self.progress_label = tk.Label(self, text="Idle")
        self.progress_label.pack(anchor='w', padx=5, pady=(5, 0))

        self.progressbar = ttk.Progressbar(self, mode='determinate')
        self.progressbar.pack(fill='x', padx=5, pady=(0, 5))

        table_frame = tk.Frame(self)
        table_frame.pack(fill='both', expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(table_frame, columns=('pkg', 'action', 'btn'), show='headings')
        self.tree.heading('pkg', text='Target Package')
        self.tree.heading('action', text='Intent Action')
        self.tree.heading('btn', text='')

        self.tree.column('pkg', anchor='w', width=250)
        self.tree.column('action', anchor='w', width=300)
        self.tree.column('btn', anchor='center', width=100)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        self.buttons = {}
        self.pack(fill='both', expand=True)

        self.packages = []
        self.current_index = 0

        self.tree.bind("<Button-1>", self.handle_click_event)
        self.tree.bind("<Motion>", self.handle_mouse_motion)
        self.tree.bind("<Leave>", lambda e: self.tree.configure(cursor=""))

    def update_filter(self, event=None):
        q = self.search_entry.get().lower()
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            text = f"{values[0]} {values[1]}".lower()
            visible = q in text
            self.tree.detach(item) if not visible else self.tree.reattach(item, '', 'end')

    def load_selected_packages(self):
        input_text = self.pkg_entry.get().strip()
        if not input_text:
            return
        self.packages = input_text.split()
        self.start_processing()

    def load_all_apks(self):
        self.packages = self.list_installed_packages()
        self.start_processing()

    def start_processing(self):
        self.current_index = 0
        self.progressbar['maximum'] = len(self.packages)
        self.progressbar['value'] = 0
        self.progress_label.config(text=f"0 / {len(self.packages)}")
        self.after(100, self.process_next_package)

    def process_next_package(self):
        if self.current_index >= len(self.packages):
            self.progress_label.config(text="Done")
            return

        pkg = self.packages[self.current_index]
        apk_path = self.get_apk_path(pkg)
        if apk_path:
            local_apk = os.path.join(LOCAL_APKS, f"{pkg}.apk")
            subprocess.run(["adb", "pull", apk_path, local_apk], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            extract_dir = os.path.join(LOCAL_APKS, pkg)
            os.makedirs(extract_dir, exist_ok=True)
            try:
                with zipfile.ZipFile(local_apk, 'r') as zip_ref:
                    zip_ref.extract('AndroidManifest.xml', path=extract_dir)
                axml = open(os.path.join(extract_dir, 'AndroidManifest.xml'), 'rb').read()
                xml_str = AXMLPrinter(axml).get_xml()
                self.parse_manifest(xml_str, pkg)
            except:
                pass

        self.current_index += 1
        self.progressbar['value'] = self.current_index
        self.progress_label.config(text=f"{self.current_index} / {len(self.packages)}")
        self.after(10, self.process_next_package)

    def list_installed_packages(self):
        r = subprocess.run(["adb", "shell", "pm", "list", "packages"], capture_output=True, text=True)
        return [line.split("package:")[-1].strip() for line in r.stdout.splitlines() if line.startswith("package:")]

    def get_apk_path(self, pkg):
        r = subprocess.run(["adb", "shell", "pm", "path", pkg], capture_output=True, text=True)
        if r.returncode != 0:
            return None
        for line in r.stdout.splitlines():
            if line.startswith("package:"):
                return line.strip().split("package:")[-1]
        return None

    def parse_manifest(self, xml_str, package_name):
        try:
            root = ET.fromstring(xml_str)
            ns = '{http://schemas.android.com/apk/res/android}'

            def collect_intents(tag):
                for node in root.iter(tag):
                    name = node.attrib.get(f'{ns}name', '')
                    component = name if not name.startswith('.') else package_name + name
                    component = package_name + "/" + component
                    for intent_filter in node.findall('intent-filter'):
                        for action in intent_filter.findall('action'):
                            act = action.attrib.get(f'{ns}name', '')
                            if act:
                                self.insert_intent(package_name, act, component)

            collect_intents('activity')
            collect_intents('activity-alias')
        except:
            pass

    def insert_intent(self, pkg, action, component):
        iid = self.tree.insert('', 'end', values=(pkg, action, 'Send'))
        self.buttons[iid] = (action, component)

    def handle_click_event(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        if col != "#3":  # "Send" column
            return
        row_id = self.tree.identify_row(event.y)
        if row_id in self.buttons:
            action, component = self.buttons[row_id]
            self.send_intent(action, component)

    def send_intent(self, action, component):
        subprocess.run(['adb', 'shell', 'am', 'start', '-a', action, '-n', component])

    def handle_mouse_motion(self, event):
        region = self.tree.identify_region(event.x, event.y)
        col = self.tree.identify_column(event.x)
        if region == "cell" and col == "#3":
            self.tree.configure(cursor="hand2")
        else:
            self.tree.configure(cursor="")
