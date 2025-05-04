from flask import Flask
import subprocess
import signal
import os
import getpass

app = Flask(__name__)

process = None
script_path = "/opt/meet_recorder/record_meeting.sh"  # Update if needed

@app.route('/meet-start', methods=['POST'])
def start_meeting():
    global process
    if process and process.poll() is None:
        print("Recording already in progress.")
        return 'Recording already in progress.', 409
    try:
        # Print info about the current user
        print(f"Current user (getpass.getuser()): {getpass.getuser()}")
        print(f"Effective UID: {os.geteuid()}")
        print(f"Real UID: {os.getuid()}")
        print(f"Groups: {os.getgroups()}")
        process = subprocess.Popen(['bash', script_path])
        print(f"Started script with PID: {process.pid}")
        return f"process.pid: {process.pid}", 200
    except Exception as e:
        print(f"Error starting recording: {e}")
        return 'Failed to start recording.', 500

@app.route('/meet-end', methods=['POST'])
def end_meeting():
    global process
    if process and process.poll() is None:
        print(f"Terminating script with PID: {process.pid}")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        process = None
        return '', 204
    else:
        print("No recording in progress.")
        return 'No recording in progress.', 409

if __name__ == '__main__':
    app.run(port=13371)
