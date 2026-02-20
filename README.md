# BlueCrypt

BlueCrypt is a Streamlit web app for secure image steganography using:

- AES-256-GCM encryption (password hashed with SHA-256)
- Adaptive 2:2:4 LSB embedding (R=2 bits, G=2 bits, B=4 bits)
- 32-bit payload length header
- PSNR analysis for imperceptibility checks

## One-Command Install (Linux + macOS, direct from Git)

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/ShiyadChathoth/BlueCrypt/main/install.sh)"
```

What this does:
- Downloads the latest code from Git and installs BlueCrypt locally
- Creates command-line launcher: `~/.local/bin/bluecrypt`
- Linux install path: `~/.local/share/bluecrypt`
- macOS install path: `~/Library/Application Support/bluecrypt`
- Linux desktop app entry: `BlueCrypt` in app menu
- macOS shortcut: `~/Applications/BlueCrypt.command`

Alternative (from a cloned repo):

```bash
git clone https://github.com/ShiyadChathoth/BlueCrypt.git BlueCrypt && cd BlueCrypt && ./install.sh
```

## Launch

- From terminal: `bluecrypt`
- Linux desktop apps: search for `BlueCrypt` and open it
- macOS Finder: open `~/Applications/BlueCrypt.command`
- If Chrome/Chromium is installed, it opens in app-window mode

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py --client.toolbarMode minimal
```

## Uninstall (Linux + macOS local install)

```bash
./uninstall.sh
```

## Features

- `Hide Data`: Encrypt a secret file and embed it into a cover image. Output is PNG.
- `Hide Data`: Choose cover image source as uploaded image(s) or pre-generated images in `random_ai_photos`. You can randomly pick from either source.
- `Hide Data`: Choose secret file source as uploaded file or pre-generated files in `random_secret_files`. You can randomly pick from either source.
- `Extract Data`: Recover encrypted payload from a stego image and decrypt with password.
- `Analyze`: Compare original vs stego image and compute PSNR.
