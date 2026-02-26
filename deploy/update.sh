#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/testflow}"
APP_DIR="${APP_DIR:-$REPO_DIR/cookbook/pocketflow-system-test-agent-web}"
BRANCH="${BRANCH:-main}"
SERVICE_NAME="${SERVICE_NAME:-testflow-web}"
APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT="${APP_PORT:-8010}"

echo "[1/6] Checking directories..."
if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "Error: git repo not found: $REPO_DIR"
  exit 1
fi
if [[ ! -d "$APP_DIR" ]]; then
  echo "Error: app directory not found: $APP_DIR"
  exit 1
fi

echo "[2/6] Updating source code..."
git -C "$REPO_DIR" fetch --all --prune
git -C "$REPO_DIR" checkout "$BRANCH"
git -C "$REPO_DIR" pull --ff-only origin "$BRANCH"

echo "[3/6] Ensuring virtualenv..."
if [[ ! -x "$APP_DIR/.venv/bin/python3" ]]; then
  python3 -m venv "$APP_DIR/.venv"
fi

VENV_PY="$APP_DIR/.venv/bin/python3"

echo "[4/6] Installing dependencies..."
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r "$APP_DIR/requirements.txt"

echo "[5/6] Restarting service: $SERVICE_NAME"
if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl daemon-reload || true
  sudo systemctl restart "$SERVICE_NAME"
  sudo systemctl --no-pager -l status "$SERVICE_NAME" | sed -n '1,30p'
else
  echo "Warning: systemctl not found, skip restart."
fi

echo "[6/6] Health check..."
if command -v curl >/dev/null 2>&1; then
  if curl -fsS "http://$APP_HOST:$APP_PORT/" >/dev/null; then
    echo "OK: service is reachable at http://$APP_HOST:$APP_PORT/"
  else
    echo "Warning: health check failed at http://$APP_HOST:$APP_PORT/"
    exit 1
  fi
else
  echo "Warning: curl not found, skip health check."
fi

echo "Update completed."
