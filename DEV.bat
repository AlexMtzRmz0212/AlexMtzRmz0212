@echo off
title Profile README preview
cd /d "%~dp0"
rem Renders README.md the way GitHub shows it, at http://localhost:5183. Close this window to stop it.
python "%~dp0preview.py"
pause
