import zipfile, os, tempfile, tkinter as tk, sys
from tkinter import filedialog
from PIL import Image, ImageTk

def load_bootanimation(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zf:
        temp_dir = tempfile.mkdtemp()
        zf.extractall(temp_dir)
    desc_path = os.path.join(temp_dir, "desc.txt")
    with open(desc_path, "r") as f:
        lines = f.read().splitlines()
    w, h, fps = map(int, lines[0].split())
    delay = 1 / fps
    frames = []
    for line in lines[1:]:
        if not line.strip(): continue
        part = line.split()
        if len(part) < 4: continue
        anim_type, loop_count, pause_seconds, folder = part[:4]
        folder_path = os.path.join(temp_dir, folder)
        if not os.path.isdir(folder_path): continue
        imgs = sorted([os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".png")])
        if loop_count == "0": loop_count = len(imgs)
        else: loop_count = int(loop_count)
        for _ in range(loop_count): frames.extend(imgs)
    return w, h, delay, frames

def select_file():
    path = filedialog.askopenfilename(filetypes=[("Boot Animation", "*.zip")])
    if path:
        start_animation(path)

def start_animation(path):
    global frames, delay, w, h, i, playing
    w, h, delay, frames = load_bootanimation(path)
    canvas.config(scrollregion=(0, 0, w, h), width=min(800, w), height=min(600, h))
    i = 0
    playing = True
    play()

def play():
    global i, imgtk
    if not playing or not frames: return
    if i >= len(frames):
        if loop_enabled.get():
            i = 0
        else:
            return
    img = Image.open(frames[i])

    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    scale = min(screen_w / w, screen_h / h) - 0.1
    new_w = int(w * scale)
    new_h = int(h * scale)

    imgtk = ImageTk.PhotoImage(img.resize((new_w, new_h)))
    canvas.config(scrollregion=(0, 0, new_w, new_h), width=new_w, height=new_h)
    canvas.create_image(0, 0, anchor="nw", image=imgtk)

    i += 1
    root.after(int(delay * 1000), play)

def toggle_play():
    global playing
    playing = not playing
    if playing: play()

root = tk.Tk()
root.title("Bootanimation Viewer")
root.attributes('-topmost', True)

frame = tk.Frame(root)
frame.pack()

tk.Button(frame, text="Open bootanimation.zip", command=select_file).pack(side="left", padx=5)
tk.Button(frame, text="Play/Pause", command=toggle_play).pack(side="left", padx=5)
loop_enabled = tk.BooleanVar(value=True)
tk.Checkbutton(frame, text="Loop", variable=loop_enabled).pack(side="left", padx=5)

canvas_frame = tk.Frame(root)
canvas_frame.pack(fill="both", expand=True)

h_scroll = tk.Scrollbar(canvas_frame, orient="horizontal")
h_scroll.pack(side="bottom", fill="x")
v_scroll = tk.Scrollbar(canvas_frame, orient="vertical")
v_scroll.pack(side="right", fill="y")

canvas = tk.Canvas(canvas_frame, xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
canvas.pack(side="left", fill="both", expand=True)

h_scroll.config(command=canvas.xview)
v_scroll.config(command=canvas.yview)

frames, delay, w, h, i, playing = [], 0, 0, 0, 0, False
imgtk = None

if len(sys.argv) > 1:
    preload_path = sys.argv[1]
    if os.path.isfile(preload_path):
        start_animation(preload_path)

root.mainloop()
