#!/bin/bash
# Wrapper: scrcpy → mkv → ffmpeg → fMP4 fragmentado (para MediaSource)
# Uso: stream_device.sh <DEVICE_ID>
DEVICE="$1"
FILE="/tmp/faebook_streams/stream_${DEVICE}.mkv"
mkdir -p /tmp/faebook_streams
rm -f "$FILE"

# scrcpy en background
scrcpy -s "$DEVICE" --no-window --no-audio --max-size=1080 --max-fps=15 \
    --record="$FILE" --record-format=mkv >/dev/null 2>&1 &
SCRCPY_PID=$!

# Esperar que el archivo tenga datos (max 30s)
for i in $(seq 1 60); do
    if [ -s "$FILE" ]; then break; fi
    sleep 0.5
done

# tail -f → ffmpeg → fMP4 fragmentado (H.264, sin re-codificar)
tail -c +1 -f "$FILE" 2>/dev/null | \
    ffmpeg -loglevel quiet -i pipe:0 -c copy \
        -f mp4 -movflags frag_keyframe+empty_moov+default_base_moof pipe:1 2>/dev/null

# Limpiar
kill $SCRCPY_PID 2>/dev/null
wait $SCRCPY_PID 2>/dev/null
rm -f "$FILE"
