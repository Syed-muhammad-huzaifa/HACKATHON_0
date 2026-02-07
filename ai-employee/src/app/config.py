from pathlib import Path
import os
from typing import Dict, List
from dotenv import load_dotenv
import yaml
from pydantic import BaseModel
from pydantic.functional_validators import field_validator

# Load environment variables
load_dotenv()

class VaultConfig(BaseModel):
    # Environment variables
    vault_path: str = os.getenv("VAULT_PATH", "/mnt/c/AI_Hackthon")
    cooldown_seconds: int = int(os.getenv("COOLDOWN_SECONDS", "30"))
    orch_poll_seconds: int = int(os.getenv("ORCH_POLL_SECONDS", "3"))
    claude_entry: str = os.getenv("CLAUDE_ENTRY", "ccr")
    claude_mode: str = os.getenv("CLAUDE_MODE", "code")
    claude_skill_inbox: str = os.getenv("CLAUDE_SKILL_INBOX", "/inbox-orchestrator")
    claude_timeout_seconds: int = int(os.getenv("CLAUDE_TIMEOUT_SECONDS", "180"))
    max_file_mb: int = int(os.getenv("MAX_FILE_MB", "25"))
    ignore_patterns: List[str] = [p.strip() for p in os.getenv("IGNORE_PATTERNS", "~$, .tmp, .swp, .crdownload, .part").split(", ")]
    timezone: str = os.getenv("TZ", "Asia/Karachi")

    # Gmail credentials
    gmail_client_id: str = os.getenv("GMAIL_CLIENT_ID", "")
    gmail_client_secret: str = os.getenv("GMAIL_CLIENT_SECRET", "")

    # YAML config
    folders: Dict[str, str] = {}
    files: Dict[str, str] = {}
    logging: Dict[str, str] = {}
    watcher: Dict[str, str] = {}

    @field_validator('vault_path')
    @classmethod
    def validate_vault_path(cls, v):
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Vault path does not exist: {v}")
        return v

    @field_validator('cooldown_seconds', 'orch_poll_seconds', 'claude_timeout_seconds', 'max_file_mb')
    @classmethod
    def validate_positive_int(cls, v):
        if v <= 0:
            raise ValueError("Value must be positive")
        return v

def _resolve_vault_path(yaml_config: dict) -> str:
    """Resolve vault path from env, YAML, or common defaults."""
    candidates = []

    env_path = os.getenv("VAULT_PATH")
    if env_path:
        candidates.append(env_path)

    yaml_path = None
    if isinstance(yaml_config, dict):
        yaml_path = yaml_config.get("vault_path")
    if yaml_path:
        candidates.append(yaml_path)

    candidates.extend([
        "/mnt/c/AI_Hackthon/vault",
        "/mnt/c/AI_Hackthon",
        str(Path.home() / "AI_Employee_Vault"),
    ])

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))

    raise ValueError(
        "Vault path does not exist. Set VAULT_PATH or update vault_config.yaml."
    )


def _resolve_folder_name(vault_path: Path, configured: str, aliases: list[str]) -> str:
    """Resolve folder name based on existing directories and common aliases."""
    if (vault_path / configured).exists():
        return configured

    for name in aliases:
        if (vault_path / name).exists():
            return name

    existing = {}
    try:
        for item in vault_path.iterdir():
            if item.is_dir():
                existing[item.name.lower()] = item.name
    except FileNotFoundError:
        return configured

    for name in [configured] + aliases:
        match = existing.get(name.lower())
        if match:
            return match

    return configured


def _resolve_folders(vault_path: Path, folders: dict) -> dict:
    """Resolve folder names to match actual vault casing/names when possible."""
    alias_map = {
        "inbox": ["INBOX", "Inbox"],
        "needs_action": ["NEEDS_ACTION", "Needs_Action", "Needs-Action"],
        "plan": ["PLAN", "Plan"],
        "pending_approval": ["PENDING-APPROVAL", "Pending-Approval", "Pending_Approval"],
        "approved": ["APPROVED", "Approved"],
        "rejected": ["REJECTED", "Rejected"],
        "archived": ["ARCHIVED", "Archive", "ARCHIVE", "Archived"],
        "logs": ["LOGS", "Logs", "logs"],
        "done": ["DONE", "Done"],
    }

    resolved = dict(folders)
    for key, configured in folders.items():
        aliases = alias_map.get(key, [])
        resolved[key] = _resolve_folder_name(vault_path, configured, aliases)

    return resolved


def load_config() -> VaultConfig:
    """Load configuration from YAML file and environment variables"""
    config_path = Path(__file__).parent.parent.parent / "config" / "vault_config.yaml"

    if not config_path.exists():
        # Create default config if it doesn't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)

        default_config = {
            "folders": {
                "inbox": "INBOX",
                "needs_action": "NEEDS_ACTION",
                "plan": "PLAN",
                "pending_approval": "PENDING-APPROVAL",
                "approved": "APPROVED",
                "rejected": "REJECTED",
                "archived": "ARCHIVED",
                "logs": "LOGS",
                "done": "DONE"
            },
            "files": {
                "handbook": "Company_Handbook.md",
                "dashboard": "dashboard.md"
            },
            "logging": {
                "format": "jsonl",
                "state_flag": "LOGS/STATE_CHANGED.flag",
                "lock_file": "LOGS/orchestrator.lock"
            },
            "watcher": {
                "attachments_subdir": "INBOX/_attachments"
            }
        }

        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)

    with open(config_path) as f:
        yaml_config = yaml.safe_load(f)

    vault_path = Path(_resolve_vault_path(yaml_config))

    # Resolve folder names against existing vault structure
    yaml_config["folders"] = _resolve_folders(vault_path, yaml_config["folders"])

    # Normalize logging paths to use resolved logs folder
    logs_folder = yaml_config["folders"]["logs"]
    yaml_config["logging"]["state_flag"] = f"{logs_folder}/STATE_CHANGED.flag"
    yaml_config["logging"]["lock_file"] = f"{logs_folder}/orchestrator.lock"

    # Normalize attachments subdir to resolved inbox folder
    inbox_folder = yaml_config["folders"]["inbox"]
    yaml_config["watcher"]["attachments_subdir"] = f"{inbox_folder}/_attachments"

    # Export resolved folders for child processes (shell scripts, etc.)
    os.environ["VAULT_PATH"] = str(vault_path)
    os.environ["LOGS_DIR"] = logs_folder
    os.environ["INBOX_DIR"] = inbox_folder
    os.environ["NEEDS_ACTION_DIR"] = yaml_config["folders"]["needs_action"]

    # Validate that vault path exists
    if not vault_path.exists():
        raise ValueError(f"Vault path does not exist: {vault_path}")

    # Ensure required folders exist
    for folder_name in yaml_config["folders"].values():
        folder_path = vault_path / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

    # Create minimal handbook and dashboard if they don't exist
    handbook_path = vault_path / yaml_config["files"]["handbook"]
    if not handbook_path.exists():
        handbook_path.write_text("# Company Handbook\n\nDefault company handbook content.\n")

    dashboard_path = vault_path / yaml_config["files"]["dashboard"]
    if not dashboard_path.exists():
        dashboard_path.write_text("# Dashboard\n\nSystem dashboard.\n")

    # Merge YAML config with environment variables
    config_data = {
        "vault_path": str(vault_path),
        "cooldown_seconds": int(os.getenv("COOLDOWN_SECONDS", "30")),
        "orch_poll_seconds": int(os.getenv("ORCH_POLL_SECONDS", "3")),
        "claude_entry": os.getenv("CLAUDE_ENTRY", "ccr"),
        "claude_mode": os.getenv("CLAUDE_MODE", "code"),
        "claude_skill_inbox": os.getenv("CLAUDE_SKILL_INBOX", "/inbox-orchestrator"),
        "claude_timeout_seconds": int(os.getenv("CLAUDE_TIMEOUT_SECONDS", "180")),
        "max_file_mb": int(os.getenv("MAX_FILE_MB", "25")),
        "ignore_patterns": [p.strip() for p in os.getenv("IGNORE_PATTERNS", "~$, .tmp, .swp, .crdownload, .part").split(", ")],
        "timezone": os.getenv("TZ", "Asia/Karachi"),
        "folders": yaml_config["folders"],
        "files": yaml_config["files"],
        "logging": yaml_config["logging"],
        "watcher": yaml_config["watcher"]
    }

    return VaultConfig(**config_data)
