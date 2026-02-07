import subprocess
import time
from pathlib import Path
from typing import Tuple
import os
from .config import load_config
from .log_jsonl import append_event

def run_claude_non_interactive(config) -> bool:
    """
    Run Claude in non-interactive mode using the shell script wrapper
    """
    vault_path = Path(config.vault_path)

    append_event(
        vault_path,
        {
            "event": "claude_run_started",
            "component": "claude_runner",
            "command": f"{config.claude_entry} {config.claude_mode} {config.claude_skill_inbox}"
        }
    )

    # Path to the shell script
    script_path = Path(__file__).parent.parent.parent / "scripts" / "claude_run.sh"

    if not script_path.exists():
        append_event(
            vault_path,
            {
                "event": "error",
                "component": "claude_runner",
                "message": f"Shell script not found: {script_path}"
            }
        )
        return False

    # Prepare environment
    env = os.environ.copy()
    env["CLAUDE_ENTRY"] = config.claude_entry
    env["CLAUDE_MODE"] = config.claude_mode
    env["CLAUDE_SKILL_INBOX"] = config.claude_skill_inbox
    env["CLAUDE_TIMEOUT_SECONDS"] = str(config.claude_timeout_seconds)
    env["VAULT_PATH"] = str(vault_path)
    env["INBOX_DIR"] = config.folders["inbox"]
    env["NEEDS_ACTION_DIR"] = config.folders["needs_action"]
    env["LOGS_DIR"] = config.folders["logs"]

    # Prepare command
    cmd = ["bash", str(script_path)]

    # Try running with retries
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(
                cmd,
                cwd=script_path.parent,
                env=env,
                capture_output=True,
                timeout=config.claude_timeout_seconds + 30  # Add buffer
            )

            # Log stdout and stderr to vault logs
            log_date = time.strftime("%Y-%m-%d")
            stdout_log = vault_path / "LOGS" / f"claude-stdout-{log_date}.log"
            stderr_log = vault_path / "LOGS" / f"claude-stderr-{log_date}.log"

            stdout_log.parent.mkdir(parents=True, exist_ok=True)

            if result.stdout:
                with open(stdout_log, "a", encoding="utf-8") as f:
                    f.write(f"\n--- Run at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                    f.write(result.stdout.decode('utf-8'))

            if result.stderr:
                with open(stderr_log, "a", encoding="utf-8") as f:
                    f.write(f"\n--- Run at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                    f.write(result.stderr.decode('utf-8'))

            if result.returncode == 0:
                append_event(
                    vault_path,
                    {
                        "event": "claude_run_finished",
                        "component": "claude_runner",
                        "exit_code": result.returncode,
                        "attempt": attempt + 1
                    }
                )
                return True
            else:
                append_event(
                    vault_path,
                    {
                        "event": "claude_run_failed",
                        "component": "claude_runner",
                        "exit_code": result.returncode,
                        "attempt": attempt + 1,
                        "stdout": result.stdout.decode('utf-8') if result.stdout else "",
                        "stderr": result.stderr.decode('utf-8') if result.stderr else ""
                    }
                )

        except subprocess.TimeoutExpired:
            append_event(
                vault_path,
                {
                    "event": "claude_run_timeout",
                    "component": "claude_runner",
                    "attempt": attempt + 1
                }
            )
        except Exception as e:
            append_event(
                vault_path,
                {
                    "event": "claude_run_exception",
                    "component": "claude_runner",
                    "attempt": attempt + 1,
                    "error": str(e)
                }
            )

        # If this wasn't the last attempt, wait before retrying
        if attempt < max_retries:
            time.sleep(5 * (attempt + 1))  # Increasing delay

    return False
