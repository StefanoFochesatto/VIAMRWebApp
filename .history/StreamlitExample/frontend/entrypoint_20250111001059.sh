#!/bin/bash
set -e

# Start Xvfb
Xvfb :99 -screen 0 1024x768x24 &
export DISPLAY=:99

# Start Streamlit
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
