#!/usr/bin/env python3
"""Auto-commit and push changes for Betty project."""
import subprocess, os, sys
from datetime import datetime

REPO = "/home/tom/ai-video-platform"
os.chdir(REPO)

# Check for uncommitted changes
status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
if not status.stdout.strip():
    sys.exit(0)  # Nothing to commit

# Stage all changes
subprocess.run(["git", "add", "-A"], capture_output=True)

# Generate commit message
ts = datetime.now().strftime("%Y-%m-%d %H:%M")
commit_msg = f"auto: {ts}"

r = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)
if r.returncode != 0:
    print(f"Commit failed: {r.stderr}")
    sys.exit(1)

print(f"Committed: {commit_msg}")

# Push
r = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, timeout=60)
if r.returncode == 0:
    print("Pushed successfully")
else:
    print(f"Push failed: {r.stderr} (will retry next cycle)")
