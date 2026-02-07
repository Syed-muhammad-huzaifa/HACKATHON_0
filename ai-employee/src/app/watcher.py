import time
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Set
import os
from .config import load_config
from .log_jsonl import append_event
import shutil
import json
from datetime import datetime

class VaultWatcher(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.vault_path = Path(self.config.vault_path)
        self.last_event_time = 0
        self.debounce_timer = None
        self.cooldown_seconds = self.config.cooldown_seconds

        # Track watched folders
        self.watched_folders = [
            self.vault_path / self.config.folders["inbox"],
            self.vault_path / self.config.folders["needs_action"],
            self.vault_path / self.config.folders["plan"],
            self.vault_path / self.config.folders["pending_approval"],
            self.vault_path / self.config.folders["approved"],
            self.vault_path / self.config.folders["rejected"],
        ]

        # Track ignore patterns
        self.ignore_patterns = [p.strip() for p in self.config.ignore_patterns]

        # Track state transitions
        self.approved_folder = self.vault_path / self.config.folders["approved"]
        self.rejected_folder = self.vault_path / self.config.folders["rejected"]
        self.archived_folder = self.vault_path / self.config.folders["archived"]
        self.logs_folder = self.vault_path / self.config.folders["logs"]

        # Attachments directory
        self.attachments_dir = self.vault_path / self.config.watcher["attachments_subdir"]
        self.attachments_dir.mkdir(parents=True, exist_ok=True)

        # For polling mechanism
        self.folder_snapshots = {}
        for folder_path in self.watched_folders:
            self.folder_snapshots[folder_path] = self._get_folder_contents(folder_path)

    def _get_folder_contents(self, folder_path):
        """Get a snapshot of folder contents"""
        if folder_path.exists():
            try:
                return set(f.name for f in folder_path.iterdir() if f.is_file())
            except PermissionError:
                return set()
        return set()

    def should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored based on patterns and directories"""
        path_str = str(path)

        # Ignore LOGS and ARCHIVED directories
        if self.logs_folder in path.parents or self.archived_folder in path.parents:
            return True

        # Check ignore patterns
        for pattern in self.ignore_patterns:
            if pattern in path_str:
                return True

        return False

    def is_stable_file(self, filepath: Path, timeout: float = 5.0, check_interval: float = 0.5) -> bool:
        """Check if file size is stable (not being written to)"""
        initial_size = filepath.stat().st_size
        start_time = time.time()

        while time.time() - start_time < timeout:
            time.sleep(check_interval)
            current_size = filepath.stat().st_size
            if current_size == initial_size:
                return True  # File size is stable
            initial_size = current_size

        return False  # Timeout reached

    def normalize_file_drop(self, filepath: Path) -> bool:
        """Handle non-MD files dropped into INBOX"""
        max_size = self.config.max_file_mb * 1024 * 1024  # Convert MB to bytes

        # Check if file is stable
        if not self.is_stable_file(filepath):
            print(f"File {filepath} is not stable, skipping normalization")
            return False

        # Check file size
        file_size = filepath.stat().st_size
        if file_size > max_size:
            # Create wrapper MD for large files without moving the original
            wrapper_content = f"""---
source_type: file_drop
original_name: "{filepath.name}"
attachment_path: "{filepath}"
received_at: "{datetime.now().isoformat()}"
---

# Large File Reference: {filepath.name}

File is too large to process ({file_size / (1024*1024):.2f}MB). Original file remains at:

```
{filepath}
```
"""
        else:
            # Move file to attachments and create wrapper
            attachment_path = self.attachments_dir / filepath.name
            shutil.move(str(filepath), str(attachment_path))

            wrapper_content = f"""---
source_type: file_drop
original_name: "{filepath.name}"
attachment_path: "{str(attachment_path.relative_to(self.vault_path))}"
received_at: "{datetime.now().isoformat()}"
---

# File Drop: {filepath.name}

Attachment stored in: `{str(attachment_path.relative_to(self.vault_path))}`
"""

        # Create wrapper MD file in INBOX
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        wrapper_filename = f"FILE_{timestamp}_{len(str(filepath))}.md"
        wrapper_path = filepath.parent / wrapper_filename

        with open(wrapper_path, 'w', encoding='utf-8') as f:
            f.write(wrapper_content)

        append_event(
            self.vault_path,
            {
                "event": "watcher_normalized_item",
                "component": "watcher",
                "original_path": str(filepath),
                "wrapper_path": str(wrapper_path),
                "file_size": file_size,
                "is_large": file_size > max_size
            }
        )

        return True

    def on_any_event(self, event):
        """Handle any filesystem event"""
        if event.is_directory:
            return

        event_path = Path(event.src_path)

        if self.should_ignore(event_path):
            return

        # Store the last event path for the flag
        setattr(self, 'last_event_path', str(event_path))

        # Check if it's a file drop in INBOX
        inbox_path = self.vault_path / self.config.folders["inbox"]
        if inbox_path in event_path.parents and event_path.suffix.lower() != ".md":
            # Non-MD file dropped in INBOX - normalize it
            if event.event_type in ['created', 'moved']:
                try:
                    self.normalize_file_drop(event_path)
                except Exception as e:
                    print(f"Error normalizing file drop {event_path}: {e}")
                    append_event(
                        self.vault_path,
                        {
                            "event": "error",
                            "component": "watcher",
                            "message": f"Error normalizing file drop: {str(e)}",
                            "file_path": str(event_path)
                        }
                    )

        # Check for state transitions
        if self.approved_folder in event_path.parents:
            append_event(
                self.vault_path,
                {
                    "event": "state_transition_detected",
                    "component": "watcher",
                    "transition": "approval_granted",
                    "item_path": str(event_path)
                }
            )
        elif self.rejected_folder in event_path.parents:
            append_event(
                self.vault_path,
                {
                    "event": "state_transition_detected",
                    "component": "watcher",
                    "transition": "approval_rejected",
                    "item_path": str(event_path)
                }
            )

        # Schedule the debounce
        current_time = time.time()
        self.last_event_time = current_time

        if self.debounce_timer:
            self.debounce_timer.cancel()

        self.debounce_timer = threading.Timer(self.cooldown_seconds, self.set_trigger_flag)
        self.debounce_timer.start()

    def poll_for_changes(self):
        """Poll for changes as a fallback for WSL environments"""
        while True:
            try:
                for folder_path in self.watched_folders:
                    current_contents = self._get_folder_contents(folder_path)
                    previous_contents = self.folder_snapshots.get(folder_path, set())

                    # Check for new files
                    new_files = current_contents - previous_contents

                    if new_files:
                        # Found new files, trigger the same logic as a filesystem event
                        setattr(self, 'last_event_path', str(folder_path))

                        # Schedule the debounce
                        current_time = time.time()
                        self.last_event_time = current_time

                        if self.debounce_timer:
                            self.debounce_timer.cancel()

                        self.debounce_timer = threading.Timer(self.cooldown_seconds, self.set_trigger_flag)
                        self.debounce_timer.start()

                        print(f"Polling detected new files in {folder_path}: {new_files}")

                        # Update the snapshot to current state
                        self.folder_snapshots[folder_path] = current_contents

                    # Update the snapshot if there were changes
                    elif current_contents != previous_contents:
                        self.folder_snapshots[folder_path] = current_contents

                time.sleep(2)  # Poll every 2 seconds

            except Exception as e:
                print(f"Error in polling: {e}")
                time.sleep(5)  # Wait longer on error

    def set_trigger_flag(self):
        """Set the trigger flag after debounce period"""
        flag_path = self.vault_path / self.config.logging["state_flag"]
        flag_path.parent.mkdir(parents=True, exist_ok=True)

        # Write flag with last event info
        flag_content = {
            "last_event_ts": datetime.now().isoformat(),
            "last_event_path": getattr(self, 'last_event_path', 'unknown')
        }

        with open(flag_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(flag_content))

        append_event(
            self.vault_path,
            {
                "event": "watcher_trigger_set",
                "component": "watcher",
                "flag_path": str(flag_path)
            }
        )

def start_watcher():
    """Start the filesystem watcher"""
    from datetime import datetime
    import json

    config = load_config()
    vault_path = Path(config.vault_path)

    event_handler = VaultWatcher()
    observer = Observer()

    # Watch all relevant folders
    for folder_path in event_handler.watched_folders:
        if folder_path.exists():
            observer.schedule(event_handler, str(folder_path), recursive=False)
            print(f"Watching: {folder_path}")
        else:
            print(f"Warning: Watched folder does not exist: {folder_path}")

    observer.start()

    # Start the polling thread as a fallback for WSL
    polling_thread = threading.Thread(target=event_handler.poll_for_changes, daemon=True)
    polling_thread.start()

    append_event(
        vault_path,
        {
            "event": "watcher_started",
            "component": "watcher"
        }
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        append_event(
            vault_path,
            {
                "event": "watcher_stopped",
                "component": "watcher"
            }
        )

    observer.join()