#!/bin/bash
# Wrapper: scrcpy → mkv creciente → ffmpeg -re → fMP4 fragmentado
DEVICE="$1"
FILE="/tmp/faebook_streams/stream_${DEVICE}.mkv"
mkdir -p /tmp/faebook_streams
rm -f "$FILE"

# Iniciar scrcpy en background escribiendo al archivo
scrcpy -s "$DEVICE" --no-window --no-audio --max-size=1080 --max-fps=15 \
    --record="$FILE" --record-format=mkv >/dev/null 2>&1 &
SCRCPY_PID=$!

# Esperar que el archivo tenga datos
for i in $(seq 1 60); do
    if [ -s "$FILE" ]; then break; fi
    sleep 0.5
done

# ffmpeg lee el archivo en crecimiento (-re = real-time, se queda esperando)
ffmpeg -loglevel quiet -re -i "$FILE" \
    -c:v libx264 -preset ultrafast -tune zerolatency \
    -f mp4 -movflags frag_keyframe+empty_moov+default_base_moof \
    pipe:1 2>/dev/null

# Limpiar al terminar
kill $SCRCPY_PID 2>/dev/null
wait $SCRCPY_PID 2>/dev/null
rm -f "$FILE"
