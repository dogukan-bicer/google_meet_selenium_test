#!/bin/bash
# Create the base Python environment; model stacks are optional.

set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 -m venv "$REPO_DIR/.venv"
"$REPO_DIR/.venv/bin/python" -m pip install --upgrade pip
"$REPO_DIR/.venv/bin/python" -m pip install -r "$REPO_DIR/requirements.txt"

cat <<'EOF'
Base environment ready.
Optional image models: .venv/bin/pip install -r requirements-vision.txt
Optional audio models: .venv/bin/pip install -r requirements-audio.txt
Run the UI with: ./run_ui.command
EOF
