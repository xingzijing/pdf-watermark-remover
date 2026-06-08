#!/bin/bash

set -e

if command -v conda >/dev/null 2>&1; then
  conda install -c conda-forge pymupdf -y || conda run python -m pip install --upgrade PyMuPDF
  echo "PyMuPDF installed."
  read -r -p "Press Enter to close..."
  exit 0
fi

if command -v python3 >/dev/null 2>&1; then
  python3 -m pip install --upgrade PyMuPDF
  echo "PyMuPDF installed."
  read -r -p "Press Enter to close..."
  exit 0
fi

if command -v python >/dev/null 2>&1; then
  python -m pip install --upgrade PyMuPDF
  echo "PyMuPDF installed."
  read -r -p "Press Enter to close..."
  exit 0
fi

echo "Install failed. Could not find python3, python, or conda."
read -r -p "Press Enter to close..."
