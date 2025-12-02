"""
LAMO Viewer
Um visualizador simples para arquivos .lamo (e imagens comuns) semelhante ao Fotos do Windows.
Requisitos: Pillow
Instalação: pip install pillow
Roda: python lamo_viewer.py
"""

import os
import struct
import json
import zlib
from io import BytesIO
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

MAGIC = b'LMGO'
VERSION = 1

# --- leitura do formato .lamo ---
def read_lamo(path: str):
    with open(path, 'rb') as f:
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError('Formato não reconhecido')
        version = struct.unpack('!B', f.read(1))[0]
        if version != VERSION:
            raise ValueError(f'Versão incompatível: {version}')
        meta_len = struct.unpack('!I', f.read(4))[0]
        meta_json = f.read(meta_len).decode('utf-8')
        metadata = json.loads(meta_json)
        data_len = struct.unpack('!I', f.read(4))[0]
        compressed = f.read(data_len)
        png_bytes = zlib.decompress(compressed)
    bio = BytesIO(png_bytes)
    img = Image.open(bio)
    img.load()
    img.format = 'PNG'
    return img, metadata

# --- Viewer ---
class LamoViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('LAMO Viewer')
        self.geometry('1000x700')
        self.configure(bg='black')

        # estado
        self.files = []            # lista de caminhos
        self.index = -1            # índice atual
        self.pil_image = None      # PIL.Image
        self.tk_image = None       # PhotoImage
        self.zoom = 1.0
        self.fit = True
        self.slideshow_running = False
        self.slideshow_delay = 3000  # ms

        # UI
        self.canvas = tk.Canvas(self, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # binds
        self.bind('<Right>', lambda e: self.next_image())
        self.bind('<Left>', lambda e: self.prev_image())
        self.bind('<Escape>', lambda e: self.exit_fullscreen())
        self.bind('<f>', lambda e: self.toggle_fullscreen())
        self.bind('<space>', lambda e: self.toggle_slideshow())
        self.bind('<plus>', lambda e: self.set_zoom(self.zoom * 1.25))
        self.bind('<minus>', lambda e: self.set_zoom(self.zoom / 1.25))
        self.bind('<Configure>', lambda e: self._refresh())
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Button-1>', lambda e: self.toggle_ui())

        # menu simples
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label='Abrir arquivo...', command=self.open_file)
        filemenu.add_command(label='Abrir pasta...', command=self.open_folder)
        filemenu.add_separator()
        filemenu.add_command(label='Sair', command=self.quit)
        menubar.add_cascade(label='Arquivo', menu=filemenu)

        viewmenu = tk.Menu(menubar, tearoff=0)
        viewmenu.add_command(label='Zoom 100%', command=lambda: self.set_zoom(1.0))
        viewmenu.add_command(label='Ajustar à janela', command=self.toggle_fit)
        viewmenu.add_command(label='Tela cheia (f)', command=self.toggle_fullscreen)
        menubar.add_cascade(label='Visualizar', menu=viewmenu)

        toolsmenu = tk.Menu(menubar, tearoff=0)
        toolsmenu.add_command(label='Próxima (→)', command=self.next_image)
        toolsmenu.add_command(label='Anterior (←)', command=self.prev_image)
        toolsmenu.add_command(label='Slideshow (space)', command=self.toggle_slideshow)
        menubar.add_cascade(label='Ferramentas', menu=toolsmenu)

        self.config(menu=menubar)

        # info overlay
        self.info_var = tk.StringVar()
        self.info_text = self.canvas.create_text(10, 10, anchor='nw', text='', fill='white', font=('Segoe UI', 10))

        # inicial
        self.update_info('Pronto — abra um .lamo ou uma pasta')

    def update_info(self, text: str):
        self.info_var.set(text)
        self.canvas.itemconfig(self.info_text, text=text)

    def open_file(self):
        path = filedialog.askopenfilename(title='Abrir imagem ou .lamo', filetypes=[('LAMO files', '*.lamo'), ('Imagens', '*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif'), ('Todos', '*.*')])
        if not path:
            return
        # se for .lamo, carrega apenas ele
        if path.lower().endswith('.lamo'):
            self.files = [path]
            self.index = 0
            self.load_current()
        else:
            # imagem comum
            self.files = [path]
            self.index = 0
            self.load_current()

    def open_folder(self):
        folder = filedialog.askdirectory(title='Abrir pasta')
        if not folder:
            return
        # lista .lamo e imagens comuns
        exts = ('.lamo', '.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')
        files = [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.lower().endswith(exts)]
        if not files:
            messagebox.showinfo('Nenhum arquivo', 'Nenhum .lamo ou imagem suportada encontrada na pasta')
            return
        self.files = files
        self.index = 0
        self.load_current()

    def load_current(self):
        if not (0 <= self.index < len(self.files)):
            return
        path = self.files[self.index]
        try:
            if path.lower().endswith('.lamo'):
                pil, meta = read_lamo(path)
            else:
                pil = Image.open(path)
                pil.load()
            self.pil_image = pil
            self.zoom = 1.0
            self.fit = True
            self._refresh()
            self.update_info(f'[{self.index+1}/{len(self.files)}] {os.path.basename(path)} — {pil.width}x{pil.height}')
        except Exception as e:
            messagebox.showerror('Erro', f'Falha ao abrir: {e}')

    def _refresh(self):
        if not self.pil_image:
            self.canvas.delete('IMG')
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if self.fit:
            # escala para caber na tela
            img = self.pil_image.copy()
            img.thumbnail((cw, ch), Image.LANCZOS)
            self.tk_image = ImageTk.PhotoImage(img)
            self.canvas.delete('IMG')
            self.canvas.create_image(cw//2, ch//2, image=self.tk_image, anchor='center', tags='IMG')
        else:
            # aplica zoom
            w = int(self.pil_image.width * self.zoom)
            h = int(self.pil_image.height * self.zoom)
            img = self.pil_image.resize((max(1,w), max(1,h)), Image.LANCZOS)
            self.tk_image = ImageTk.PhotoImage(img)
            self.canvas.delete('IMG')
            self.canvas.create_image(cw//2, ch//2, image=self.tk_image, anchor='center', tags='IMG')

    def next_image(self):
        if not self.files:
            return
        self.index = (self.index + 1) % len(self.files)
        self.load_current()

    def prev_image(self):
        if not self.files:
            return
        self.index = (self.index - 1) % len(self.files)
        self.load_current()

    def set_zoom(self, z: float):
        self.zoom = max(0.05, min(8.0, z))
        self.fit = False
        self._refresh()
        self.update_info(f'Zoom: {self.zoom:.2f}x')

    def toggle_fit(self):
        self.fit = not self.fit
        self._refresh()
        self.update_info('Ajustar à janela' if self.fit else 'Zoom livre')

    def toggle_fullscreen(self):
        is_full = self.attributes('-fullscreen')
        self.attributes('-fullscreen', not is_full)

    def exit_fullscreen(self):
        self.attributes('-fullscreen', False)

    def toggle_ui(self):
        # placeholder para esconder/mostrar UI (poderia esconder menubar)
        pass

    def toggle_slideshow(self):
        if self.slideshow_running:
            self.slideshow_running = False
            self.update_info('Slideshow parado')
        else:
            self.slideshow_running = True
            self.update_info('Slideshow iniciado')
            self.after(self.slideshow_delay, self._slideshow_step)

    def _slideshow_step(self):
        if not self.slideshow_running:
            return
        self.next_image()
        self.after(self.slideshow_delay, self._slideshow_step)

    def _on_mousewheel(self, event):
        # zoom com roda do mouse
        delta = event.delta
        if delta > 0:
            self.set_zoom(self.zoom * 1.1)
        else:
            self.set_zoom(self.zoom / 1.1)


if __name__ == '__main__':
    app = LamoViewer()
    app.mainloop()
