# Google Meet Recorder

This project enables automatic audio recording of Google Meet sessions by combining a Chrome extension, a webhook-based Python service, and a system-level recording setup using PulseAudio and `ffmpeg`.

---

## 📁 Folder Structure

```
google-meet/
├── deploy_meet_recorder.sh               # Idempotent setup and deploy script
├── meet_webhook_service.py              # Python Flask service to listen for recording events
├── meet_recorder.service                # systemd unit to start the Flask service on boot
├── record_meeting.sh                    # Bash script to record audio via PulseAudio and ffmpeg
├── meet-toast/                          # Chrome extension for Google Meet tab detection
│   ├── manifest.json
│   ├── content.js
│   └── icon128.png (optional)
```

---

## 🔧 Setup Instructions

### 1. 🐧 System Requirements

- Linux OS with PulseAudio
- `ffmpeg` installed (`sudo apt install ffmpeg`)
- Python 3.8+ and `venv`

---

### 2. 🧪 Deployment

Run the included deploy script to create a system user, configure the virtual environment, and register the service:

```bash
cd google-meet
chmod +x deploy_meet_recorder.sh
./deploy_meet_recorder.sh
```

This will:
- Create a `meetrecorder` system user (if it doesn’t exist)
- Set up `/opt/meet_recorder` and install a virtual environment
- Install `Flask`
- Copy the Flask service and systemd unit file
- Enable and start the `meet_recorder` service on boot

---

### 3. 🎙️ Bash Script: `record_meeting.sh`

This script:
- Creates a virtual PulseAudio sink called `combined`
- Loops back both the speaker and microphone into this sink
- Records from `combined.monitor` using `ffmpeg`
- Saves a `.wav` file in the current working directory with a timestamped filename

Ensure that it is located at `/opt/meet_recorder/record_meeting.sh` or update `meet_webhook_service.py` accordingly.

Make it executable:

```bash
chmod +x /opt/meet_recorder/record_meeting.sh
```

---

## 🧠 How it works

### ▶️ Starting a Google Meet call

- The Chrome extension detects when you join a Google Meet tab (`https://meet.google.com/*`)
- It sends a `POST` request to `http://localhost:13371/meet-start`
- The Python service starts the `record_meeting.sh` script
- A toast is shown inside the Meet tab: ✅ `Recording started`

### ⏹️ Leaving a call

- When the tab is closed or the red hang-up button is clicked:
  - A `POST` is sent to `http://localhost:13371/meet-end`
  - The Python service stops the recording
  - A toast is shown: ✅ `Recording ended`

### ⚠️ If an error occurs:
- You’ll see a red toast like ❌ `Failed to start recording: Recording already in progress`

---

## 🧩 Chrome Extension Setup

1. Open `chrome://extensions`
2. Enable **Developer Mode**
3. Click **“Load unpacked”**
4. Select the `google-meet/meet-toast/` directory

This extension:
- Injects a content script into Meet tabs
- Shows HTML toasts when recording starts/stops
- Pings the Python webhook backend

---

## 🛠️ Advanced Notes

- You can adjust PulseAudio source/sink names inside `record_meeting.sh` if needed
- Logs are shown in `journalctl -u meet_recorder.service`
- Webhook runs on port `13371`
- Use `systemctl` to control the service manually:
  ```bash
  sudo systemctl status meet_recorder
  sudo systemctl restart meet_recorder
  ```

---

## 📂 Outputs

- Audio files are saved in the directory where `record_meeting.sh` is executed (default: `/opt/meet_recorder/`)
- Filename format: `call_recording_YYYYMMDD_HHMMSS.wav`

---

## ✅ Summary

This system:
- Detects when you join or leave a Google Meet call
- Starts/stops an audio recording automatically
- Uses PulseAudio to merge mic + speaker output
- Notifies you with in-browser HTML toasts