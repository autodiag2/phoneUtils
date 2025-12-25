import subprocess, os, sys, io
from phoneutils.android.lib.lib import *

CHEAT_APPS = {
    
}


def _package_installed(pkg: str) -> bool:
    try:
        result = subprocess.run(
            ["adb", "shell", "pm", "list", "packages", pkg], capture_output=True, timeout=5
        )
        return pkg in result.stdout.decode()
    except Exception:
        return False


class CheatsTab(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.buttons = {}
        self._build()

    def _build(self):
        for idx, (name, info) in enumerate(CHEAT_APPS.items()):
            row, col = divmod(idx, 2)
            enabled = _package_installed(info["package"])
            btn = tk.Button(
                self,
                text=name,
                width=20,
                height=5,
                command=lambda l=info["launcher"]: self._open(l),
                state=tk.NORMAL if enabled else tk.DISABLED,
            )
            if not enabled:
                btn.configure(bg="#cccccc")
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            self.buttons[name] = btn
        for i in range(2):
            self.columnconfigure(i, weight=1)
        self.rowconfigure(0, weight=1)

    def _open(self, launcher):
        launcher()