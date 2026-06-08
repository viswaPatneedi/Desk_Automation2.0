#!/usr/bin/env python3
import os
import subprocess
import sys

os.chdir('/home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard')

print("=" * 70)
print("STARTUP SCRIPTS CLEANUP & RESTART")
print("=" * 70)
print("")

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

print("🗑️  Deleting redundant startup scripts...")
print("")

deleted_count = 0
for file in files_to_delete:
    if os.path.exists(file):
        try:
            os.remove(file)
            print(f"  ✅ Deleted: {file}")
            deleted_count += 1
        except Exception as e:
            print(f"  ❌ Failed to delete {file}: {e}")
    else:
        print(f"  ℹ️  Not found: {file}")

print("")
print("=" * 70)
print("CLEANUP COMPLETE")
print("=" * 70)
print("")

# List remaining startup scripts
print("📋 Remaining startup scripts:")
scripts = []
for pattern in ['start*.sh', 'start_*.sh', 'run_*.sh']:
    import glob
    scripts.extend(glob.glob(pattern))

scripts = sorted(set(scripts))
if scripts:
    for script in scripts:
        print(f"  ✅ {script}")
else:
    print("  ✗ No startup scripts found")

print("")
print(f"Deleted: {deleted_count} files")
print("")

# Make start-app.sh executable
print("=" * 70)
print("MAKING START-APP.SH EXECUTABLE")
print("=" * 70)
if os.path.exists('start-app.sh'):
    try:
        os.chmod('start-app.sh', 0o755)
        print("✅ start-app.sh is now executable")
    except Exception as e:
        print(f"❌ Failed to make executable: {e}")
else:
    print("❌ start-app.sh not found!")

print("")
print("=" * 70)
print("RESTARTING APPLICATION")
print("=" * 70)
print("")

# Restart the app
print("Executing: ./start-app.sh restart")
print("")

try:
    result = subprocess.run(['bash', './start-app.sh', 'restart'], 
                          capture_output=True, 
                          text=True, 
                          timeout=15)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print("")
    print("✅ RESTART COMPLETE")
except subprocess.TimeoutExpired:
    print("⚠️  Command timeout")
except Exception as e:
    print(f"❌ Error during restart: {e}")

print("")
print("=" * 70)
print("CHECKING APP STATUS")
print("=" * 70)
print("")

try:
    result = subprocess.run(['bash', './start-app.sh', 'status'], 
                          capture_output=True, 
                          text=True, 
                          timeout=10)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
except Exception as e:
    print(f"❌ Error checking status: {e}")

print("")
print("✅ ALL OPERATIONS COMPLETE")
