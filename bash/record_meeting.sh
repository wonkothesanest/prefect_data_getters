#!/bin/bash
set -e

# Unload previously loaded modules (if any)
pactl unload-module module-loopback 2>/dev/null || true
pactl unload-module module-null-sink 2>/dev/null || true

# Load the virtual sink if not already loaded
if ! pactl list sinks short | grep -q "combined"; then
    pactl load-module module-null-sink sink_name=combined sink_properties=device.description="Combined_Sink"
fi

# Route system output (speakers) to the virtual sink
if ! pactl list modules | grep -q "source=alsa_output.usb-0b0e_Jabra_Speak_710_745C4B5FDC54-00.analog-stereo.monitor"; then
    pactl load-module module-loopback source=alsa_output.usb-0b0e_Jabra_Speak_710_745C4B5FDC54-00.analog-stereo.monitor sink=combined
fi

# Route microphone input to the virtual sink
if ! pactl list modules | grep -q "source=alsa_input.usb-0b0e_Jabra_Speak_710_745C4B5FDC54-00.mono-fallback"; then
    pactl load-module module-loopback source=alsa_input.usb-0b0e_Jabra_Speak_710_745C4B5FDC54-00.mono-fallback sink=combined
fi

# Record audio from the virtual sink monitor with a timestamped filename
OUTPUT_FILE="call_recording_$(date +%Y%m%d_%H%M%S).wav"
ffmpeg -f pulse -i combined.monitor -ac 2 -ar 44100 -y "$OUTPUT_FILE"

echo "Recording saved to $OUTPUT_FILE"
