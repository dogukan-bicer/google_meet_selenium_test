#!/bin/zsh

PID_FILE="$HOME/.cache/selenium/local-grid.pid"
if [[ ! -f "$PID_FILE" ]]; then
  echo "Local Grid PID file not found."
  exit 0
fi

GRID_PID="$(cat "$PID_FILE")"
GRID_COMMAND="$(ps -p "$GRID_PID" -o command= 2>/dev/null || true)"
if [[ "$GRID_COMMAND" != *"selenium-server-"* ]]; then
  rm -f "$PID_FILE"
  echo "No matching local Selenium Grid process is running."
  exit 0
fi

kill "$GRID_PID"
rm -f "$PID_FILE"
echo "Local Selenium Grid stopped."
