"""
LAMO Viewer
Um visualizador simples para arquivos .lamo (e imagens comuns) semelhante ao Fotos do Windows.
Requisitos: Pillow, cryptography
Instalação: pip install pillow cryptography
Roda: python lamo_viewer.py
"""

import os
import struct
import json
import zlib
from io import BytesIO
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from PIL import Image, ImageTk, ImageFile
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from base64 import urlsafe_b64encode, urlsafe_b64decode

# --- Configurações de Segurança ---
# VULN-03: Limita o número máximo de pixels para evitar ataques de exaustão de memória (DoS)
# 178956970 pixels é o limite padrão do Pillow (aprox. 178.9 MP)
ImageFile.MAX_IMAGE_PIXELS = 178956970
MAX_META_SIZE = 1024 * 1024  # 1MB para metadados JSON (VULN-02)
MAX_DECOMPRESSED_SIZE = 100 * 1024 * 1024  # 100MB para dados de imagem (VULN-01)

MAGIC = b'LMGO'
VERSION = 1

# --- funções de criptografia ---
def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000, # Recomendado pelo OWASP
    )
    key = urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def decrypt_data(data: bytes, password: str, salt: bytes) -> bytes:
    key = derive_key(password, salt)
    f = Fernet(key)
    return f.decrypt(data)

# --- leitura do formato .lamo ---
def read_lamo(path: str, parent=None):
    with open(path, 'rb') as f:
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError('Formato não reconhecido')
        version = struct.unpack('!B', f.read(1))[0]
        if version != VERSION:
            raise ValueError(f'Versão incompatível: {version}')

        # VULN-02: Checagem de tamanho para metadados JSON
        meta_len = struct.unpack('!I', f.read(4))[0]
        if meta_len > MAX_META_SIZE:
            raise ValueError(f'Tamanho de metadados excedido: {meta_len} bytes')

        meta_json = f.read(meta_len).decode('utf-8')
        metadata = json.loads(meta_json)

        # VULN-01: Checagem de tamanho para dados comprimidos
        data_len = struct.unpack('!I', f.read(4))[0]
        if data_len > MAX_DECOMPRESSED_SIZE: # Usando o mesmo limite como um proxy
            raise ValueError(f'Tamanho de dados comprimidos excedido: {data_len} bytes')

        compressed = f.read(data_len)

        # --- Descriptografia (se necessário) ---
        if metadata.get("encrypted"):
            password = simpledialog.askstring("Senha", "O arquivo .lamo está criptografado. Digite a senha:", show='*', parent=parent)
            if not password:
                raise ValueError("Operação cancelada. Senha necessária para descriptografar.")
            
            salt = urlsafe_b64decode(metadata.get("salt").encode('utf-8'))
            
            try:
                compressed = decrypt_data(compressed, password, salt)
            except Exception as e:
                raise ValueError(f"Falha na descriptografia. Senha incorreta ou arquivo corrompido: {e}")

        # VULN-01: Descompressão segura com limite de tamanho
        dobj = zlib.decompressobj()
        png_bytes = b''
        decompressed_size = 0

        # Descomprime em blocos para checar o tamanho total
        for chunk in [compressed[i:i + 1024] for i in range(0, len(compressed), 1024)]:
            png_bytes += dobj.decompress(chunk)
            decompressed_size = len(png_bytes)
            if decompressed_size > MAX_DECOMPRESSED_SIZE:
                raise ValueError('Tamanho de dados descompactados excedido (Compression Bomb)')

        png_bytes += dobj.flush()

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
        
        # --- Configuração do Tema Escuro ---
        style = ttk.Style(self)
        style.theme_use('clam') # Um tema base mais moderno
        
        # Cores para o tema escuro
        DARK_BG = '#2e2e2e'
        DARK_FG = '#ffffff'
        DARK_ACTIVE = '#4a4a4a'
        DARK_BORDER = '#1e1e1e'
        
        self.configure(bg=DARK_BG)
        
        # Configuração geral do estilo
        style.configure('.', background=DARK_BG, foreground=DARK_FG, bordercolor=DARK_BORDER)
        style.configure('TFrame', background=DARK_BG)
        style.configure('TLabel', background=DARK_BG, foreground=DARK_FG)
        style.configure('TButton', background=DARK_BG, foreground=DARK_FG)
        style.map('TButton', background=[('active', DARK_ACTIVE)])
        style.configure('TMenu', background=DARK_BG, foreground=DARK_FG)
        
        # Configuração do Menu (tk.Menu não usa ttk.Style diretamente, mas tentamos)
        self.option_add('*Menu.background', DARK_BG)
        self.option_add('*Menu.foreground', DARK_FG)
        self.option_add('*Menu.activeBackground', DARK_ACTIVE)
        self.option_add('*Menu.activeForeground', DARK_FG)
        
        # --- Fim da Configuração do Tema Escuro ---

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
        # O canvas deve usar a cor de fundo escura
        self.canvas = tk.Canvas(self, bg=DARK_BG, highlightthickness=0)
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
        # O texto deve usar a cor de primeiro plano escura
        self.info_text = self.canvas.create_text(10, 10, anchor='nw', text='', fill=DARK_FG, font=('Segoe UI', 10))

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
                pil, meta = read_lamo(path, parent=self)
            else:
                # VULN-03: ImageFile.MAX_IMAGE_PIXELS já está configurado globalmente
                pil = Image.open(path)
                pil.load()
            self.pil_image = pil
            self.zoom = 1.0
            self.fit = True
            self._refresh()
            self.update_info(f'[{self.index+1}/{len(self.files)}] {os.path.basename(path)} — {pil.width}x{pil.height}')
        except Exception as e:
            # VULN-04: Tratamento de erro seguro - não expõe detalhes internos da exceção
            print(f"Erro ao carregar {path}: {e}") # Log interno para debug
            messagebox.showerror('Erro', 'Falha ao abrir o arquivo. O arquivo pode estar corrompido ou o formato não é suportado.')

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
