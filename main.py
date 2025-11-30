"""
LAMO Converter - GUI
Requisitos: Pillow
Instalação: pip install pillow
Roda: python main.py
"""

import json
import zlib
import struct
import os
from io import BytesIO
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

# --- formato ---
MAGIC = b'LMGO'
VERSION = 1

# --- funções de I/O do formato LAMO ---
def image_to_png_bytes(img: Image.Image) -> bytes:
    bio = BytesIO()
    img.save(bio, format='PNG')
    return bio.getvalue()

def write_lamo(path: str, img: Image.Image, metadata: dict = None):
    png_bytes = image_to_png_bytes(img)
    compressed = zlib.compress(png_bytes)

    meta = metadata.copy() if metadata else {}
    meta.setdefault("width", img.width)
    meta.setdefault("height", img.height)
    meta.setdefault("mode", img.mode)
    meta.setdefault("inner_format", "PNG")
    meta_json = json.dumps(meta, ensure_ascii=False).encode('utf-8')

    with open(path, 'wb') as f:
        f.write(MAGIC)
        f.write(struct.pack('!B', VERSION))
        f.write(struct.pack('!I', len(meta_json)))
        f.write(meta_json)
        f.write(struct.pack('!I', len(compressed)))
        f.write(compressed)

def read_lamo(path: str):
    with open(path, 'rb') as f:
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError("Formato não reconhecido (magic mismatch).")
        version = struct.unpack('!B', f.read(1))[0]
        if version != VERSION:
            raise ValueError(f"Versão incompatível: {version}")

        meta_len = struct.unpack('!I', f.read(4))[0]
        meta_json = f.read(meta_len).decode('utf-8')
        metadata = json.loads(meta_json)

        data_len = struct.unpack('!I', f.read(4))[0]
        compressed = f.read(data_len)
        png_bytes = zlib.decompress(compressed)

    bio = BytesIO(png_bytes)
    img = Image.open(bio)
    img.load()
    return img, metadata

# --- utilidades ---
def convert_png_to_lamo(png_path: str, out_path: str = None):
    if out_path is None:
        out_path = os.path.splitext(png_path)[0] + ".lamo"
    img = Image.open(png_path)
    write_lamo(out_path, img, metadata={"source": os.path.basename(png_path)})
    return out_path

# --- GUI ---
class LamoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LAMO Converter")
        self.geometry("900x600")
        self.resizable(True, True)

        self.current_image = None      # PIL.Image
        self.tk_image = None           # ImageTk.PhotoImage
        self.current_meta = None
        self.current_path = None

        self.create_widgets()

    def create_widgets(self):
        # Frames
        top = ttk.Frame(self, padding=8)
        top.pack(side=tk.TOP, fill=tk.X)

        middle = ttk.Frame(self, padding=8)
        middle.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        bottom = ttk.Frame(self, padding=8)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)

        # Top buttons
        ttk.Button(top, text="Abrir PNG...", command=self.open_png).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Converter PNG → .lamo", command=self.convert_current_png).pack(side=tk.LEFT, padx=4)
        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(top, text="Abrir .lamo...", command=self.open_lamo).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Salvar reconstruído (.png)", command=self.save_reconstructed_png).pack(side=tk.LEFT, padx=4)

        # Middle: preview + metadata
        preview_frame = ttk.LabelFrame(middle, text="Preview", padding=8)
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        meta_frame = ttk.LabelFrame(middle, text="Metadata", padding=8, width=300)
        meta_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # Canvas preview (uses a label)
        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        # Metadata text
        self.meta_text = tk.Text(meta_frame, width=40, wrap=tk.WORD)
        self.meta_text.pack(fill=tk.BOTH, expand=True)

        # Bottom: info and path
        self.path_var = tk.StringVar(value="Nenhum arquivo carregado")
        ttk.Label(bottom, textvariable=self.path_var).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="Limpar", command=self.clear).pack(side=tk.RIGHT, padx=4)

    # --- ações ---
    def open_png(self):
        path = filedialog.askopenfilename(title="Abrir PNG", filetypes=[("PNG", "*.png"), ("All files", "*.*")])
        if not path:
            return
        try:
            img = Image.open(path)
            img.load()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir a imagem: {e}")
            return
        self.set_image(img, {"source": os.path.basename(path), "note": "PNG aberto"})
        self.current_path = path
        self.path_var.set(path)

    def open_lamo(self):
        path = filedialog.askopenfilename(title="Abrir .lamo", filetypes=[("LAMO files", "*.lamo"), ("All files", "*.*")])
        if not path:
            return
        try:
            img, meta = read_lamo(path)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao ler .lamo: {e}")
            return
        self.set_image(img, meta)
        self.current_path = path
        self.path_var.set(path)

    def convert_current_png(self):
        if not self.current_image:
            messagebox.showwarning("Aviso", "Carrega um PNG primeiro (Abrir PNG...)")
            return
        out = filedialog.asksaveasfilename(defaultextension=".lamo", filetypes=[("LAMO", "*.lamo")], title="Salvar como .lamo", initialfile="saida.lamo")
        if not out:
            return
        try:
            write_lamo(out, self.current_image, metadata=self.current_meta or {})
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao escrever .lamo: {e}")
            return
        messagebox.showinfo("Pronto", f"Arquivo salvo: {out}")
        self.current_path = out
        self.path_var.set(out)

    def save_reconstructed_png(self):
        if not self.current_image:
            messagebox.showwarning("Aviso", "Não há imagem para salvar.")
            return
        out = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")], title="Salvar PNG reconstruído", initialfile="reconstruido.png")
        if not out:
            return
        try:
            self.current_image.save(out, format="PNG")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar PNG: {e}")
            return
        messagebox.showinfo("Pronto", f"PNG salvo: {out}")

    def set_image(self, pil_image: Image.Image, metadata: dict):
        # salva PIL
        self.current_image = pil_image
        self.current_meta = metadata or {}

        # cria thumbnail para preview
        preview = pil_image.copy()
        preview.thumbnail((700, 500), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(preview)
        self.preview_label.configure(image=self.tk_image)

        # mostra metadata formatada
        pretty = json.dumps(self.current_meta, indent=2, ensure_ascii=False)
        self.meta_text.delete("1.0", tk.END)
        self.meta_text.insert(tk.END, pretty)

    def clear(self):
        self.current_image = None
        self.current_meta = None
        self.tk_image = None
        self.preview_label.configure(image='')
        self.meta_text.delete("1.0", tk.END)
        self.path_var.set("Nenhum arquivo carregado")
        self.current_path = None

# --- main ---
def main():
    app = LamoApp()
    app.mainloop()

if __name__ == "__main__":
    main()
