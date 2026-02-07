

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import os
import random

def append_event(vault_path: Path, event: Dict[str, Any]) -> None:
    """
    Append a JSON event to the daily log file in vault/LOGS/
    Format: JSON Lines (append-only)
    """
    timestamp = datetime.now().isoformat()

    # Create the event record
    log_record = {
        "ts": timestamp,
        **event
    }

    # Determine the log file path (daily log)
    log_date = datetime.now().strftime("%Y-%m-%d")
    logs_dir = os.getenv("LOGS_DIR", "LOGS")
    log_file = vault_path / logs_dir / f"{log_date}.jsonl"

    # Create LOGS directory if it doesn't exist
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Attempt to write with retry and backoff
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_record) + "\n")

            # Also create a separate internal process log
            service_log_file = vault_path / logs_dir / f"service-{log_date}.jsonl"
            with open(service_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_record) + "\n")

            return  # Success
        except IOError as e:
            if attempt == max_retries - 1:  # Last attempt
                print(f"Failed to write log event after {max_retries} attempts: {e}")
                return

            # Exponential backoff: sleep for 2^attempt seconds + some jitter
            sleep_time = (2 ** attempt) + (random.uniform(0, 1))
            time.sleep(sleep_time)
