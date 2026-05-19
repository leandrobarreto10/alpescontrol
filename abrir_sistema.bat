@echo off
cd /d "%~dp0"
start "" "http://localhost:8501"
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.fileWatcherType poll
pause
