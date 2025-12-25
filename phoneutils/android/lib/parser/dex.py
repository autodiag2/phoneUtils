import tkinter as tk
from tkinter import ttk, scrolledtext, font
import subprocess, tempfile, os, string, pathlib
from phoneutils.android.lib.lib import *
import re
import xml.etree.ElementTree as ET
from tkinter import ttk
from PIL import Image, ImageTk
import io

def parser_dex(data, frame):
    for widget in frame.winfo_children():
        widget.destroy()

    text_widget = scrolledtext.ScrolledText(frame, wrap='none', font=('Courier', 9))
    text_widget.pack(fill='both', expand=True)
    
    from loguru import logger
    logger.remove()
    logger.add(lambda _: None, level="ERROR")

    from androguard.decompiler.decompiler import decompile
    from androguard.misc import AnalyzeDex

    try:

        with tempfile.NamedTemporaryFile(delete=False, suffix='.dex') as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        _, vm, dx = AnalyzeDex(tmp_path)

        for cls in vm.get_classes():
            text_widget.insert('end', f'\nClass: {cls.get_name()}\n')
            for method in cls.get_methods():
                ma = dx.get_method(method)
                if ma is None:
                    continue
                try:
                    d = decompile.DvMethod(ma)
                    d.process()
                    source = d.get_source()
                    text_widget.insert('end', f"{source}\n\n")
                except Exception as e:
                    text_widget.insert('end', f"Error decompiling method: {e}\n")

        text_widget.config(state='disabled')

    except Exception as e:
        tk.Label(frame, text=f"DEX parsing error: {e}", fg='red').pack(anchor='w')
