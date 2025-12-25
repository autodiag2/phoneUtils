
import tkinter as tk
from tkinter import ttk, scrolledtext, font
import subprocess, tempfile, os, string, pathlib
from phoneutils.android.lib.lib import *
import re
import xml.etree.ElementTree as ET
from tkinter import ttk
from PIL import Image, ImageTk
import io

def parser_android_manifest_bin(data, frame):
    try:
        from androguard.core.axml import AXMLPrinter
        xml_str = AXMLPrinter(data).get_xml()

        text = tk.Text(frame, wrap='none', height=15)
        text.insert('1.0', xml_str)
        text.config(state='disabled')
        text.pack(fill='x', expand=False)

        permissions = []
        intent_map = {}
        package_name = ''

        try:
            root = ET.fromstring(xml_str)
            package_name = root.attrib.get('package', '')

            for elem in root.iter('uses-permission'):
                perm = elem.attrib.get('{http://schemas.android.com/apk/res/android}name', '')
                permissions.append(perm)

            ns = '{http://schemas.android.com/apk/res/android}'

            def collect_intents(activity_tag, is_alias=False):
                for activity in root.iter(activity_tag):
                    name = activity.attrib.get(f'{ns}name', '')
                    if not name.startswith('.'):
                        component = f"{package_name}/{name}"
                    else:
                        component = f"{package_name}/{package_name}{name}"
                    for intent_filter in activity.findall('intent-filter'):
                        for action in intent_filter.findall('action'):
                            act = action.attrib.get(f'{ns}name', '')
                            if act:
                                intent_map[act] = component

            collect_intents('activity')
            collect_intents('activity-alias', is_alias=True)

        except Exception as e:
            tk.Label(frame, text=f"XML parse error: {e}").pack(anchor='w')

        if permissions:
            table_frame = tk.Frame(frame)
            table_frame.pack(fill='both', expand=True)

            tree = ttk.Treeview(table_frame, columns=('Permission',), show='headings')
            tree.heading('Permission', text='Permission')
            tree.column('Permission', anchor='w')

            for perm in permissions:
                tree.insert('', 'end', values=(perm,))
            tree.pack(fill='both', expand=True)
        else:
            tk.Label(frame, text='No permissions found').pack(anchor='w')

        if intent_map:
            tk.Label(frame, text="Intent Actions").pack(anchor='w', pady=(10, 0))
            intent_frame = tk.Frame(frame)
            intent_frame.pack(fill='both', expand=True)

            for action, component in intent_map.items():
                row = tk.Frame(intent_frame)
                row.pack(fill='x', pady=2)

                lbl = tk.Label(row, text=f"{action}", anchor='w')
                lbl.pack(side='left', fill='x', expand=True)

                def send_intent(act=action, comp=component):
                    subprocess.run(['adb', 'shell', 'am', 'start', '-a', act, '-n', comp])

                btn = tk.Button(row, text="Send Intent", command=send_intent)
                btn.pack(side='right')
        else:
            tk.Label(frame, text='No intent actions found').pack(anchor='w')

    except Exception as e:
        tk.Label(frame, text=f"Error parsing AndroidManifest: {e}").pack(anchor='w')
