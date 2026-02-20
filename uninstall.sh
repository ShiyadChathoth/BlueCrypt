#!/usr/bin/env bash
set -euo pipefail

APP_ID="bluecrypt"
APP_NAME="BlueCrypt"
OS_NAME="$(uname -s)"

case "${OS_NAME}" in
  Linux)
    INSTALL_DIR="${HOME}/.local/share/${APP_ID}"
    CACHE_DIR="${HOME}/.cache/${APP_ID}"
    DESKTOP_FILE="${HOME}/.local/share/applications/${APP_ID}.desktop"
    MAC_SHORTCUT=""
    ;;
  Darwin)
    INSTALL_DIR="${HOME}/Library/Application Support/${APP_ID}"
    CACHE_DIR="${HOME}/Library/Caches/${APP_ID}"
    DESKTOP_FILE=""
    MAC_SHORTCUT="${HOME}/Applications/${APP_NAME}.command"
    ;;
  *)
    echo "Unsupported OS: ${OS_NAME}. Supported: Linux, macOS."
    exit 1
    ;;
esac

BIN_PATH="${HOME}/.local/bin/${APP_ID}"

if [[ -x "${BIN_PATH}" ]]; then
  "${BIN_PATH}" stop >/dev/null 2>&1 || true
fi

rm -rf "${INSTALL_DIR}" "${CACHE_DIR}"
rm -f "${BIN_PATH}"

if [[ -n "${DESKTOP_FILE}" ]]; then
  rm -f "${DESKTOP_FILE}"
fi

if [[ -n "${MAC_SHORTCUT}" ]]; then
  rm -f "${MAC_SHORTCUT}"
fi

if [[ "${OS_NAME}" == "Linux" ]] && command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${HOME}/.local/share/applications" >/dev/null 2>&1 || true
fi

echo "${APP_NAME} has been removed."
