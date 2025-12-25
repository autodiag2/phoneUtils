import tkinter as tk
from tkinter import ttk, scrolledtext, font
import subprocess, tempfile, os, string, pathlib
from phoneutils.android.lib.lib import *
import re
import xml.etree.ElementTree as ET
from tkinter import ttk
from PIL import Image, ImageTk
import io

from phoneutils.android.lib.parser.dex import parser_dex
from phoneutils.android.lib.parser.font import parser_font
from phoneutils.android.lib.parser.manifest_bin import parser_android_manifest_bin
from phoneutils.android.lib.parser.web import parser_web_related

def parser_png(data, frame):
    for widget in frame.winfo_children():
        widget.destroy()

    if data[:4] != b'\x89PNG':
        tk.Label(frame, text='Not a valid PNG file', fg='red').pack(anchor='w')
        return

    try:
        image = Image.open(io.BytesIO(data))
        photo = ImageTk.PhotoImage(image)
        img_label = tk.Label(frame, image=photo)
        img_label.image = photo
        img_label.pack(anchor='center', expand=True)
    except Exception as e:
        tk.Label(frame, text=f'Error displaying image: {e}', fg='red').pack(anchor='w')

def parser_zip(data, frame):
    if not data.startswith(b'PK'):
        return
    label = tk.Label(frame, text='ZIP Archive Detected', font=('Arial', 12))
    label.pack(anchor='w')
    
def parser_txt(data, frame):
    text = tk.Text(frame, wrap='none', height=15)
    text.insert('1.0', data)
    text.config(state='disabled')
    text.pack(fill='x', expand=False)
