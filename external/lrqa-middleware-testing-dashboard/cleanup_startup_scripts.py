#!/usr/bin/env python3
"""Cleanup redundant startup scripts"""

import os
import glob

# Directory
os.chdir('/home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard')

# List of files to delete
files_to_delete = [
    'start_venv_with_email.sh',
    'start_with_email.sh',
    'start_bg.sh',
    'start_app_with_email.sh',
    'start_background.sh',
    'start_with_gmail.sh',
    'run_app.sh'
]

print("🗑️  Cleaning up redundant startup scripts...\n")

deleted_count = 0
for file in files_to_delete:
    if os.path.exists(file):
        try:
            os.remove(file)
            print(f"  ❌ Deleted: {file}")
            deleted_count += 1
        except Exception as e:
            print(f"  ⚠️  Failed to delete {file}: {e}")
    else:
        print(f"  ℹ️  Already deleted/not found: {file}")

print(f"\n✅ Cleanup complete! Deleted {deleted_count} files\n")

# List remaining startup scripts
print("📋 Remaining startup scripts:")
remaining = glob.glob('start*.sh') + glob.glob('start_*.sh') + glob.glob('run_*.sh')
if remaining:
    for script in sorted(remaining):
        print(f"  ✅ {script}")
else:
    print("  (None found)")

print("\n🎯 Keep using:")
print("  • ./start-app.sh          (Primary - local/production)")
print("  • ./start-rdk-app.sh      (Docker - container deployment)")
print("  • ./start_cloud_mode.sh   (Cloud - tunnel mode)")
