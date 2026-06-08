#!/bin/bash

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$DIR/remove_pdf_text_watermark.py"

check_pymupdf() {
  "$1" - <<'PY' >/dev/null 2>&1
import importlib.util as u
raise SystemExit(0 if (u.find_spec("fitz") or u.find_spec("pymupdf")) else 1)
PY
}

run_with_python() {
  local py="$1"
  shift
  if check_pymupdf "$py"; then
    "$py" "$SCRIPT" "$@"
    exit 0
  fi
}

if command -v python3 >/dev/null 2>&1; then
  run_with_python "$(command -v python3)" "$@"
fi

if command -v python >/dev/null 2>&1; then
  run_with_python "$(command -v python)" "$@"
fi

if command -v conda >/dev/null 2>&1; then
  if conda run python - <<'PY' >/dev/null 2>&1
import importlib.util as u
raise SystemExit(0 if (u.find_spec("fitz") or u.find_spec("pymupdf")) else 1)
PY
  then
    conda run python "$SCRIPT" "$@"
    exit 0
  fi
fi

echo "Could not find a Python environment with PyMuPDF installed."
echo
echo "Install it first with one of these commands:"
echo "  python3 -m pip install PyMuPDF"
echo "  conda install -c conda-forge pymupdf"
echo
echo "Then run this file again."
read -r -p "Press Enter to close..."
