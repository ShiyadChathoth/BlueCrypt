from __future__ import annotations

from io import BytesIO
from pathlib import Path
import random

import math
import streamlit as st
from PIL import Image, UnidentifiedImageError

from bluecrypt_core import (
    BlueCryptError,
    calculate_psnr,
    decrypt_payload,
    derive_key,
    embed_encrypted_data,
    encrypt_payload,
    extract_encrypted_data,
    max_embeddable_payload_bytes,
    package_secret_file,
    unpackage_secret_file,
)


LOSSLESS_TYPES = ["png", "bmp", "tif", "tiff"]
RANDOM_AI_PHOTOS_DIR = Path(__file__).resolve().parent / "random_ai_photos"
RANDOM_SECRET_FILES_DIR = Path(__file__).resolve().parent / "random_secret_files"
LOSSLESS_EXTENSIONS = {f".{file_type}" for file_type in LOSSLESS_TYPES}


def load_image(image_source) -> Image.Image:
    try:
        if isinstance(image_source, Path):
            return Image.open(image_source).convert("RGB")

        image_source.seek(0)
        return Image.open(image_source).convert("RGB")
    except (UnidentifiedImageError, OSError, AttributeError) as exc:
        raise BlueCryptError("Unsupported image file.") from exc


def format_psnr(psnr_value: float) -> str:
    if math.isinf(psnr_value):
        return "Infinity"
    return f"{psnr_value:.2f}"


def list_random_ai_photos() -> list[Path]:
    if not RANDOM_AI_PHOTOS_DIR.exists():
        return []
    image_paths = [
        path
        for path in RANDOM_AI_PHOTOS_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in LOSSLESS_EXTENSIONS
    ]
    return sorted(image_paths, key=lambda path: str(path.relative_to(RANDOM_AI_PHOTOS_DIR)).lower())


def list_random_secret_files() -> list[Path]:
    if not RANDOM_SECRET_FILES_DIR.exists():
        return []
    secret_paths = [
        path
        for path in RANDOM_SECRET_FILES_DIR.rglob("*")
        if path.is_file() and path.name != ".gitkeep"
    ]
    return sorted(
        secret_paths,
        key=lambda path: str(path.relative_to(RANDOM_SECRET_FILES_DIR)).lower(),
    )


st.set_page_config(page_title="BlueCrypt", layout="wide")
st.title("BlueCrypt")
st.caption("Adaptive Hybrid Steganography using AES-256-GCM + 2:2:4 channel optimization")

hide_tab, extract_tab, analyze_tab = st.tabs(["Hide Data", "Extract Data", "Analyze"])

with hide_tab:
    st.subheader("Encrypt and Hide Data")
    cover_source = st.radio(
        "Cover Image Source",
        options=["Upload image(s)", "Pre-generated random_ai_photos"],
        horizontal=True,
        key="cover_source",
    )

    cover_preview = None
    cover_name = "cover"

    if cover_source == "Upload image(s)":
        cover_files = st.file_uploader(
            "Upload Cover Image(s) (PNG/BMP/TIFF)",
            type=LOSSLESS_TYPES,
            accept_multiple_files=True,
            key="hide_cover",
        )
        selected_cover = None
        if cover_files:
            if len(cover_files) == 1:
                selected_cover = cover_files[0]
            else:
                selection_mode = st.radio(
                    "Selection Mode",
                    options=["Manual", "Random"],
                    horizontal=True,
                    key="cover_selection_mode",
                )
                if selection_mode == "Manual":
                    names = [f.name for f in cover_files]
                    selected_idx = st.selectbox(
                        "Choose Cover Image",
                        options=list(range(len(cover_files))),
                        format_func=lambda i: names[i],
                        key="cover_manual_index",
                    )
                    selected_cover = cover_files[selected_idx]
                else:
                    if (
                        "cover_random_index" not in st.session_state
                        or st.session_state.cover_random_index >= len(cover_files)
                    ):
                        st.session_state.cover_random_index = random.randrange(len(cover_files))
                    if st.button("Pick Random Uploaded Image", key="pick_random_cover"):
                        st.session_state.cover_random_index = random.randrange(len(cover_files))
                    selected_cover = cover_files[st.session_state.cover_random_index]
                    st.caption(f"Randomly selected: {selected_cover.name}")

        if selected_cover:
            try:
                cover_preview = load_image(selected_cover)
                cover_name = Path(selected_cover.name).stem
            except BlueCryptError as err:
                st.error(str(err))
    else:
        pre_generated_images = list_random_ai_photos()
        selected_cover_path = None

        if not pre_generated_images:
            st.warning(
                f"No supported images found in `{RANDOM_AI_PHOTOS_DIR}`. "
                "Add PNG/BMP/TIF/TIFF files to this folder."
            )
        else:
            selection_mode = st.radio(
                "Selection Mode",
                options=["Manual", "Random"],
                horizontal=True,
                key="pre_generated_selection_mode",
            )
            if selection_mode == "Manual":
                selected_cover_path = st.selectbox(
                    "Choose Pre-generated Image",
                    options=pre_generated_images,
                    format_func=lambda p: str(p.relative_to(RANDOM_AI_PHOTOS_DIR)),
                    key="pre_generated_manual_path",
                )
            else:
                if (
                    "pre_generated_random_index" not in st.session_state
                    or st.session_state.pre_generated_random_index >= len(pre_generated_images)
                ):
                    st.session_state.pre_generated_random_index = random.randrange(
                        len(pre_generated_images)
                    )
                if st.button(
                    "Pick Random Pre-generated Image",
                    key="pick_random_pre_generated_cover",
                ):
                    st.session_state.pre_generated_random_index = random.randrange(
                        len(pre_generated_images)
                    )
                selected_cover_path = pre_generated_images[
                    st.session_state.pre_generated_random_index
                ]
                st.caption(
                    "Randomly selected: "
                    f"{selected_cover_path.relative_to(RANDOM_AI_PHOTOS_DIR)}"
                )

        if selected_cover_path:
            try:
                cover_preview = load_image(selected_cover_path)
                cover_name = selected_cover_path.stem
            except BlueCryptError as err:
                st.error(str(err))

    secret_name = None
    secret_data = None
    secret_source = st.radio(
        "Secret File Source",
        options=["Upload Secret File", "Pre-generated random_secret_files"],
        horizontal=True,
        key="secret_source",
    )

    if secret_source == "Upload Secret File":
        uploaded_secret = st.file_uploader("Upload Secret File", key="hide_secret")
        if uploaded_secret:
            secret_name = uploaded_secret.name
            secret_data = uploaded_secret.getvalue()
    else:
        pre_generated_secret_files = list_random_secret_files()
        selected_secret_path = None

        if not pre_generated_secret_files:
            st.warning(
                f"No files found in `{RANDOM_SECRET_FILES_DIR}`. "
                "Add files to this folder."
            )
        else:
            selection_mode = st.radio(
                "Secret Selection Mode",
                options=["Manual", "Random"],
                horizontal=True,
                key="pre_generated_secret_selection_mode",
            )
            if selection_mode == "Manual":
                selected_secret_path = st.selectbox(
                    "Choose Pre-generated Secret File",
                    options=pre_generated_secret_files,
                    format_func=lambda p: str(p.relative_to(RANDOM_SECRET_FILES_DIR)),
                    key="pre_generated_secret_manual_path",
                )
            else:
                if (
                    "pre_generated_secret_random_index" not in st.session_state
                    or st.session_state.pre_generated_secret_random_index
                    >= len(pre_generated_secret_files)
                ):
                    st.session_state.pre_generated_secret_random_index = random.randrange(
                        len(pre_generated_secret_files)
                    )
                if st.button(
                    "Pick Random Pre-generated Secret File",
                    key="pick_random_pre_generated_secret",
                ):
                    st.session_state.pre_generated_secret_random_index = random.randrange(
                        len(pre_generated_secret_files)
                    )
                selected_secret_path = pre_generated_secret_files[
                    st.session_state.pre_generated_secret_random_index
                ]
                st.caption(
                    "Randomly selected secret file: "
                    f"{selected_secret_path.relative_to(RANDOM_SECRET_FILES_DIR)}"
                )

        if selected_secret_path:
            try:
                secret_name = selected_secret_path.name
                secret_data = selected_secret_path.read_bytes()
            except OSError as err:
                st.error(f"Failed to read secret file: {err}")

    hide_password = st.text_input("Password", type="password", key="hide_password")

    if cover_preview:
        try:
            capacity = max_embeddable_payload_bytes(cover_preview)
            st.info(f"Maximum encrypted payload capacity: {capacity} bytes")
        except BlueCryptError as err:
            st.error(str(err))

    if st.button("Encrypt & Generate Stego PNG", key="hide_action"):
        if not cover_preview or secret_data is None or not hide_password:
            st.error("Cover image, secret file, and password are all required.")
        else:
            try:
                with st.spinner("Encrypting and embedding payload..."):
                    cover_image = cover_preview
                    key = derive_key(hide_password)
                    secret_blob = package_secret_file(secret_name, secret_data)
                    encrypted_blob = encrypt_payload(secret_blob, key)
                    stego_image = embed_encrypted_data(cover_image, encrypted_blob)

                    output_bytes = BytesIO()
                    stego_image.save(output_bytes, format="PNG")
                    stego_png = output_bytes.getvalue()

                    psnr_value = calculate_psnr(cover_image, stego_image)

                st.success("Stego image created successfully.")
                col1, col2 = st.columns(2)
                with col1:
                    st.image(cover_image, caption="Cover Image", use_container_width=True)
                with col2:
                    st.image(stego_image, caption="Stego Image", use_container_width=True)

                st.metric("PSNR (dB)", format_psnr(psnr_value))
                if not math.isinf(psnr_value) and psnr_value < 55:
                    st.warning(
                        "PSNR is below 55 dB for this payload size. "
                        "Try a larger cover image or smaller secret file."
                    )

                stego_name = f"{cover_name}_stego.png"
                st.download_button(
                    "Download Stego PNG",
                    data=stego_png,
                    file_name=stego_name,
                    mime="image/png",
                    key="download_stego",
                )
            except BlueCryptError as err:
                st.error(str(err))
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")

with extract_tab:
    st.subheader("Extract and Decrypt Data")
    stego_file = st.file_uploader(
        "Upload Stego Image (PNG/BMP/TIFF)",
        type=LOSSLESS_TYPES,
        key="extract_stego",
    )
    extract_password = st.text_input("Password", type="password", key="extract_password")

    if st.button("Extract Secret", key="extract_action"):
        if not stego_file or not extract_password:
            st.error("Stego image and password are required.")
        else:
            try:
                with st.spinner("Extracting and decrypting payload..."):
                    stego_image = load_image(stego_file)
                    key = derive_key(extract_password)
                    encrypted_blob = extract_encrypted_data(stego_image)
                    plaintext_blob = decrypt_payload(encrypted_blob, key)
                    secret = unpackage_secret_file(plaintext_blob)

                st.success("Secret data extracted successfully.")
                st.download_button(
                    "Download Extracted Secret",
                    data=secret.data,
                    file_name=secret.filename,
                    mime="application/octet-stream",
                    key="download_secret",
                )
            except BlueCryptError as err:
                st.error(str(err))
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")

with analyze_tab:
    st.subheader("Quality Analysis (PSNR)")
    original_file = st.file_uploader(
        "Upload Original Cover Image",
        type=LOSSLESS_TYPES,
        key="analyze_original",
    )
    analyzed_stego_file = st.file_uploader(
        "Upload Stego Image",
        type=LOSSLESS_TYPES,
        key="analyze_stego",
    )

    if original_file and analyzed_stego_file:
        try:
            original_image = load_image(original_file)
            analyzed_stego = load_image(analyzed_stego_file)

            if original_image.size != analyzed_stego.size:
                st.error("Both images must have the same dimensions for PSNR analysis.")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    st.image(
                        original_image,
                        caption="Original Cover Image",
                        use_container_width=True,
                    )
                with col2:
                    st.image(
                        analyzed_stego,
                        caption="Stego Image",
                        use_container_width=True,
                    )

                psnr_value = calculate_psnr(original_image, analyzed_stego)
                st.metric("PSNR (dB)", format_psnr(psnr_value))
                if math.isinf(psnr_value) or psnr_value > 55:
                    st.success("Imperceptibility target achieved (>55 dB).")
                else:
                    st.warning("PSNR below target threshold of 55 dB.")
        except BlueCryptError as err:
            st.error(str(err))
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
