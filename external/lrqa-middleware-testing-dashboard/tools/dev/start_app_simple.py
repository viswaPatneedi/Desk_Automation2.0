#!/usr/bin/env python3
"""Simple app startup wrapper"""
import subprocess
import sys
import os

os.chdir('/home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard')

# Activate venv and start app
result = subprocess.Popen([
    'bash', '-c',
    'source venv/bin/activate && python app.py > logs/app-background.log 2>&1 &'
])

print("✅ app.py started in background")
sys.exit(0)
