#!/usr/bin/env bash
# deploy.sh - One-shot bootstrap for asa-overseer on Oracle VM (Ubuntu/Debian)
# Run as: bash deploy.sh
set -euo pipefail

APP_DIR="/opt/asa-overseer"
SERVICE_NAME="asa-overseer"
PYTHON="python3"
REPO="https://github.com/LordShaikh/asa-overseer.git"

echo "=== ASA Overseer Deploy ==="

# 1. Install system dependencies
echo "[1/6] Installing system packages..."
sudo apt-get update -y
sudo apt-get install -y git python3 python3-pip python3-venv

# 2. Clone or pull repo
echo "[2/6] Cloning/updating repo..."
if [ -d "$APP_DIR/.git" ]; then
  cd "$APP_DIR" && git pull
else
  sudo git clone "$REPO" "$APP_DIR"
  cd "$APP_DIR"
fi

# 3. Create virtualenv and install deps
echo "[3/6] Setting up Python venv..."
if [ ! -d "$APP_DIR/.venv" ]; then
  sudo $PYTHON -m venv "$APP_DIR/.venv"
fi
sudo "$APP_DIR/.venv/bin/pip" install --upgrade pip
sudo "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# 4. Create .env if it doesn't exist
echo "[4/6] Checking .env..."
if [ ! -f "$APP_DIR/.env" ]; then
  sudo cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo "  !! IMPORTANT: Edit $APP_DIR/.env with your real values before starting the bot!"
fi

# 5. Install systemd service
echo "[5/6] Installing systemd service..."
cat <<EOF | sudo tee /etc/systemd/system/${SERVICE_NAME}.service
[Unit]
Description=ASA Overseer Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/python ${APP_DIR}/run.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 6. Enable and start service
echo "[6/6] Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}

echo ""
echo "=== Done! ==="
echo "Next steps:"
echo "  1. Edit /opt/asa-overseer/.env with your real tokens/credentials"
echo "  2. Run: sudo systemctl start asa-overseer"
echo "  3. Check logs: sudo journalctl -u asa-overseer -f"
