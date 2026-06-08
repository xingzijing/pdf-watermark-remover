@echo off
setlocal

set "SCRIPT=%~dp0remove_pdf_text_watermark.py"
set "CHECK=import importlib.util as u; raise SystemExit(0 if (u.find_spec('fitz') or u.find_spec('pymupdf')) else 1)"

rem Portable launcher: use the script beside this BAT, then find Python from PATH.
where conda >nul 2>nul
if not errorlevel 1 (
  conda run python -c "%CHECK%" >nul 2>nul
  if not errorlevel 1 (
    conda run python "%SCRIPT%" %*
    goto :eof
  )
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "%CHECK%" >nul 2>nul
  if not errorlevel 1 (
    py -3 "%SCRIPT%" %*
    goto :eof
  )
)

where python >nul 2>nul
if not errorlevel 1 (
  python -c "%CHECK%" >nul 2>nul
  if not errorlevel 1 (
    python "%SCRIPT%" %*
    goto :eof
  )
)

echo Could not find a Python environment with PyMuPDF installed.
echo Open Anaconda Prompt or Command Prompt in this folder and run:
echo python remove_pdf_text_watermark.py
echo.
echo Or install it into the active Python with:
echo python -m pip install PyMuPDF
pause
