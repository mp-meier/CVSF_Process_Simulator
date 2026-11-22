#!/usr/bin/env bash
# CVSF Model GUI - starts the interface in the default web browser (Linux / macOS)
cd "$(dirname "$0")"
python3 -c "import streamlit, plotly" 2>/dev/null || python3 -m pip install -r requirements.txt
python3 tools/model_update.py --auto
python3 -m streamlit run gui/app.py
