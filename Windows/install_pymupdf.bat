@echo off
setlocal

where conda >nul 2>nul
if not errorlevel 1 (
  conda run python -m pip install --upgrade PyMuPDF
  if not errorlevel 1 goto :done
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m pip install --upgrade PyMuPDF
  if not errorlevel 1 goto :done
)

where python >nul 2>nul
if not errorlevel 1 (
  python -m pip install --upgrade PyMuPDF
  if not errorlevel 1 goto :done
)

echo Install failed. Could not find Python, or pip failed to install PyMuPDF.
pause
exit /b 1

:done
echo PyMuPDF installed successfully.
pause
