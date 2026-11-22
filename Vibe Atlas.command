#!/bin/bash
# Double-click to open Vibe Atlas locally (disk saving, offline mode, CARI).
# Starts the small local server if it isn't already running, then opens the browser.
cd "$(dirname "$0")" || exit 1
URL="http://127.0.0.1:8765/explorer/"
if ! curl -s -o /dev/null --max-time 1 "http://127.0.0.1:8765/api/saved"; then
  echo "Starting Vibe Atlas…"
  nohup python3 explorer/server.py > "${TMPDIR:-/tmp}/vibe-atlas.log" 2>&1 &
  for i in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.5
    curl -s -o /dev/null --max-time 1 "http://127.0.0.1:8765/api/saved" && break
  done
fi
open "$URL"
echo "Vibe Atlas is running at $URL — you can close this window."
