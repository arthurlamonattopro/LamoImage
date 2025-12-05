"""
LAMO Converter - GUI
Requisitos: Pillow, cryptography
Instalação: pip install pillow cryptography
Roda: python conversor.py
"""

import json
import zlib
import struct
import os
from io import BytesIO
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from PIL import Image, ImageTk, ImageFile
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from base64 import urlsafe_b64encode, urlsafe_b64decode

# --- Configurações de Segurança ---
# VULN-02: Limita o número máximo de pixels para evitar ataques de exaustão de memória (DoS)
ImageFile.MAX_IMAGE_PIXELS = 178956970
MAX_META_SIZE = 1024 * 1024  # 1MB para metadados JSON (VULN-03)
MAX_DECOMPRESSED_SIZE = 100 * 1024 * 1024  # 100MB para dados de imagem (VULN-01)

# --- formato ---
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

def encrypt_data(data: bytes, password: str, salt: bytes) -> bytes:
    key = derive_key(password, salt)
    f = Fernet(key)
    return f.encrypt(data)

def decrypt_data(data: bytes, password: str, salt: bytes) -> bytes:
    key = derive_key(password, salt)
    f = Fernet(key)
    return f.decrypt(data)

# --- funções de I/O do formato LAMO ---
def image_to_png_bytes(img: Image.Image, quality: int = 95) -> bytes:
    bio = BytesIO()
    # Salvamos o conteúdo interno como PNG (formato do payload)
    # A compressão PNG é lossless, mas a qualidade do JPEG/WEBP original é mantida
    # O parâmetro 'compress_level' do PNG controla a compressão, mas não a qualidade visual.
    # Para simular o controle de qualidade, vamos salvar como JPEG temporariamente se a qualidade for menor que 95,
    # e depois converter para PNG. Isso é uma simplificação, mas funciona para o propósito.
    # No entanto, o formato LAMO usa PNG comprimido com zlib, que é lossless.
    # Para controlar a "qualidade" da imagem final, o melhor é controlar a qualidade da imagem ANTES de salvar como PNG.
    # Como o objetivo é controlar a compressão, vamos usar o compress_level do PNG.
    # Mas para o usuário, "qualidade" é mais intuitivo. Vamos manter o PNG lossless e usar o zlib_level.
    
    # O zlib.compress já usa compressão nível 9 por padrão.
    # Para dar controle ao usuário, vamos usar o parâmetro 'quality' para o nível de compressão zlib.
    # No entanto, a função image_to_png_bytes só deve gerar os bytes PNG.
    # A compressão zlib é feita em write_lamo.
    
    # Vamos manter a função image_to_png_bytes simples e lossless.
    img.save(bio, format='PNG')
    return bio.getvalue()

def write_lamo(path: str, img: Image.Image, metadata: dict = None, password: str = None, zlib_level: int = 9):
    png_bytes = image_to_png_bytes(img)
    
    # Compressão ZLIB com nível ajustável
    compressed = zlib.compress(png_bytes, level=zlib_level)

    salt = None
    if password:
        salt = os.urandom(16)
        compressed = encrypt_data(compressed, password, salt)
        meta.setdefault("encrypted", True)
        meta.setdefault("salt", urlsafe_b64encode(salt).decode('utf-8'))

    meta = metadata.copy() if metadata else {}
    meta.setdefault("width", img.width)
    meta.setdefault("height", img.height)
    meta.setdefault("mode", img.mode)
    # tenta pegar formato original se existir
    meta.setdefault("inner_format", getattr(img, "format", "PNG") or "PNG")
    meta.setdefault("zlib_level", zlib_level) # Salva o nível de compressão

    meta_json = json.dumps(meta, ensure_ascii=False).encode('utf-8')

    # VULN-03: Checagem de tamanho para metadados JSON (embora seja gerado internamente, é uma boa prática)
    if len(meta_json) > MAX_META_SIZE:
        raise ValueError(f'Tamanho de metadados gerados excedido: {len(meta_json)} bytes')

    with open(path, 'wb') as f:
        f.write(MAGIC)
        f.write(struct.pack('!B', VERSION))
        f.write(struct.pack('!I', len(meta_json)))
        f.write(meta_json)
        f.write(struct.pack('!I', len(compressed)))
        f.write(compressed)

def read_lamo(path: str, parent=None):
    with open(path, 'rb') as f:
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError("Formato não reconhecido (magic mismatch).")
        version = struct.unpack('!B', f.read(1))[0]
        if version != VERSION:
            raise ValueError(f"Versão incompatível: {version}")

        # VULN-03: Checagem de tamanho para metadados JSON
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
        # Nota: O tamanho do chunk é arbitrário, mas 1024 é um bom ponto de partida.
        for chunk in [compressed[i:i + 1024] for i in range(0, len(compressed), 1024)]:
            png_bytes += dobj.decompress(chunk)
            decompressed_size = len(png_bytes)
            if decompressed_size > MAX_DECOMPRESSED_SIZE:
                raise ValueError('Tamanho de dados descompactados excedido (Compression Bomb)')

        png_bytes += dobj.flush()

    bio = BytesIO(png_bytes)
    # VULN-02: ImageFile.MAX_IMAGE_PIXELS já está configurado globalmente
    img = Image.open(bio)
    img.load()
    # Depois de reconstruir, define format para PNG (conteúdo interno)
    img.format = "PNG"
    return img, metadata

# --- utilidades ---
def convert_file_to_lamo(input_path: str, out_path: str = None, zlib_level: int = 9):
    # VULN-05: Garantir que o caminho de saída não permita Path Traversal
    if not out_path:
        # Usa apenas o nome do arquivo de entrada para construir o nome de saída
        base_name = os.path.basename(input_path)
        # Remove a extensão original e adiciona .lamo
        file_name_without_ext = os.path.splitext(base_name)[0]
        # Assume que o arquivo de saída deve ser criado no diretório atual
        out_path = file_name_without_ext + ".lamo"

    # VULN-02: ImageFile.MAX_IMAGE_PIXELS já está configurado globalmente
    img = Image.open(input_path)
    # garante carregamento (evita lazy load issues)
    img.load()
    write_lamo(out_path, img, metadata={"source": os.path.basename(input_path), "orig_format": getattr(img, "format", None)}, zlib_level=zlib_level)
    return out_path

def convert_png_to_lamo(png_path: str, out_path: str = None, zlib_level: int = 9):
    return convert_file_to_lamo(png_path, out_path, zlib_level)

def convert_jpg_to_lamo(jpg_path: str, out_path: str = None, zlib_level: int = 9):
    return convert_file_to_lamo(jpg_path, out_path, zlib_level)

def convert_webp_to_lamo(webp_path: str, out_path: str = None, zlib_level: int = 9):
    return convert_file_to_lamo(webp_path, out_path, zlib_level)

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
        self.password_var = tk.StringVar()
        self.encrypt_var = tk.BooleanVar()
        self.zlib_level_var = tk.IntVar(value=9) # Nível de compressão ZLIB (0-9)
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
        ttk.Button(top, text="Abrir IMAGEM...", command=self.open_image).pack(side=tk.LEFT, padx=4)
        
        # Campos de criptografia
        ttk.Checkbutton(top, text="Criptografar", variable=self.encrypt_var).pack(side=tk.LEFT, padx=4)
        ttk.Label(top, text="Senha:").pack(side=tk.LEFT, padx=2)
        ttk.Entry(top, textvariable=self.password_var, show="*", width=15).pack(side=tk.LEFT, padx=4)
        
        # Controle de compressão
        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Label(top, text="Compressão (0-9):").pack(side=tk.LEFT, padx=2)
        self.zlib_level_spinbox = tk.Spinbox(top, from_=0, to=9, textvariable=self.zlib_level_var, width=3)
        self.zlib_level_spinbox.pack(side=tk.LEFT, padx=4)

        ttk.Button(top, text="Converter imagem atual → .lamo", command=self.convert_current_image).pack(side=tk.LEFT, padx=4)
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
    def open_image(self):
        # aceita PNG, JPG/JPEG, WEBP e outros formatos que PIL entenda
        path = filedialog.askopenfilename(title="Abrir IMAGEM", filetypes=[
            ("Imagens (PNG, JPG, JPEG, WEBP)", "*.png;*.jpg;*.jpeg;*.webp"),
            ("PNG", "*.png"),
            ("JPEG", "*.jpg;*.jpeg"),
            ("WEBP", "*.webp"),
            ("Todos os arquivos", "*.*"),
        ])
        if not path:
            return
        try:
            # VULN-02: ImageFile.MAX_IMAGE_PIXELS já está configurado globalmente
            img = Image.open(path)
            img.load()
        except Exception as e:
            # VULN-04: Tratamento de erro seguro
            print(f"Erro ao abrir imagem: {e}") # Log interno para debug
            messagebox.showerror("Erro", "Não foi possível abrir a imagem. O arquivo pode estar corrompido ou o formato não é suportado.")
            return

        # metadata base
        meta = {
            "source": os.path.basename(path),
            "note": "Imagem aberta",
            "orig_format": getattr(img, "format", None)
        }
        self.set_image(img, meta)
        self.current_path = path
        self.path_var.set(path)

    def open_lamo(self):
        path = filedialog.askopenfilename(title="Abrir .lamo", filetypes=[("LAMO files", "*.lamo"), ("All files", "*.*")])
        if not path:
            return
        try:
            # VULN-01, VULN-02, VULN-03: read_lamo já está corrigido
            img, meta = read_lamo(path, parent=self)
        except Exception as e:
            # VULN-04: Tratamento de erro seguro
            print(f"Erro ao ler .lamo: {e}") # Log interno para debug
            messagebox.showerror("Erro", "Falha ao ler .lamo. O arquivo pode estar corrompido ou ser malicioso.")
            return
        # marca que veio de um .lamo
        meta = meta or {}
        meta.setdefault("source_lamo", os.path.basename(path))
        self.set_image(img, meta)
        self.current_path = path
        self.path_var.set(path)

    def convert_current_image(self):
        if not self.current_image:
            messagebox.showwarning("Aviso", "Carrega uma imagem primeiro (Abrir IMAGEM...)")
            return

        # O filedialog.asksaveasfilename já garante que o usuário está salvando em um local seguro
        out = filedialog.asksaveasfilename(defaultextension=".lamo", filetypes=[("LAMO", "*.lamo")], title="Salvar como .lamo", initialfile="saida.lamo")
        if not out:
            return
        try:
            # preserva metadata existente e marca formato original se disponível
            meta = self.current_meta.copy() if self.current_meta else {}
            meta.setdefault("source", os.path.basename(self.current_path) if self.current_path else "current_image")
            meta.setdefault("orig_format", getattr(self.current_image, "format", None))
            
            password = self.password_var.get() if self.encrypt_var.get() else None
            if self.encrypt_var.get() and not password:
                messagebox.showerror("Erro", "A criptografia está ativada, mas a senha está vazia.")
                return
            
            zlib_level = self.zlib_level_var.get()
            
            # write_lamo já tem checagem de tamanho de metadados
            write_lamo(out, self.current_image, metadata=meta, password=password, zlib_level=zlib_level)
        except Exception as e:
            # VULN-04: Tratamento de erro seguro
            print(f"Erro ao escrever .lamo: {e}") # Log interno para debug
            messagebox.showerror("Erro", "Falha ao escrever .lamo. Verifique as permissões ou o espaço em disco.")
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
            # VULN-04: Tratamento de erro seguro
            print(f"Erro ao salvar PNG: {e}") # Log interno para debug
            messagebox.showerror("Erro", "Falha ao salvar PNG. Verifique as permissões ou o espaço em disco.")
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
        self.meta_text.config(state=tk.NORMAL)
        pretty = json.dumps(self.current_meta, indent=2, ensure_ascii=False)
        self.meta_text.delete("1.0", tk.END)
        self.meta_text.insert(tk.END, pretty)

    def clear(self):
        self.current_image = None
        self.current_meta = None
        self.tk_image = None
        self.preview_label.configure(image='')
        self.meta_text.config(state=tk.NORMAL)
        self.meta_text.delete("1.0", tk.END)
        self.meta_text.config(state=tk.DISABLED)
        self.path_var.set("Nenhum arquivo carregado")
        self.current_path = None

# --- main ---
def main():
    app = LamoApp()
    app.mainloop()

if __name__ == "__main__":
    main()
