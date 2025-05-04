#!/bin/bash
set -e

# echo "[1/6] Creating meetrecorder user if it doesn't exist..."
# if ! id "meetrecorder" &>/dev/null; then
#     sudo useradd --system --no-create-home meetrecorder
# fi

echo "[2/6] Creating folders..."
sudo mkdir -p /opt/meet_recorder
sudo chown dusty:dusty /opt/meet_recorder

echo "[3/6] Setting up Python virtual environment..."
if [ ! -d /opt/meet_recorder/env ]; then
    sudo -u dusty python3 -m venv /opt/meet_recorder/env
fi

echo "[4/6] Installing Flask if not present..."
sudo -u dusty /opt/meet_recorder/env/bin/pip install --upgrade pip
sudo -u dusty /opt/meet_recorder/env/bin/pip install flask

echo "[5/6] Copying service files..."
sudo cp ./meet_webhook_service.py /opt/meet_recorder/meet_webhook_service.py
sudo cp ./record_meeting.sh /opt/meet_recorder/record_meeting.sh
sudo chown dusty:dusty /opt/meet_recorder/record_meeting.sh
sudo chmod +x /opt/meet_recorder/record_meeting.sh
sudo chown dusty:dusty /opt/meet_recorder/meet_webhook_service.py
sudo cp ./meet_recorder.service /etc/systemd/system/meet_recorder.service

echo "[6/6] Enabling and starting systemd service..."
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable meet_recorder.service
sudo systemctl restart meet_recorder.service

echo "✅ Deploy complete. Service status:"
sudo systemctl status meet_recorder.service --no-pager
