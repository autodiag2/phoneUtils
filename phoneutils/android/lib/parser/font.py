from fontTools.ttLib import TTFont
import io

class FontLoader:
    def __init__(self, data, ext=None):
        self.font = None
        self.error = None
        self.ext = ext

        try:
            if isinstance(data, bytes):
                self.font = TTFont(io.BytesIO(data), recalcBBoxes=False, fontNumber=0)
            else:
                self.font = TTFont(data, recalcBBoxes=False, fontNumber=0)
        except Exception as e:
            self.error = f"Failed to load font: {e}"

    def list_glyphs(self):
        if not self.font:
            return []
        return self.font.getGlyphOrder()

from PIL import ImageFont, ImageDraw, Image, ImageTk
import io, tempfile, os
import tkinter as tk

def parser_font(data, frame):
    for widget in frame.winfo_children():
        widget.destroy()

    loader = FontLoader(data)
    if not loader.font:
        tk.Label(frame, text=loader.error, fg='red').pack(anchor='w')
        return

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ttf') as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        font = ImageFont.truetype(tmp_path, size=32)
        img = Image.new('RGB', (400, 80), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 20), "Font Preview", font=font, fill='black')

        os.unlink(tmp_path)

        photo = ImageTk.PhotoImage(img)
        label = tk.Label(frame, image=photo)
        label.image = photo
        label.pack(anchor='center', expand=True)

    except Exception as e:
        tk.Label(frame, text=f"Font preview error: {e}", fg='red').pack(anchor='w')