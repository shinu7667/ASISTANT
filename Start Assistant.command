#!/bin/bash
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python nahi mila. python.org se Python install karo, phir dobara double-click karo."; read -r; exit 1
fi
if [ ! -f venv/ready ]; then
  echo "Pehli baar setup ho raha hai, 1-2 minute lagenge. Internet chalu rakho..."
  python3 -m venv venv && venv/bin/pip install -q -r requirements.txt && touch venv/ready || { echo "Setup fail ho gaya."; read -r; exit 1; }
fi
venv/bin/python server.py
