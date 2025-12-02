# LAMO Converter — GUI

**Descrição**
Conversor gráfico para transformar PNG ↔ `.lamo`, o formato customizado que embala PNG comprimido + metadata dentro de um arquivo só. Interface leve em Tkinter, preview integrado e leitura/escrita completa do formato.

---

## 🔥 Download (Release)

Baixe a versão compilada aqui:
👉 **Release V2:** [https://github.com/arthurlamonattopro/LamoImage/releases/tag/V3](https://github.com/arthurlamonattopro/LamoImage/releases/tag/V3)

*(Se quiser rodar direto sem instalar Python. A interface é a mesma.)*

---

## 📦 Recursos

* Abrir e visualizar **PNG**.
* Converter images(png, jpg, webp) → **.lamo**.
* Abrir `.lamo` e reconstruir a imagem original.
* Exibir metadata completa do arquivo.
* Preview com redimensionamento automático.
* Estrutura binária documentada e fácil de expandir.

---

## 🧩 Requisitos (para rodar via fonte)

* Python 3.8+
* Pillow

Instalação:

```bash
pip install pillow
```

---

## ▶️ Como rodar (versão fonte)

```bash
python main.py
```

---

## 🧠 Estrutura do formato `.lamo`

Arquivo binário com:

* `LMGO` — assinatura (4 bytes)
* `1` — versão (1 byte)
* Tamanho do JSON (4 bytes, big-endian)
* Metadata (JSON UTF-8)
* Tamanho dos dados comprimidos (4 bytes)
* PNG comprimido (`zlib`)

Metadata mínima:

```json
{
  "width": 1920,
  "height": 1080,
  "mode": "RGB",
  "inner_format": "PNG"
}
```

---

## ✨ API interna (para devs)

* `write_lamo(path, img, metadata)` — cria `.lamo`.
* `read_lamo(path)` — lê `.lamo` e retorna `(Image, metadata)`.
* `convert_png_to_lamo(path)` — conversão rápida.
* `LamoApp` — GUI inteira em Tkinter.

---

## 🧪 Exemplos de uso

Conversão programática:

```python
from main import write_lamo, convert_png_to_lamo
convert_png_to_lamo("foto.png")
```

Adicionar metadata manualmente:

```python
from PIL import Image
img = Image.open("foto.png")
write_lamo("saida.lamo", img, {"autor": "Lamo", "descricao": "Teste"})
```

---

## ⚠️ Problemas comuns

* *"magic mismatch"* → arquivo não é `.lamo` ou está quebrado.
* PNG gigante demora no preview → normal, Tkinter respira fundo antes de renderizar.

---

## 🚀 Roadmap / sugestões

* Modo batch (converter pastas inteiras).
* Compressão configurável.
* Metadados editáveis pela interface.
* <del>melhorar segurança do formato</del>
* <del>Suporte WebP/JPEG interno.</del>

---
---

## 🤝 Contribuindo

Fork, modifique e mande PR. O mundo `.lamo` cresce contigo.
