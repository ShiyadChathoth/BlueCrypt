"""Core cryptography and steganography utilities for BlueCrypt."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

import numpy as np
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes
from PIL import Image


MAGIC = b"BCP1"
NONCE_LEN = 12
TAG_LEN = 16
HEADER_LEN = 4


class BlueCryptError(Exception):
    """Raised when BlueCrypt input/output validation fails."""


@dataclass(frozen=True)
class SecretFile:
    filename: str
    data: bytes


def derive_key(password: str) -> bytes:
    """Derive a 32-byte AES key from password using SHA-256."""
    if not password:
        raise BlueCryptError("Password is required.")
    hasher = SHA256.new()
    hasher.update(password.encode("utf-8"))
    return hasher.digest()


def package_secret_file(filename: str, data: bytes) -> bytes:
    """Pack secret file metadata and bytes into a binary envelope."""
    if not data:
        raise BlueCryptError("Secret file is empty.")
    clean_name = os.path.basename(filename or "").strip() or "secret.bin"
    name_bytes = clean_name.encode("utf-8")
    if len(name_bytes) > 65535:
        raise BlueCryptError("Filename is too long.")
    return MAGIC + len(name_bytes).to_bytes(2, "big") + name_bytes + data


def unpackage_secret_file(payload: bytes) -> SecretFile:
    """Unpack binary envelope into filename and raw file bytes."""
    if len(payload) < len(MAGIC) + 2:
        raise BlueCryptError("Extracted data is too short.")
    if payload[: len(MAGIC)] != MAGIC:
        raise BlueCryptError("Invalid payload format.")

    name_len_offset = len(MAGIC)
    name_len = int.from_bytes(payload[name_len_offset : name_len_offset + 2], "big")
    data_offset = name_len_offset + 2 + name_len
    if len(payload) < data_offset:
        raise BlueCryptError("Corrupted extracted payload.")

    name_bytes = payload[name_len_offset + 2 : data_offset]
    filename = name_bytes.decode("utf-8", errors="replace").strip() or "extracted_secret.bin"
    data = payload[data_offset:]
    if not data:
        raise BlueCryptError("Extracted file content is empty.")
    return SecretFile(filename=filename, data=data)


def encrypt_payload(plaintext: bytes, key: bytes) -> bytes:
    """Encrypt payload using AES-256-GCM and return nonce+tag+ciphertext."""
    nonce = get_random_bytes(NONCE_LEN)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return nonce + tag + ciphertext


def decrypt_payload(encrypted: bytes, key: bytes) -> bytes:
    """Decrypt nonce+tag+ciphertext using AES-256-GCM."""
    min_size = NONCE_LEN + TAG_LEN
    if len(encrypted) <= min_size:
        raise BlueCryptError("Encrypted payload is too short.")
    nonce = encrypted[:NONCE_LEN]
    tag = encrypted[NONCE_LEN : NONCE_LEN + TAG_LEN]
    ciphertext = encrypted[NONCE_LEN + TAG_LEN :]

    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    try:
        return cipher.decrypt_and_verify(ciphertext, tag)
    except ValueError as exc:
        raise BlueCryptError(
            "Decryption failed. Wrong password or tampered stego image."
        ) from exc


def max_embeddable_payload_bytes(image: Image.Image) -> int:
    """
    Capacity in bytes for encrypted payload.

    2:2:4 stores exactly 1 byte per pixel.
    First 4 bytes are reserved for payload length header.
    """
    width, height = image.size
    return max((width * height) - HEADER_LEN, 0)


def _bytes_to_224_channels(data: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    red_bits = (data >> 6) & 0x03
    green_bits = (data >> 4) & 0x03
    blue_bits = data & 0x0F
    return red_bits.astype(np.uint8), green_bits.astype(np.uint8), blue_bits.astype(np.uint8)


def _channels_to_bytes(pixels: np.ndarray) -> np.ndarray:
    red_bits = (pixels[:, 0] & 0x03) << 6
    green_bits = (pixels[:, 1] & 0x03) << 4
    blue_bits = pixels[:, 2] & 0x0F
    return (red_bits | green_bits | blue_bits).astype(np.uint8)


def embed_encrypted_data(cover_image: Image.Image, encrypted_payload: bytes) -> Image.Image:
    """Embed encrypted payload into image using 2:2:4 LSB replacement."""
    if not encrypted_payload:
        raise BlueCryptError("Encrypted payload is empty.")

    capacity = max_embeddable_payload_bytes(cover_image)
    if len(encrypted_payload) > capacity:
        raise BlueCryptError(
            f"Insufficient image capacity. Need {len(encrypted_payload)} bytes, "
            f"but only {capacity} bytes available."
        )

    rgb_image = cover_image.convert("RGB")
    pixels = np.array(rgb_image, dtype=np.uint8).reshape(-1, 3)

    payload = len(encrypted_payload).to_bytes(HEADER_LEN, "big") + encrypted_payload
    payload_np = np.frombuffer(payload, dtype=np.uint8)
    red_bits, green_bits, blue_bits = _bytes_to_224_channels(payload_np)

    # val & 0xFC clears 2 LSBs in Red/Green channels; val & 0xF0 clears 4 LSBs in Blue.
    count = payload_np.size
    pixels[:count, 0] = (pixels[:count, 0] & 0xFC) | red_bits
    pixels[:count, 1] = (pixels[:count, 1] & 0xFC) | green_bits
    pixels[:count, 2] = (pixels[:count, 2] & 0xF0) | blue_bits

    stego = pixels.reshape(rgb_image.height, rgb_image.width, 3)
    return Image.fromarray(stego, mode="RGB")


def extract_encrypted_data(stego_image: Image.Image) -> bytes:
    """Extract encrypted payload from stego image using 2:2:4 LSB recovery."""
    rgb_image = stego_image.convert("RGB")
    pixels = np.array(rgb_image, dtype=np.uint8).reshape(-1, 3)
    if len(pixels) <= HEADER_LEN:
        raise BlueCryptError("Image is too small to contain BlueCrypt header.")

    header_bytes = _channels_to_bytes(pixels[:HEADER_LEN]).tobytes()
    data_len = int.from_bytes(header_bytes, "big")
    max_data_len = len(pixels) - HEADER_LEN

    if data_len <= 0 or data_len > max_data_len:
        raise BlueCryptError("Stego image does not contain a valid BlueCrypt payload.")

    payload_pixels = pixels[HEADER_LEN : HEADER_LEN + data_len]
    return _channels_to_bytes(payload_pixels).tobytes()


def calculate_psnr(image_a: Image.Image, image_b: Image.Image) -> float:
    """Calculate PSNR value (dB) between two RGB images of equal size."""
    if image_a.size != image_b.size:
        raise BlueCryptError("PSNR requires images of identical dimensions.")
    arr_a = np.array(image_a.convert("RGB"), dtype=np.float64)
    arr_b = np.array(image_b.convert("RGB"), dtype=np.float64)
    mse = np.mean((arr_a - arr_b) ** 2)
    if mse == 0:
        return math.inf
    return 20 * math.log10(255.0 / math.sqrt(mse))
