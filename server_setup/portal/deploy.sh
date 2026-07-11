#!/usr/bin/env bash
# HyeAn Portal — Ubuntu Phase 1 배포 스크립트
# sudo 없이 ~/hyean-portal 경로에 배포 (원격 SSH 환경용)
set -euo pipefail

APP_DIR="${HOME}/hyean-portal"
LOG_DIR="${HOME}/logs/hyean-portal"
REPO_URL="${REPO_URL:-https://github.com/Bright-Sunny-Kim/landing_page.git}"
BRANCH="${BRANCH:-main}"

echo "==> [1/6] Clone or update source"
if [ -d "${APP_DIR}/.git" ]; then
    cd "${APP_DIR}"
    git fetch origin
    git checkout "${BRANCH}"
    git pull origin "${BRANCH}"
elif [ -d "${APP_DIR}" ]; then
    if [ -n "$(ls -A "${APP_DIR}" 2>/dev/null)" ]; then
        echo "ERROR: ${APP_DIR} exists but is not a git repository."
        echo "Remove the directory or empty it before re-running deploy."
        exit 1
    fi
    git clone --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
    cd "${APP_DIR}"
else
    git clone --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
    cd "${APP_DIR}"
fi

echo "==> [2/6] Python venv"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "==> [3/6] Environment file"
if [ ! -f .env ]; then
    cp server_setup/portal/.env.example .env
    echo "WARNING: .env created from template. Edit ${APP_DIR}/.env before starting."
fi

echo "==> [4/6] Log directory"
mkdir -p "${LOG_DIR}"

echo "==> [5/6] Health check (manual start)"
echo "Run: cd ${APP_DIR} && source venv/bin/activate && gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 120 app:app"
echo "Test: curl http://127.0.0.1:5000/"

echo "==> [6/6] Optional: user systemd service"
echo "Copy server_setup/portal/hyean-portal-user.service to ~/.config/systemd/user/hyean-portal-user.service"
echo "Then: systemctl --user daemon-reload && systemctl --user enable --now hyean-portal-user"
echo "Done."
