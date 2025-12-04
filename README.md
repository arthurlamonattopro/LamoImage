# LAMO Converter — GUI
https://arthurlamonattopro.github.io/LamoImage/

**Descrição**
Conversor gráfico para transformar PNG ↔ `.lamo`, o formato customizado que embala PNG comprimido + metadata dentro de um arquivo só. Interface leve em Tkinter, preview integrado e leitura/escrita completa do formato.

---

## 🔥 Download (Release)

Baixe a versão compilada aqui:
👉 **Release V4:** [https://github.com/arthurlamonattopro/LamoImage/releases/tag/V4](https://github.com/arthurlamonattopro/LamoImage/releases/tag/V4)

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

# Instruções de Portabilidade para Linux e macOS

O projeto `LamoImage` consiste em dois scripts Python (`LamoViewer.py` e `conversor.py`) que utilizam a biblioteca **Pillow** para manipulação de imagens e **Tkinter** para a interface gráfica (GUI).

Como Python e suas bibliotecas são multiplataforma, o código-fonte é diretamente compatível com Linux e macOS. A portabilidade se resume a garantir que as dependências necessárias estejam instaladas em seu sistema.

## 1. Pré-requisitos

Você precisará ter o **Python 3** instalado. Recomenda-se o uso de uma versão 3.6 ou superior.

### 1.1. Dependência da Interface Gráfica (Tkinter)

O **Tkinter** é a biblioteca padrão do Python para GUI.

*   **macOS:** Geralmente, o Tkinter já vem pré-instalado com as distribuições oficiais do Python (python.org). Se você estiver usando o Python que vem com o sistema (o que não é recomendado), pode ser necessário instalá-lo separadamente.
*   **Linux:** Em muitas distribuições Linux, o Tkinter precisa ser instalado como um pacote separado do sistema.

## 2. Instalação das Dependências

Recomenda-se fortemente o uso de um **ambiente virtual** para isolar as dependências do projeto.

### Passo 1: Criar e Ativar o Ambiente Virtual

```bash
# Navegue até a pasta do projeto
cd /caminho/para/lamo_project

# Crie o ambiente virtual
python3 -m venv venv

# Ative o ambiente virtual
# No Linux/macOS:
source venv/bin/activate
```

### Passo 2: Instalar o Tkinter (Apenas Linux)

Se você estiver no **Linux**, pode ser necessário instalar o pacote `python3-tk` usando o gerenciador de pacotes do seu sistema.

| Distribuição | Comando de Instalação |
| :--- | :--- |
| **Debian/Ubuntu** | `sudo apt update && sudo apt install python3-tk` |
| **Fedora/CentOS** | `sudo dnf install python3-tkinter` |
| **Arch Linux** | `sudo pacman -S tk` |

### Passo 3: Instalar a Biblioteca Pillow

Com o ambiente virtual ativado, instale a biblioteca Pillow:

```bash
pip install Pillow
```

## 3. Execução dos Scripts

Após a instalação das dependências, você pode executar os scripts diretamente:

### 3.1. LAMO Viewer

Para iniciar o visualizador de imagens (`.lamo` e formatos comuns):

```bash
python3 LamoViewer.py
```

### 3.2. LAMO Converter

Para iniciar a ferramenta de conversão (imagens comuns para `.lamo` e vice-versa):

```bash
python3 conversor.py
```

---

**Nota sobre macOS:** Em algumas versões do macOS, o Tkinter pode ter problemas de foco ou aparência. Se isso ocorrer, a solução mais comum é garantir que você está usando uma instalação do Python obtida diretamente do site oficial do Python ou via Homebrew, e não a versão do sistema.

**Nota sobre Linux:** Certifique-se de que o seu ambiente gráfico (X server ou Wayland) está funcionando corretamente, pois o Tkinter depende dele para exibir a interface. Se você tentar rodar o script em um terminal SSH sem encaminhamento X (`ssh -X`), receberá um erro (`no display name and no $DISPLAY environment variable`).


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
