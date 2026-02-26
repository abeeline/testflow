#!/usr/bin/env bash
set -euo pipefail

# One-click VPS deploy for PocketFlow system-test web app.
# Usage:
#   sudo bash deploy/vps_deploy.sh \
#     --repo https://github.com/abeeline/testflow.git \
#     --branch main \
#     --app-dir /opt/testflow \
#     --domain your.domain.com

REPO_URL="https://github.com/abeeline/testflow.git"
BRANCH="main"
APP_DIR="/opt/testflow"
DOMAIN="_"
PORT="8010"
SERVICE_NAME="testflow-web"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO_URL="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --app-dir) APP_DIR="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --service) SERVICE_NAME="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

PROJECT_SUBDIR="cookbook/pocketflow-system-test-agent-web"
PROJECT_DIR="${APP_DIR}/${PROJECT_SUBDIR}"

echo "[1/8] Installing system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git python3 python3-venv python3-pip nginx

echo "[2/8] Cloning/updating repository..."
mkdir -p "${APP_DIR}"
if [[ -d "${APP_DIR}/.git" ]]; then
  git -C "${APP_DIR}" fetch --all --prune
  git -C "${APP_DIR}" checkout "${BRANCH}"
  git -C "${APP_DIR}" pull --ff-only origin "${BRANCH}"
else
  rm -rf "${APP_DIR}" 2>/dev/null || true
  git clone -b "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
fi

if [[ ! -f "${PROJECT_DIR}/main.py" ]]; then
  echo "ERROR: ${PROJECT_DIR}/main.py not found"
  exit 1
fi

echo "[3/8] Creating virtualenv and installing Python deps..."
rm -rf "${PROJECT_DIR}/.venv"
python3 -m venv "${PROJECT_DIR}/.venv"
VENV_PY="${PROJECT_DIR}/.venv/bin/python"
if [[ ! -x "${VENV_PY}" ]]; then
  echo "ERROR: venv python not found at ${VENV_PY}"
  exit 1
fi
"${VENV_PY}" -m pip install -U pip
"${VENV_PY}" -m pip install -r "${PROJECT_DIR}/requirements.txt"

echo "[4/8] Ensuring .env exists..."
if [[ ! -f "${PROJECT_DIR}/.env" ]]; then
  cat > "${PROJECT_DIR}/.env" <<'EOF'
# Fill your LLM settings before production use
LLM_API_BASE=
LLM_API_KEY=
LLM_MODEL=
EOF
fi

echo "[5/8] Writing systemd service..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=PocketFlow System Test Agent Web
After=network.target

[Service]
Type=simple
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/.venv/bin/uvicorn main:app --host 127.0.0.1 --port ${PORT}
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo "[6/8] Writing nginx reverse-proxy..."
cat > "/etc/nginx/sites-available/${SERVICE_NAME}" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:${PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf "/etc/nginx/sites-available/${SERVICE_NAME}" "/etc/nginx/sites-enabled/${SERVICE_NAME}"
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo "[7/8] Service health..."
systemctl --no-pager --full status "${SERVICE_NAME}" | sed -n '1,15p'

echo "[8/8] Done."
echo "Open: http://${DOMAIN}"
echo "Local health: curl http://127.0.0.1:${PORT}/"
echo "If using domain, point DNS first, then add TLS with certbot:"
echo "  apt-get install -y certbot python3-certbot-nginx"
echo "  certbot --nginx -d ${DOMAIN}"
