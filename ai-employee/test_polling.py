#!/usr/bin/env python3
import os
import time
from pathlib import Path

# Add src to path
import sys
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Set the vault path
os.environ['VAULT_PATH'] = '/mnt/c/AI_Hackthon'

from app.watcher import VaultWatcher

# Create the watcher
watcher = VaultWatcher()

# Test the polling manually
inbox_path = Path('/mnt/c/AI_Hackthon/INBOX')
print(f"Initial snapshot for {inbox_path}: {watcher.folder_snapshots[inbox_path]}")

# Get current contents
current = watcher._get_folder_contents(inbox_path)
print(f"Current contents: {current}")

# Check for differences
new_files = current - watcher.folder_snapshots[inbox_path]
print(f"New files: {new_files}")

if new_files:
    print("Would trigger event!")
else:
    print("No new files detected")

# Create a new file and check again
print("\nCreating a new test file...")
new_file = inbox_path / f"manual_test_{int(time.time())}.md"
new_file.write_text(f"Test file created at {time.time()}")

time.sleep(1)  # Allow file to be written

current_after = watcher._get_folder_contents(inbox_path)
print(f"Contents after adding file: {current_after}")

new_files_after = current_after - current
print(f"New files after adding: {new_files_after}")