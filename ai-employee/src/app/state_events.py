"""
Module for handling state transition events in the vault system.
Detects when items move between state folders and logs them appropriately.
"""
from pathlib import Path
from typing import Optional
import time
from .config import load_config
from .log_jsonl import append_event

class StateEventManager:
    def __init__(self):
        self.config = load_config()
        self.vault_path = Path(self.config.vault_path)

        # Track folder paths
        self.approved_folder = self.vault_path / self.config.folders["approved"]
        self.rejected_folder = self.vault_path / self.config.folders["rejected"]
        self.pending_approval_folder = self.vault_path / self.config.folders["pending_approval"]
        self.inbox_folder = self.vault_path / self.config.folders["inbox"]
        self.needs_action_folder = self.vault_path / self.config.folders["needs_action"]
        self.archived_folder = self.vault_path / self.config.folders["archived"]
        self.plan_folder = self.vault_path / self.config.folders["plan"]

    def detect_state_transitions(self, event_path: Path) -> Optional[dict]:
        """
        Detect if a file movement represents a state transition
        Returns transition info or None if not a state transition
        """
        parent_dirs = []
        current_path = event_path
        while current_path != current_path.parent:
            parent_dirs.append(current_path.name)
            current_path = current_path.parent

        # Check if the file is in a state folder
        if self.approved_folder in event_path.parents:
            return {
                "type": "approval_granted",
                "from_folder": self._infer_previous_state(event_path),
                "to_folder": "approved",
                "item_path": str(event_path)
            }
        elif self.rejected_folder in event_path.parents:
            return {
                "type": "approval_rejected",
                "from_folder": self._infer_previous_state(event_path),
                "to_folder": "rejected",
                "item_path": str(event_path)
            }
        elif self.pending_approval_folder in event_path.parents:
            return {
                "type": "submitted_for_approval",
                "from_folder": self._infer_previous_state(event_path),
                "to_folder": "pending_approval",
                "item_path": str(event_path)
            }

        return None

    def _infer_previous_state(self, item_path: Path) -> str:
        """Try to infer the previous state of an item based on its history or name"""
        # For now, just return unknown, but could be enhanced to track history
        return "unknown"

    def log_state_transition(self, transition_info: dict):
        """Log a state transition event"""
        append_event(
            self.vault_path,
            {
                "event": "state_transition_detected",
                "component": "state_events",
                **transition_info
            }
        )

_STATE_EVENT_MANAGER: Optional[StateEventManager] = None


def get_state_event_manager() -> StateEventManager:
    """Get singleton instance of state event manager"""
    global _STATE_EVENT_MANAGER
    if _STATE_EVENT_MANAGER is None:
        _STATE_EVENT_MANAGER = StateEventManager()
    return _STATE_EVENT_MANAGER
