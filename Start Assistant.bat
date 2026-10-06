@echo off
title Open Assistant
cd /d "%~dp0"
py -3 --version >nul 2>nul
if errorlevel 1 (
  echo Python nahi mila. Install kar raha hoon, thoda ruko...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  echo.
  echo Install ho gaya. Is window ko band karo aur "Start Assistant" par dobara double-click karo.
  echo Agar install nahi hua to python.org se Python download karo ^(Add Python to PATH tick karna^).
  pause
  exit /b
)
if not exist "venv\ready.txt" (
  echo Pehli baar setup ho raha hai, 1-2 minute lagenge. Internet chalu rakho...
  py -3 -m venv venv || goto fail
  venv\Scripts\python -m pip install -q -r requirements.txt || goto fail
  echo ok> venv\ready.txt
)
venv\Scripts\python server.py
pause
exit /b
:fail
echo.
echo Setup fail ho gaya. Internet check karo aur dobara try karo.
pause
