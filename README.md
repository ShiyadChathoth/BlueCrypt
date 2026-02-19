# BlueCrypt

BlueCrypt is a Streamlit web app for secure image steganography using:

- AES-256-GCM encryption (password hashed with SHA-256)
- Adaptive 2:2:4 LSB embedding (R=2 bits, G=2 bits, B=4 bits)
- 32-bit payload length header
- PSNR analysis for imperceptibility checks

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## Features

- `Hide Data`: Encrypt a secret file and embed it into a cover image. Output is PNG.
- `Hide Data`: Choose cover image source as uploaded image(s) or pre-generated images in `random_ai_photos`. You can randomly pick from either source.
- `Extract Data`: Recover encrypted payload from a stego image and decrypt with password.
- `Analyze`: Compare original vs stego image and compute PSNR.
