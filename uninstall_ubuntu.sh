#!/usr/bin/env bash
set -euo pipefail

APP_ID="bluecrypt"
APP_NAME="BlueCrypt"
INSTALL_DIR="${HOME}/.local/share/${APP_ID}"
BIN_PATH="${HOME}/.local/bin/${APP_ID}"
DESKTOP_FILE="${HOME}/.local/share/applications/${APP_ID}.desktop"
CACHE_DIR="${HOME}/.cache/${APP_ID}"

if [[ -x "${BIN_PATH}" ]]; then
  "${BIN_PATH}" stop >/dev/null 2>&1 || true
fi

rm -rf "${INSTALL_DIR}" "${CACHE_DIR}"
rm -f "${BIN_PATH}" "${DESKTOP_FILE}"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${HOME}/.local/share/applications" >/dev/null 2>&1 || true
fi

echo "${APP_NAME} has been removed."
