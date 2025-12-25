import zipfile, os, tempfile, tkinter as tk, sys, subprocess, datetime
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
from phoneutils.android.lib.lib import *

boot_anim_candidates = [
    "/system/media/bootanimation.zip",
    "/product/media/bootanimation.zip",
    "/data/local/bootanimation.zip",
    "/system/customize/resource/bootanimation.zip"
]
def adb_pull_bootanimation(dst):
    for src in boot_anim_candidates:
        adb_root()
        r = subprocess.run(["adb", "pull", src, dst], capture_output=True)
        if r.returncode == 0 and os.path.isfile(dst) and os.path.getsize(dst) > 0:
            return True
    return False

def adb_push_bootanimation(src):
    adb_root()
    for dst in boot_anim_candidates:
        adb_ensure_folder_writable(os.path.dirname(dst))
        r = subprocess.run(["adb", "shell", "ls", dst], capture_output=True)
        if r.returncode == 0:
            r2 = subprocess.run(["adb", "push", src, dst], capture_output=True)
            if r2.returncode == 0:
                return dst
    return None

class BootAnimationTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.frames = []
        self.delay = 0
        self.w = 0
        self.h = 0
        self.i = 0
        self.playing = False
        self.imgtk = None
        self.parts = []
        self.frame_to_part = []

        self.boot_status_label = tk.Label(self, text="")
        self.boot_status_label.pack(padx=5, pady=2, anchor="w")
        tk.Button(self, text="Download bootanimation.zip", command=self.download_boot_gui).pack(padx=5, pady=10, anchor="w")

        self.boot_path = tk.StringVar()
        tk.Entry(self, textvariable=self.boot_path, width=80).pack(padx=5, pady=2, anchor="w")
        tk.Button(self, text="Play animation on device", command=self.bootanimation_on_device).pack(padx=5, pady=10, anchor="w")
        tk.Button(self, text="Open bootanimation.zip", command=self.select_file).pack(padx=5, pady=10, anchor="w")
        tk.Button(self, text="Play/Pause", command=self.toggle_play).pack(padx=5, pady=5, anchor="w")
        self.loop_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(self, text="Loop", variable=self.loop_enabled).pack(padx=5, pady=5, anchor="w")

        upload_frame = tk.Frame(self)
        upload_frame.pack(padx=5, pady=10, anchor="w")
        tk.Label(upload_frame, text="Select bootanimation to upload:").pack(side="left")
        self.upload_path = tk.StringVar()
        tk.Entry(upload_frame, textvariable=self.upload_path, width=60).pack(side="left", padx=5)
        tk.Button(upload_frame, text="Browse", command=self.select_upload_file).pack(side="left", padx=5)
        tk.Button(upload_frame, text="Upload to device", command=self.upload_boot_gui).pack(side="left", padx=5)

        self.frame_info_label = tk.Label(self, text="")
        self.frame_info_label.pack(padx=5, pady=5)

        self.progress_var = tk.IntVar()
        self.progress_scale = tk.Scale(self, from_=0, to=0, orient="horizontal", variable=self.progress_var, showvalue=0, command=self.on_progress_changed, length=600)
        self.progress_scale.pack(padx=5, pady=5, fill="x", anchor="w")

        self.boot_canvas_frame = tk.Frame(self)
        self.boot_canvas_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.h_scroll = tk.Scrollbar(self.boot_canvas_frame, orient="horizontal")
        self.h_scroll.pack(side="bottom", fill="x")
        self.v_scroll = tk.Scrollbar(self.boot_canvas_frame, orient="vertical")
        self.v_scroll.pack(side="right", fill="y")
        self.boot_canvas = tk.Canvas(
            self.boot_canvas_frame,
            xscrollcommand=self.h_scroll.set,
            yscrollcommand=self.v_scroll.set,
            width=800, height=600
        )
        self.boot_canvas.pack(side="left", fill="both", expand=True)
        self.h_scroll.config(command=self.boot_canvas.xview)
        self.v_scroll.config(command=self.boot_canvas.yview)

        self.boot_canvas_frame.bind("<Configure>", self.on_frame_resize)
        self.canvas_size = (800, 600)

        self.progress_dragging = False
        self.progress_scale.bind("<ButtonPress-1>", self.on_progress_press)
        self.progress_scale.bind("<ButtonRelease-1>", self.on_progress_release)

    def bootanimation_on_device(self):
        adb_exec(["adb", "shell", "bootanimation"])

    def on_frame_resize(self, event):
        self.canvas_size = (self.boot_canvas_frame.winfo_width(), self.boot_canvas_frame.winfo_height())

    def get_bootanimation_folder(self):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(BASE_DIR, "data", "bootanimation")

    def download_boot_gui(self):
        codename = adb_android_codename()
        now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        dst_dir = self.get_bootanimation_folder()
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, f"{codename}-{now}.zip")
        ok = adb_pull_bootanimation(dst)
        if ok and os.path.isfile(dst):
            self.boot_status_label.config(text=f"bootanimation downloaded to {dst}")
            self.boot_path.set(dst)
        else:
            self.boot_status_label.config(text="failed to download bootanimation")

    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("Boot Animation", "*.zip")], initialdir=self.get_bootanimation_folder())
        if path:
            self.boot_path.set(path)
            self.start_animation(path)

    def select_upload_file(self):
        path = filedialog.askopenfilename(filetypes=[("Boot Animation", "*.zip")])
        if path:
            self.upload_path.set(path)

    def upload_boot_gui(self):
        src = self.upload_path.get()
        if not os.path.isfile(src):
            self.boot_status_label.config(text="No file selected for upload")
            return
        ok = adb_push_bootanimation(src)
        if ok:
            self.boot_status_label.config(text=f"Uploaded {src} to device (/data/local/bootanimation.zip)")
        else:
            self.boot_status_label.config(text="Failed to upload bootanimation to device")

    def load_bootanimation(self, zip_path):
        with zipfile.ZipFile(zip_path, 'r') as zf:
            temp_dir = tempfile.mkdtemp()
            zf.extractall(temp_dir)
        desc_path = os.path.join(temp_dir, "desc.txt")
        with open(desc_path, "r") as f:
            lines = f.read().splitlines()
        w, h, fps = map(int, lines[0].split())
        delay = 1 / fps
        frames = []
        parts = []
        frame_to_part = []
        for line in lines[1:]:
            if not line.strip():
                continue
            part = line.split()
            if len(part) < 4:
                continue
            anim_type, loop_count, pause_seconds, folder = part[:4]
            folder_path = os.path.join(temp_dir, folder)
            if not os.path.isdir(folder_path):
                continue
            imgs = sorted([os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".png")])
            if loop_count == "0":
                loop_count = len(imgs)
            else:
                loop_count = int(loop_count)
            part_name = folder
            parts.append((part_name, len(frames), len(frames)+len(imgs)*loop_count-1))
            for _ in range(loop_count):
                frames.extend(imgs)
                frame_to_part.extend([part_name] * len(imgs))
        self.parts = parts
        self.frame_to_part = frame_to_part
        return w, h, delay, frames

    def start_animation(self, path):
        self.w, self.h, self.delay, self.frames = self.load_bootanimation(path)
        self.i = 0
        self.playing = True
        self.progress_scale.config(to=len(self.frames)-1)
        self.progress_var.set(0)
        self.play()

    def play(self):
        if not self.playing or not self.frames:
            return
        if self.i >= len(self.frames):
            if self.loop_enabled.get():
                self.i = 0
            else:
                return
        self.show_frame(self.i)
        if not self.progress_dragging:
            self.progress_var.set(self.i)
        self.i += 1
        self.after(int(self.delay * 1000), self.play)

    def show_frame(self, idx):
        if not self.frames or idx >= len(self.frames):
            return
        img = Image.open(self.frames[idx])
        frame_w, frame_h = self.canvas_size
        scale = min(frame_w / self.w, frame_h / self.h)
        new_w = int(self.w * scale)
        new_h = int(self.h * scale)
        if scale < 1 or scale > 1:
            img = img.resize((new_w, new_h), Image.LANCZOS)
        self.imgtk = ImageTk.PhotoImage(img)
        self.boot_canvas.config(scrollregion=(0, 0, new_w, new_h), width=frame_w, height=frame_h)
        self.boot_canvas.delete("all")
        x = (frame_w - new_w) // 2
        y = (frame_h - new_h) // 2
        self.boot_canvas.create_image(x, y, anchor="nw", image=self.imgtk)
        part = self.frame_to_part[idx] if idx < len(self.frame_to_part) else ""
        self.frame_info_label.config(text=f"{part} {idx+1}/{len(self.frames)}")

    def toggle_play(self):
        self.playing = not self.playing
        if self.playing:
            self.play()

    def on_progress_changed(self, value):
        if self.progress_dragging:
            idx = int(float(value))
            self.i = idx
            self.show_frame(idx)
            self.frame_info_label.config(text=f"{self.frame_to_part[idx] if idx < len(self.frame_to_part) else ''} {idx+1}/{len(self.frames)}")

    def on_progress_press(self, event):
        self.progress_dragging = True
        self.playing = False

    def on_progress_release(self, event):
        self.progress_dragging = False
        idx = self.progress_var.get()
        self.i = idx
        self.show_frame(idx)
