@echo off
echo Starting ShadowHunter Agent Monitor...
echo.
cd /d "%~dp0"
python agent_monitor_server.py
pause
