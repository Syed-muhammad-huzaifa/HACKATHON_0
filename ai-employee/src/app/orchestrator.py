import time
import os
from pathlib import Path
import subprocess
import tempfile
from datetime import datetime, timedelta
from .config import load_config
from .log_jsonl import append_event
from .claude_runner import run_claude_non_interactive
from .task_processor import process_needs_action, process_plans, process_approved

def run_orchestrator_loop():
    """Main orchestrator loop that polls for the state flag"""
    config = load_config()
    vault_path = Path(config.vault_path)
    flag_path = vault_path / config.logging["state_flag"]
    lock_path = vault_path / config.logging["lock_file"]

    # Track orchestrator state
    consecutive_failures = 0
    max_backoff = 300  # 5 minutes max backoff

    append_event(
        vault_path,
        {
            "event": "orchestrator_started",
            "component": "orchestrator"
        }
    )

    while True:
        # Check if flag exists (for INBOX processing)
        if flag_path.exists():
            append_event(
                vault_path,
                {
                    "event": "orchestrator_triggered",
                    "component": "orchestrator",
                    "flag_exists": True
                }
            )

            # Try to acquire lock
            if acquire_lock(lock_path, vault_path):
                try:
                    # Run Claude skill non-interactively (processes INBOX files)
                    success = run_claude_non_interactive(config)

                    if success:
                        # Delete flag on success
                        flag_path.unlink(missing_ok=True)
                        consecutive_failures = 0  # Reset failure counter
                        append_event(
                            vault_path,
                            {
                                "event": "orchestrator_success",
                                "component": "orchestrator"
                            }
                        )
                    else:
                        # Keep flag for retry
                        consecutive_failures += 1
                        append_event(
                            vault_path,
                            {
                                "event": "orchestrator_failure",
                                "component": "orchestrator",
                                "failure_count": consecutive_failures
                            }
                        )

                finally:
                    # Release lock
                    release_lock(lock_path, vault_path)
            else:
                pass

        # Check if there are tasks in NEEDS_ACTION to plan (regardless of flag)
        needs_action_path = vault_path / config.folders["needs_action"]
        if needs_action_path.exists():
            task_files = list(needs_action_path.glob("*.md"))
            if task_files and len(task_files) > 0:
                append_event(
                    vault_path,
                    {
                        "event": "orchestrator_needs_action_detected",
                        "component": "orchestrator",
                        "task_count": len(task_files)
                    }
                )

                # Try to acquire lock to process NEEDS_ACTION tasks
                if acquire_lock(lock_path, vault_path):
                    success = False
                    try:
                        # Process NEEDS_ACTION tasks into PLAN
                        process_needs_action()
                        success = True
                    except Exception as e:
                        append_event(
                            vault_path,
                            {
                                "event": "task_processor_error",
                                "component": "orchestrator",
                                "error": str(e)
                            }
                        )
                    finally:
                        # Release lock
                        release_lock(lock_path, vault_path)

                    if success:
                        consecutive_failures = 0  # Reset failure counter
                        append_event(
                            vault_path,
                            {
                                "event": "orchestrator_success",
                                "component": "orchestrator"
                            }
                        )
                    else:
                        consecutive_failures += 1
                        append_event(
                            vault_path,
                            {
                                "event": "orchestrator_failure",
                                "component": "orchestrator",
                                "failure_count": consecutive_failures
                            }
                        )
                else:
                    pass

        # Process approved items -> DONE
        approved_path = vault_path / config.folders["approved"]
        done_path = vault_path / config.folders.get("done", "DONE")
        if approved_path.exists():
            approved_files = list(approved_path.glob("*.md"))
            if approved_files:
                if acquire_lock(lock_path, vault_path):
                    try:
                        process_approved()
                        append_event(
                            vault_path,
                            {
                                "event": "approved_items_processed",
                                "component": "orchestrator",
                                "count": len(approved_files)
                            }
                        )
                    finally:
                        release_lock(lock_path, vault_path)

        # Process PLAN items -> DONE
        plan_path = vault_path / config.folders["plan"]
        if plan_path.exists():
            plan_files = list(plan_path.glob("*_plan.md"))
            if plan_files:
                if acquire_lock(lock_path, vault_path):
                    try:
                        process_plans()
                        append_event(
                            vault_path,
                            {
                                "event": "plan_items_processed",
                                "component": "orchestrator",
                                "count": len(plan_files)
                            }
                        )
                    finally:
                        release_lock(lock_path, vault_path)

        # Process rejected items -> ARCHIVED/rejected
        rejected_path = vault_path / config.folders["rejected"]
        archived_root = vault_path / config.folders["archived"]
        if rejected_path.exists():
            rejected_files = list(rejected_path.glob("*.md"))
            if rejected_files:
                if acquire_lock(lock_path, vault_path):
                    try:
                        archive_rejected = archived_root / "rejected"
                        archive_rejected.mkdir(parents=True, exist_ok=True)
                        moved = 0
                        for item in rejected_files:
                            target = archive_rejected / item.name
                            item.rename(target)
                            moved += 1

                        append_event(
                            vault_path,
                            {
                                "event": "rejected_items_archived",
                                "component": "orchestrator",
                                "count": moved,
                                "destination": str(archive_rejected)
                            }
                        )
                    finally:
                        release_lock(lock_path, vault_path)

        # Calculate sleep time based on failure count (exponential backoff)
        sleep_time = min(config.orch_poll_seconds * (2 ** min(consecutive_failures, 5)), max_backoff)
        time.sleep(sleep_time)

def acquire_lock(lock_path: Path, vault_path: Path) -> bool:
    """Acquire orchestrator lock with stale detection"""
    current_time = time.time()

    # Check if lock exists
    if lock_path.exists():
        try:
            with open(lock_path, 'r') as f:
                lock_content = f.read().strip()

            # Parse lock content to get creation time
            parts = lock_content.split('|')
            if len(parts) >= 2:
                try:
                    lock_timestamp = float(parts[0])
                    age = current_time - lock_timestamp

                    # If lock is stale (> 10 minutes), override it
                    if age > 600:  # 10 minutes
                        append_event(
                            vault_path,
                            {
                                "event": "lock_overridden",
                                "component": "orchestrator",
                                "reason": "stale_lock",
                                "age_seconds": age
                            }
                        )
                        lock_path.unlink(missing_ok=True)
                    else:
                        # Lock is still fresh
                        return False
                except ValueError:
                    # Invalid timestamp, remove lock
                    lock_path.unlink(missing_ok=True)
            else:
                # Invalid lock file format, remove it
                lock_path.unlink(missing_ok=True)
        except Exception:
            # Error reading lock file, assume it's corrupted and remove it
            lock_path.unlink(missing_ok=True)

    # Create lock file with timestamp
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, 'w') as f:
            f.write(f"{current_time}|orchestrator_pid_{os.getpid()}")

        append_event(
            vault_path,
            {
                "event": "orchestrator_locked",
                "component": "orchestrator"
            }
        )
        return True
    except Exception as e:
        append_event(
            vault_path,
            {
                "event": "lock_acquisition_error",
                "component": "orchestrator",
                "error": str(e)
            }
        )
        return False

def release_lock(lock_path: Path, vault_path: Path):
    """Release orchestrator lock"""
    try:
        if lock_path.exists():
            lock_path.unlink()
    except Exception as e:
        append_event(
            vault_path,
            {
                "event": "lock_release_error",
                "component": "orchestrator",
                "error": str(e)
            }
        )
