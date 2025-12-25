import tkinter as tk
import jsbeautifier

def parser_web_related(data, frame):
    pretty = jsbeautifier.beautify(data.decode())
    text = tk.Text(frame, wrap='none', height=15)
    text.insert('1.0', pretty)
    text.config(state='disabled')
    text.pack(fill='x', expand=False)