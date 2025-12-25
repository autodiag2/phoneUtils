import tkinter as tk
from tkinter import ttk, scrolledtext, font
import subprocess, tempfile, os, string, pathlib
from phoneutils.android.lib.lib import *
import re

class FileExplorer(tk.Frame):
    def __init__(self, master, on_file_selected, connector_type="filesystem", root_path="/"):
        super().__init__(master)
        self.on_file_selected = on_file_selected
        self.connector_type = connector_type
        self.root_path = root_path

        button_frame = tk.Frame(self)
        button_frame.pack(fill='x')
        tk.Button(button_frame, text='Rename', command=self.rename_item).pack(fill='x')
        tk.Button(button_frame, text='Delete', command=self.delete_item).pack(fill='x')
        tk.Button(button_frame, text='New Folder', command=self.new_folder).pack(fill='x')

        tree_frame = tk.Frame(self)
        tree_frame.pack(fill='both', expand=True)

        yscroll = ttk.Scrollbar(tree_frame, orient='vertical')
        xscroll = ttk.Scrollbar(tree_frame, orient='horizontal')

        self.tree = ttk.Treeview(tree_frame, yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.config(command=self.tree.yview)
        xscroll.config(command=self.tree.xview)

        self.tree.grid(row=0, column=0, sticky='nsew')
        yscroll.grid(row=0, column=1, sticky='ns')
        xscroll.grid(row=1, column=0, sticky='ew')

        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.tree.bind('<<TreeviewOpen>>', self.on_open)
        self.tree.bind('<Double-1>', self.on_double_click)

        style = ttk.Style(self)
        bold_font = font.Font(self, weight='bold')
        self.tree.tag_configure('dir', foreground='dark blue', font=bold_font)
        self.tree.tag_configure('link_dir', foreground='blue', font=bold_font)
        self.tree.tag_configure('link_file', foreground='blue')
        self.tree.tag_configure('exec', foreground='light green')

        root_node = self.tree.insert('', 'end', text=self.root_path, values=[self.root_path], tags=("dir",))
        self.tree.insert(root_node, 'end', text='')
        self.load_children(root_node, self.root_path)

    def load_children(self, node, path):
        kids = self.tree.get_children(node)
        if len(kids) == 1 and self.tree.item(kids[0], 'text') == '':
            self.tree.delete(kids[0])
        if self.tree.get_children(node):
            return

        if self.connector_type == "adb":
            out = adb_exec(['adb', 'shell', 'ls', '-alp', path])
            pattern = re.compile(
                r'^(?P<perms>[dlrwx-]+)\s+\d+\s+\S+\s+\S+\s+\d+\s+[\d-]+ [\d:]+ (?P<name>[^ ]+(?: -> .+)?)$'
            )
            for line in out.decode(errors='ignore').splitlines():
                if line.startswith('total'):
                    continue
                m = pattern.match(line)
                if not m:
                    continue
                perms = m.group('perms')
                name_field = m.group('name')
                if name_field in ('.', '..','./','../'):
                    continue
                if '->' in name_field:
                    name, link = map(str.strip, name_field.split('->', 1))
                else:
                    name, link = name_field, None
                is_dir = perms.startswith('d')
                is_link = perms.startswith('l')
                is_exec = 'x' in perms[1:]
                full = path.rstrip('/') + '/' + name
                tag = ''
                if is_dir:
                    tag = 'dir'
                elif is_link and link:
                    tag = 'link_dir' if is_dir else 'link_file'
                elif is_exec:
                    tag = 'exec'
                if is_dir:
                    child = self.tree.insert(node, 'end', text=name[:-1], values=[full[:-1]], tags=(tag,))
                    self.tree.insert(child, 'end', text='')
                else:
                    self.tree.insert(node, 'end', text=name, values=[full], tags=(tag,))
        else:
            try:
                for name in sorted(os.listdir(path)):
                    if name in ('.', '..'):
                        continue
                    fullpath = os.path.join(path, name)
                    is_dir = os.path.isdir(fullpath)
                    is_link = os.path.islink(fullpath)
                    is_exec = os.access(fullpath, os.X_OK)
                    tag = ''
                    if is_dir:
                        tag = 'dir'
                    elif is_link:
                        tag = 'link_file'
                    elif is_exec:
                        tag = 'exec'
                    if is_dir:
                        child = self.tree.insert(node, 'end', text=name, values=[fullpath], tags=(tag,))
                        self.tree.insert(child, 'end', text='')
                    else:
                        self.tree.insert(node, 'end', text=name, values=[fullpath], tags=(tag,))
            except Exception:
                pass

    def on_open(self, event):
        node = self.tree.focus()
        path = self.tree.item(node, 'values')[0]
        self.load_children(node, path)

    def on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        path = self.tree.item(item, 'values')[0]
        if self.connector_type == "adb":
            if path.endswith('/'):
                return
        else:
            if os.path.isdir(path):
                return
        self.on_file_selected(path)

    def get_selected_path(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.tree.item(sel[0], 'values')[0]

    def rename_item(self):
        item = self.tree.selection()
        if not item:
            return
        path = self.tree.item(item[0], 'values')[0]
        new_name = tk.simpledialog.askstring('Rename', 'New name:', initialvalue=os.path.basename(path))
        if not new_name:
            return
        parent = os.path.dirname(path)
        new_path = os.path.join(parent, new_name)
        if self.connector_type == "adb":
            adb_exec(['adb', 'shell', 'mv', path, new_path])
            self.tree.item(item[0], text=new_name, values=[new_path])
        else:
            try:
                os.rename(path, new_path)
                self.tree.item(item[0], text=new_name, values=[new_path])
            except Exception as e:
                tk.messagebox.showwarning('Rename Error', f'Failed to rename:\n{e}')

    def delete_item(self):
        item = self.tree.selection()
        if not item:
            return
        path = self.tree.item(item[0], 'values')[0]
        if not tk.messagebox.askyesno('Delete', f'Delete {path}?'):
            return
        if self.connector_type == "adb":
            adb_exec(['adb', 'shell', 'rm', '-rf', path])
            self.tree.delete(item[0])
        else:
            try:
                if os.path.isdir(path):
                    os.rmdir(path)
                else:
                    os.remove(path)
                self.tree.delete(item[0])
            except Exception as e:
                tk.messagebox.showwarning('Delete Error', f'Failed to delete:\n{e}')

    def new_folder(self):
        sel_path = self.get_selected_path()
        if not sel_path:
            return
        if self.connector_type == "adb":
            if os.path.splitext(sel_path)[1]:
                sel_path = os.path.dirname(sel_path)
            name = tk.simpledialog.askstring('New Folder', 'Folder name:')
            if not name:
                return
            new_path = sel_path.rstrip('/') + '/' + name
            if not adb_ensure_folder_writable(sel_path):
                tk.messagebox.showwarning('Error', f"Folder '{sel_path}' not writable")
                return
            adb_exec(['adb', 'shell', 'mkdir', new_path])
            node = self.tree.selection()[0]
            child = self.tree.insert(node, 'end', text=name, values=[new_path])
            self.tree.insert(child, 'end', text='')
        else:
            if os.path.isfile(sel_path):
                sel_path = os.path.dirname(sel_path)
            name = tk.simpledialog.askstring('New Folder', 'Folder name:')
            if not name:
                return
            new_path = os.path.join(sel_path, name)
            try:
                os.mkdir(new_path)
                node = self.tree.selection()[0]
                child = self.tree.insert(node, 'end', text=name, values=[new_path], tags=('dir',))
                self.tree.insert(child, 'end', text='')
            except Exception as e:
                tk.messagebox.showwarning('Error', f'Folder not created:\n{e}')