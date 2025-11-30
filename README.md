# LAMO Converter — GUI

**Descrição**
Conversor gráfico simples entre PNG e o formato proprietário `.lamo`. Inclui interface Tkinter para abrir, visualizar, converter e reconstruir imagens.

---

## Recursos

* Abrir e visualizar arquivos **PNG**.
* Converter PNG → **.lamo** (formato custom: PNG comprimido + metadata).
* Abrir **.lamo** e reconstruir/salvar como PNG.
* Exibir metadata embutida no arquivo `.lamo`.
* Interface gráfica leve (Tkinter) com preview e painel de metadata.

---

## Requisitos

* Python 3.8+ (testado em 3.10/3.11)
* Biblioteca Pillow

Instale dependências:

```bash
pip install pillow
```

---

## Como rodar

```bash
python main.py
```

A janela vai abrir: use os botões no topo para abrir/convertir e salvar.

---

## Formato `.lamo` (resumo técnico)

Estrutura binária do arquivo `.lamo`:

* 4 bytes: `MAGIC = b'LMGO'`
* 1 byte: `VERSION` (atualmente `1`)
* 4 bytes: tamanho do JSON de metadata (big-endian uint32)
* N bytes: JSON de metadata (UTF-8)
* 4 bytes: tamanho dos dados comprimidos (big-endian uint32)
* M bytes: PNG original comprimido com `zlib`

A metadata inclui, por padrão:

```json
{
  "width": <int>,
  "height": <int>,
  "mode": "<PIL mode>",
  "inner_format": "PNG",
  ... outros campos opcionais ...
}
```

---

## Funções principais do script

* `image_to_png_bytes(img: Image.Image) -> bytes` — converte PIL → bytes PNG.
* `write_lamo(path: str, img: Image.Image, metadata: dict = None)` — grava `.lamo`.
* `read_lamo(path: str) -> (Image, metadata)` — lê `.lamo` e retorna PIL.Image + metadata.
* `convert_png_to_lamo(png_path: str, out_path: str = None)` — helper para conversão em lote/CLI.
* `LamoApp` — classe Tkinter que implementa a GUI (abrir, visualizar, salvar, converter).

---

## Uso rápido (exemplos)

Converter pela GUI:

1. `python main.py`
2. `Abrir PNG...` → `Converter PNG → .lamo` → escolha local para salvar.

Converter via função (script/CLI/automação):

```python
from PIL import Image
from main import write_lamo, convert_png_to_lamo

# simples
convert_png_to_lamo("exemplo.png")  # gera exemplo.lamo

# com metadata extra
img = Image.open("exemplo.png")
write_lamo("saida.lamo", img, metadata={"autor": "Lamo", "desc": "Exemplo"})
```

---

## Erros comuns / Dicas

* **"Formato não reconhecido (magic mismatch)"**: arquivo não é `.lamo` ou está corrompido.
* Se `/` problemas de permissão ao salvar, execute com permissão correta ou escolha outro diretório.
* Para imagens muito grandes, o preview redimensiona para caber na janela; a imagem original não é alterada.

---

## Contribuindo

Fork, ajuste e faça PRs. Algumas ideias:

* Suporte a outros formatos internos (ex: WebP).
* Compactação configurável (zlib level).
* Suporte a lote (converter pastas inteiras).
* Exportar metadata como JSON separado.

---

## Licença

Coloque a licença que preferir (MIT recomendada para projetos pequenos). Quer que eu adicione um `LICENSE` MIT já pronto?

---

## Contato

Criado por **Lamo** — use com parcimônia e senso estético.
Precisa que eu traduza pro inglês, gere um pacote pip ou crie interface mais bonita com QT/Tkmodern?
