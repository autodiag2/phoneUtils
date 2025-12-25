import tkinter as tk
from tkinter import ttk, scrolledtext, font
import subprocess, tempfile, os, string, pathlib
from phoneutils.android.lib.lib import *
import re
from phoneutils.android.lib.parser.all import *

class BinaryFileViewer(tk.Frame):
    def __init__(self, master, connector_type="adb"):
        super().__init__(master)
        self.font_size = 10
        self.text_font = font.Font(family='Courier', size=self.font_size)
        self.auto_fit = True
        self.current_data = b''
        self.search_matches = []
        self.current_match_index = -1
        self.selected_file_path = ''
        self.connector_type = connector_type
        self.parsers = {
            'None': lambda data, frame: None,
            'png': parser_png,
            'zip': parser_zip,
            'AndroidManifest bin': parser_android_manifest_bin,
            'txt': parser_txt,
            'font': parser_font,
            'dex': parser_dex,
            'css js json html xml': parser_web_related
        }
        self.magic_map = {
            b'\x89PNG': 'png',
            b'PK\x03\x04': 'zip'
        }
        self.extensions_map = {
            'png': 'png',
            'ttf': 'font',
            'dex': 'dex',
            'css': 'css js json html xml',
            'js': 'css js json html xml',
            'json': 'css js json html xml',
            'html': 'css js json html xml',
            'xml': 'css js json html xml'
        }

        self.pack(side="right", fill='both', expand=True)
        master.add(self)
        container = tk.PanedWindow(self, orient='horizontal')
        container.pack(fill='both', expand=True)
        self.left = tk.Frame(container)
        container.add(self.left)
        self.right = tk.Frame(container)
        container.add(self.right)

        top = tk.Frame(self.left)
        top.pack(anchor='nw', fill='x')

        buttonsAndFile = tk.Frame(top)
        buttonsAndFile.pack(fill='x', anchor='nw')
        fileFrame = tk.Frame(buttonsAndFile)
        fileFrame.pack(fill='x', anchor='w')
        self.file_label_var = tk.StringVar(self)
        self.file_label = tk.Entry(fileFrame, textvariable=self.file_label_var, state='readonly', readonlybackground='white', relief='flat')
        self.file_label.pack(side='left', fill='x', expand=True)
        buttonsFrame = tk.Frame(buttonsAndFile)
        buttonsFrame.pack(fill='x', anchor='w')
        tk.Label(buttonsFrame, text='Bytes:').pack(side='left')
        self.byte_limit = tk.Entry(buttonsFrame, width=6)
        self.byte_limit.insert(0, '500')
        self.byte_limit.pack(side='left')
        tk.Button(buttonsFrame, text='Read', command=self.read_file).pack(side='left')
        tk.Button(buttonsFrame, text='Write', command=self.write_file).pack(side='left')
        tk.Button(buttonsFrame, text='Zoom +', command=lambda: self.zoom(1)).pack(side='left')
        tk.Button(buttonsFrame, text='Zoom -', command=lambda: self.zoom(-1)).pack(side='left')
        self.underline_enabled = tk.BooleanVar(self, value=True)
        self.underline_enabled.trace_add('write', lambda *args: self.on_underline_toggle())
        tk.Checkbutton(buttonsFrame, text='Underline', variable=self.underline_enabled).pack(side='left')
        tk.Label(buttonsFrame, text='Search:').pack(side='left')
        self.search_entry = tk.Entry(buttonsFrame, width=12)
        self.search_entry.bind('<Return>', lambda e: self.find_or_next())
        self.search_entry.pack(side='left')
        self.last_query = ''
        tk.Button(buttonsFrame, text='Find', command=self.find_or_next).pack(side='left')

        self.text = scrolledtext.ScrolledText(
            self.left,
            font=self.text_font,
            wrap='none',
            undo=True,
            autoseparators=True,
            maxundo=-1,
            insertofftime=300,
            insertontime=600,
            insertwidth=2,
            insertbackground='black'
        )
        self.text.pack(fill='both', expand=True)
        self.text.bind('<KeyRelease>', self.on_hex_edit)
        self.text.bind('<Key>', self.on_key)
        self.text.bind('<<Selection>>', self.on_select)
        self.text.bind('<ButtonRelease>', self.on_cursor_move)
        self.text.bind('<Motion>', lambda e: self.after_idle(self.on_cursor_move))
        self.text.bind('<Button-1>', lambda e: self.after_idle(self.on_cursor_move))
        self.text.bind('<KeyRelease>', lambda e: self.after_idle(self.on_cursor_move))
        self.bind('<Configure>', self.adjust_font)

        viewer_top = tk.Frame(self.right)
        viewer_top.pack(fill='x')
        tk.Label(viewer_top, text='Parser:').pack(side='left')
        self.parser_choice = tk.StringVar(self, value='None')
        self.parser_box = ttk.Combobox(viewer_top, textvariable=self.parser_choice, values=list(self.parsers.keys()), state='readonly')
        self.parser_box.bind('<<ComboboxSelected>>', lambda e: self.run_parser())
        self.parser_box.pack(side='left')

        viewer_scroll = tk.Canvas(self.right)
        self.viewer_frame = tk.Frame(viewer_scroll)
        self.v_scroll = tk.Scrollbar(self.right, orient='vertical', command=viewer_scroll.yview)
        self.h_scroll = tk.Scrollbar(self.right, orient='horizontal', command=viewer_scroll.xview)
        viewer_scroll.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        viewer_scroll.pack(side='top', fill='both', expand=True)
        self.v_scroll.pack(side='right', fill='y')
        self.h_scroll.pack(side='bottom', fill='x')
        viewer_scroll.create_window((0, 0), window=self.viewer_frame, anchor='nw')
        self.viewer_frame.bind('<Configure>', lambda e: viewer_scroll.configure(scrollregion=viewer_scroll.bbox('all')))

    def detect_and_run(self):
        if self.parser_choice.get() != None and self.parser_choice.get() != "None":
            self.run_parser()
            return
        for magic, name in self.magic_map.items():
            if self.current_data.startswith(magic):
                self.parser_choice.set(name)
                self.run_parser()
                return
        for ext, name in self.extensions_map.items():
            if self.selected_file_path.endswith(ext):
                self.parser_choice.set(name)
                self.run_parser()
                return

    def run_parser(self):
        for w in self.viewer_frame.winfo_children():
            w.destroy()
        parser = self.parsers.get(self.parser_choice.get())
        if parser:
            parser(self.current_data, self.viewer_frame)

    def on_hex_edit(self, e):
        lines = self.text.get('1.0', 'end-1c').splitlines()
        hex_str = []
        for line in lines:
            if ':' not in line:
                continue
            part = line.split(':', 1)[1]
            hex_part = part.split('  ')[0]
            hex_str.extend(hex_part.strip().split())
        try:
            self.current_data = bytes.fromhex(''.join(hex_str))
            self.render(self.current_data)
        except:
            return

    def on_underline_toggle(self):
        if not self.underline_enabled.get():
            self.clear_underline_tags()

    def read_file(self):
        if not self.selected_file_path:
            return
        limit = self.byte_limit.get().strip()
        if self.connector_type == "adb":
            if limit:
                try:
                    n = int(limit)
                    data = adb_exec(['adb', 'exec-out', 'cat', self.selected_file_path])[:n]
                except:
                    data = b''
            else:
                data = adb_exec(['adb', 'exec-out', 'cat', self.selected_file_path])
        elif self.connector_type == "filesystem":
            try:
                if limit:
                    n = int(limit)
                    with open(self.selected_file_path, 'rb') as f:
                        data = f.read(n)
                else:
                    with open(self.selected_file_path, 'rb') as f:
                        data = f.read()
            except Exception:
                data = b''

        self.current_data = data
        self.render(data)
        self.detect_and_run()
        self.winfo_toplevel().title(pathlib.Path(self.selected_file_path).name)

    def write_file(self):
        content = self.text.get('1.0', 'end-1c').splitlines()
        hex_str = []
        for line in content:
            if ':' not in line:
                continue
            part = line.split(':', 1)[1]
            hex_part = part.split('  ')[0]
            hex_str.extend(hex_part.strip().split())
        try:
            data = bytes.fromhex(''.join(hex_str))
        except Exception as e:
            tk.messagebox.showwarning('Invalid Hex', f'Error parsing hex data:\n{e}')
            return
        if not self.selected_file_path:
            tk.messagebox.showwarning('No File Selected', 'Please select a file to write.')
            return
        folder=os.path.dirname(self.selected_file_path)
        if self.connector_type == "adb":
            if not adb_ensure_folder_writable(folder):
                tk.messagebox.showwarning('Write Error', f'Failed to make folder writable:\n{folder}')
                return
            tmp = tempfile.NamedTemporaryFile(delete=False)
            tmp.write(data)
            tmp.close()
            subprocess.run(['adb', 'push', tmp.name, self.selected_file_path])
            os.unlink(tmp.name)
        elif self.connector_type == "filesystem":
            try:
                with open(self.selected_file_path, 'wb') as f:
                    f.write(data)
            except Exception as e:
                tk.messagebox.showwarning('Write Error', f'Failed to write file:\n{e}')
                return
        self.current_data = data

    def zoom(self, delta):
        self.auto_fit = False
        self.font_size = max(6, self.font_size + delta)
        self.text_font.configure(size=self.font_size)
        self.text.configure(spacing3=int(self.font_size * 0.4))

    def on_key(self, e):
        if e.state & 0x04:
            if e.keysym in ('plus', 'equal'):
                self.zoom(1)
            elif e.keysym == 'minus':
                self.zoom(-1)

    def adjust_font(self, event=None):
        if not self.auto_fit:
            return
        chars = 76
        w = self.text.winfo_width()
        if w <= 0:
            return
        sz = 6
        while True:
            self.text_font.configure(size=sz)
            if self.text_font.measure('0' * chars) > w - 20:
                break
            sz += 1
        self.font_size = sz - 1
        self.text_font.configure(size=self.font_size)
        self.text.configure(spacing3=int(self.font_size * 0.4))

    def on_select(self, e):
        if not self.underline_enabled.get() or self.current_data == b'':
            return
        try:
            idx = self.text.index(tk.SEL_FIRST)
        except:
            return
        row, col = map(int, idx.split('.'))
        if not (10 <= col <= 10 + 3*16):
            return
        i = (row - 1) * 16 + (col - 10) // 3
        if not (0 <= i < len(self.current_data)):
            return
        val = self.current_data[i]
        self.clear_underline_tags()
        if val == 0:
            return
        _, pos = self.hexdump(self.current_data)
        tag = f'u_{i}'
        self.text.tag_config(tag, foreground='red', underline=1)
        for j in range(i + 1, min(i + val + 1, len(self.current_data))):
            li, bi = divmod(j, 16)
            hs, he, as_, ae = pos[li][bi]
            l = li + 1
            self.text.tag_add(tag, f'{l}.{hs}', f'{l}.{he}')
            self.text.tag_add(tag, f'{l}.{as_}', f'{l}.{ae}')

    def on_cursor_move(self, e=None):
        if not self.current_data:
            return
        try:
            index = self.text.index(tk.INSERT)
        except:
            return
        row, col = map(int, index.split('.'))
        if not (10 <= col < 10 + 3*16):
            return
        i = (row - 1) * 16 + (col - 10) // 3
        if not (0 <= i < len(self.current_data)):
            return
        self.clear_cursor_tag()
        _, pos = self.hexdump(self.current_data)
        li, bi = divmod(i, 16)
        if li >= len(pos) or bi >= len(pos[li]):
            return
        hs, he, as_, ae = pos[li][bi]
        l = li + 1
        self.text.tag_config('cursor', background='yellow')
        self.text.tag_add('cursor', f'{l}.{hs}', f'{l}.{he}')
        self.text.tag_add('cursor', f'{l}.{as_}', f'{l}.{ae}')

    def find_or_next(self):
        query = self.search_entry.get().strip()
        if not query:
            self.clear_search_tags()
            self.search_matches.clear()
            self.last_query = ''
            self.current_match_index = -1
            return

        if not self.current_data:
            return

        if not self.search_matches or self.last_query != query:
            self.search_matches.clear()
            self.clear_search_tags()
            self.last_query = query
            _, pos = self.hexdump(self.current_data)
            try:
                raw = bytes.fromhex(query)
            except:
                raw = query.encode(errors='ignore')
            for i in range(len(self.current_data) - len(raw) + 1):
                if self.current_data[i:i+len(raw)] == raw:
                    self.search_matches.append(i)
            for idx, i in enumerate(self.search_matches):
                tag = f'search_{idx}'
                self.text.tag_config(tag, background='lightblue')
                for j in range(i, i + len(raw)):
                    li, bi = divmod(j, 16)
                    hs, he, as_, ae = pos[li][bi]
                    l = li + 1
                    self.text.tag_add(tag, f'{l}.{hs}', f'{l}.{he}')
                    self.text.tag_add(tag, f'{l}.{as_}', f'{l}.{ae}')
            self.current_match_index = -1

        if not self.search_matches:
            return

        self.current_match_index = (self.current_match_index + 1) % len(self.search_matches)
        i = self.search_matches[self.current_match_index]
        row = i // 16 + 1
        self.text.see(f'{row}.0')
    
    def clear_underline_tags(self):
        for tag in self.text.tag_names():
            if tag.startswith('u_'):
                self.text.tag_delete(tag)

    def clear_cursor_tag(self):
        self.text.tag_delete('cursor')

    def clear_search_tags(self):
        for tag in self.text.tag_names():
            if tag.startswith('search_'):
                self.text.tag_delete(tag)

    def render(self, data):
        lines, _ = self.hexdump(data)
        self.text.delete('1.0', 'end')
        self.clear_underline_tags()
        self.clear_cursor_tag()
        self.clear_search_tags()
        self.text.update_idletasks()
        self.text.insert('end', ''.join(lines))
        self.text.config(font=self.text_font)
        self.text.mark_set(tk.INSERT, '1.10')
        self.text.see(tk.INSERT)
        self.text.focus_set()
        self.on_cursor_move()

    def hexdump(self, data, width=16):
        lines = []
        positions = []
        for offset in range(0, len(data), width):
            chunk = data[offset:offset+width]
            hex_parts = [f'{b:02x}' for b in chunk]
            ascii_parts = [chr(b) if chr(b) in string.printable[:-5] else '.' for b in chunk]
            lines.append(f'{offset:08x}: {" ".join(hex_parts).ljust(width*3-1)}  {"".join(ascii_parts)}\n')
            base = 10
            ascii_base = 10 + width*3 + 1
            positions.append([(base + i*3, base + i*3 + 2, ascii_base + i, ascii_base + i + 1) for i in range(len(chunk))])
        return lines, positions
    
    def on_file_selected(self, path):
        self.selected_file_path = path
        self.file_label_var.set(path)
        self.read_file()