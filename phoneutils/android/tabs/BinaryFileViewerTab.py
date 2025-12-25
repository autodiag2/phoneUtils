import tkinter as tk
from tkinter import ttk, scrolledtext, font
import subprocess, tempfile, os, string, pathlib
from phoneutils.android.lib.lib import *
import re
from phoneutils.android.lib.BinaryFileViewer import BinaryFileViewer
from phoneutils.android.lib.FileExplorer import FileExplorer

class BinaryViewerTab(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        paned = tk.PanedWindow(self, orient='horizontal')
        paned.pack(fill='both', expand=True)
        nav_frame = FileExplorer(paned, self.on_file_selected, connector_type="adb")
        paned.add(nav_frame)
        self.readFileFrame = BinaryFileViewer(paned, connector_type="adb")

    def on_file_selected(self, path):
        self.readFileFrame.on_file_selected(path)