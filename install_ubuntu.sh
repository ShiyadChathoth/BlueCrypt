#!/usr/bin/env bash
set -euo pipefail

APP_ID="bluecrypt"
APP_NAME="BlueCrypt"

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.local/share/${APP_ID}"
BIN_DIR="${HOME}/.local/bin"
DESKTOP_DIR="${HOME}/.local/share/applications"
LAUNCHER_PATH="${BIN_DIR}/${APP_ID}"
DESKTOP_FILE="${DESKTOP_DIR}/${APP_ID}.desktop"

REQUIRED_FILES=(
  "app.py"
  "bluecrypt_core.py"
  "requirements.txt"
)

ensure_requirements() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required but not installed."
    exit 1
  fi

  if ! python3 -m venv --help >/dev/null 2>&1; then
    echo "python3 venv support is missing."
    echo "Install it with: sudo apt install python3-venv"
    exit 1
  fi

  for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "${SOURCE_DIR}/${file}" ]]; then
      echo "Missing required file: ${file}"
      exit 1
    fi
  done
}

copy_item() {
  local item="$1"
  if [[ -e "${SOURCE_DIR}/${item}" ]]; then
    cp -a "${SOURCE_DIR}/${item}" "${INSTALL_DIR}/"
  fi
}

write_launcher() {
  cat >"${LAUNCHER_PATH}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

APP_ID="bluecrypt"
APP_DIR="${HOME}/.local/share/${APP_ID}"
PYTHON_BIN="${APP_DIR}/.venv/bin/python"
APP_FILE="${APP_DIR}/app.py"
CACHE_DIR="${HOME}/.cache/${APP_ID}"
PID_FILE="${CACHE_DIR}/streamlit.pid"
LOG_FILE="${CACHE_DIR}/streamlit.log"
HOST="127.0.0.1"
PORT="8501"
URL="http://${HOST}:${PORT}"

if [[ ! -x "${PYTHON_BIN}" ]] || [[ ! -f "${APP_FILE}" ]]; then
  echo "BlueCrypt is not installed correctly. Re-run install_ubuntu.sh."
  exit 1
fi

is_running() {
  if [[ ! -f "${PID_FILE}" ]]; then
    return 1
  fi

  local pid
  pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
  if [[ -z "${pid}" ]]; then
    return 1
  fi

  if kill -0 "${pid}" 2>/dev/null; then
    return 0
  fi

  rm -f "${PID_FILE}"
  return 1
}

start_server() {
  mkdir -p "${CACHE_DIR}"

  if is_running; then
    return 0
  fi

  nohup "${PYTHON_BIN}" -m streamlit run "${APP_FILE}" \
    --server.headless true \
    --server.address "${HOST}" \
    --server.port "${PORT}" \
    --client.toolbarMode minimal \
    >"${LOG_FILE}" 2>&1 &
  echo "$!" >"${PID_FILE}"

  if command -v curl >/dev/null 2>&1; then
    for _ in $(seq 1 80); do
      if curl -fsS "${URL}" >/dev/null 2>&1; then
        return 0
      fi
      sleep 0.25
    done
  else
    sleep 2
  fi

  if ! is_running; then
    echo "BlueCrypt failed to start. Check log: ${LOG_FILE}"
    exit 1
  fi
}

open_browser() {
  local browser

  for browser in google-chrome google-chrome-stable chromium-browser chromium; do
    if command -v "${browser}" >/dev/null 2>&1; then
      "${browser}" --new-window --app="${URL}" >/dev/null 2>&1 &
      return 0
    fi
  done

  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${URL}" >/dev/null 2>&1 &
    return 0
  fi

  echo "Open this URL manually: ${URL}"
}

stop_server() {
  if ! is_running; then
    echo "BlueCrypt is not running."
    return 0
  fi

  local pid
  pid="$(cat "${PID_FILE}")"
  kill "${pid}" 2>/dev/null || true
  sleep 0.5

  if kill -0 "${pid}" 2>/dev/null; then
    kill -9 "${pid}" 2>/dev/null || true
  fi

  rm -f "${PID_FILE}"
  echo "BlueCrypt stopped."
}

status_server() {
  if is_running; then
    echo "BlueCrypt is running at ${URL}"
  else
    echo "BlueCrypt is not running."
  fi
}

case "${1:-open}" in
  open)
    start_server
    open_browser
    ;;
  start)
    start_server
    echo "BlueCrypt started at ${URL}"
    ;;
  stop)
    stop_server
    ;;
  restart)
    stop_server
    start_server
    echo "BlueCrypt started at ${URL}"
    ;;
  status)
    status_server
    ;;
  *)
    echo "Usage: bluecrypt [open|start|stop|restart|status]"
    exit 1
    ;;
esac
EOF

  chmod +x "${LAUNCHER_PATH}"
}

write_desktop_file() {
  cat >"${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=${APP_NAME}
Comment=Secure image steganography with AES-256-GCM
Exec=${LAUNCHER_PATH} open
Icon=security-high
Terminal=false
Categories=Utility;Security;
Keywords=steganography;encryption;bluecrypt;
StartupNotify=true
EOF
}

install_app() {
  echo "Installing ${APP_NAME}..."
  mkdir -p "${INSTALL_DIR}" "${BIN_DIR}" "${DESKTOP_DIR}"

  find "${INSTALL_DIR}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

  copy_item "app.py"
  copy_item "bluecrypt_core.py"
  copy_item "requirements.txt"
  copy_item ".streamlit"
  copy_item "random_ai_photos"
  copy_item "random_secret_files"
  copy_item "README.md"

  python3 -m venv "${INSTALL_DIR}/.venv"
  "${INSTALL_DIR}/.venv/bin/python" -m pip install --upgrade pip
  "${INSTALL_DIR}/.venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

  write_launcher
  write_desktop_file

  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${DESKTOP_DIR}" >/dev/null 2>&1 || true
  fi

  echo
  echo "Install complete."
  echo "Run from terminal: ${APP_ID}"
  echo "Run from app menu: ${APP_NAME}"
}

ensure_requirements
install_app
