import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import load_config
from .log_jsonl import append_event


SENSITIVE_KEYWORDS = [
    "payment",
    "pay",
    "wire",
    "bank",
    "invoice",
    "refund",
    "transfer",
    "card",
]


@dataclass
class TaskContext:
    task_path: Path
    task_text: str
    task_id: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_task_id(task_path: Path) -> str:
    return task_path.stem


def _detect_amount(text: str) -> Optional[float]:
    match = re.search(r"\$\\s*([0-9]+(?:\\.[0-9]{1,2})?)", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _is_sensitive(text: str) -> bool:
    lowered = text.lower()
    if any(keyword in lowered for keyword in SENSITIVE_KEYWORDS):
        return True
    amount = _detect_amount(text)
    if amount is not None and amount >= 500:
        return True
    return False


def _load_handbook(vault_path: Path) -> str:
    handbook = vault_path / "Company_Handbook.md"
    if handbook.exists():
        return handbook.read_text(encoding="utf-8")
    return ""


def _extract_handbook_sections(handbook_text: str) -> str:
    """
    Keep only the most relevant handbook sections to avoid oversized prompts.
    """
    if not handbook_text:
        return ""

    sections = []
    for heading in [
        "## 🧩 Planning Rules",
        "## 🛑 Human Approval Rules",
        "## 🔌 Tool & Execution Rules",
    ]:
        idx = handbook_text.find(heading)
        if idx != -1:
            section = handbook_text[idx:]
            # Cut at next heading if present
            next_heading = re.search(r"\n## ", section[1:])
            if next_heading:
                section = section[: next_heading.start() + 1]
            sections.append(section.strip())

    if sections:
        return "\n\n".join(sections)

    # Fallback: limit to first 1500 chars
    return handbook_text[:1500]


def _extract_task_brief(task_text: str) -> str:
    """
    Extract the raw content section or fallback to a brief snippet.
    """
    raw_match = re.search(r"## Raw Content\\s*(.*?)\\n## ", task_text, re.DOTALL)
    if raw_match:
        content = raw_match.group(1).strip()
        if content:
            return content

    # If no Raw Content section, use a trimmed version of the task file
    return task_text.strip()[:1500]


def _call_claude(prompt: str, timeout_seconds: int, claude_entry: str, claude_mode: str) -> str:
    cmd = [claude_entry, claude_mode, "--print", prompt]
    env = os.environ.copy()
    env.setdefault("CI", "1")
    env.setdefault("CLAUDE_NON_INTERACTIVE", "1")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input="y\n",
        env=env,
        timeout=timeout_seconds,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Claude execution failed")
    return result.stdout.strip()


def _render_prompt(task_text: str, handbook_text: str, goal: str, plan_text: str = "") -> str:
    plan_section = f"\nExisting Plan:\n{plan_text}\n" if plan_text else ""
    return f"""You are an autonomous assistant. Use the Company Handbook rules if present.

Company Handbook:
{handbook_text}

Task:
{task_text}
{plan_section}

Goal:
{goal}

Return output in this exact format:
PLAN:
- step 1
- step 2
OUTPUT:
<final deliverable>
"""


def _split_plan_output(response: str) -> tuple[str, str]:
    """
    Extract plan and output sections from a Claude response.
    If the model doesn't follow the exact format, fall back gracefully.
    """
    normalized = response.strip()

    match = re.search(r"PLAN:\\s*(.*?)OUTPUT:\\s*(.*)", normalized, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    output_idx = normalized.lower().rfind("output:")
    if output_idx != -1:
        output_text = normalized[output_idx + len("output:"):].strip()
        plan_text = normalized[:output_idx].strip()
        return plan_text, output_text

    return "", normalized


def _write_plan(plan_path: Path, task_id: str, plan_text: str):
    content = f"""---\nplan_id: {task_id}\ncreated: {datetime.now().isoformat()}\n---\n\n{plan_text or '- Review task and clarify details.'}\n"""
    plan_path.write_text(content, encoding="utf-8")


def _write_done(done_path: Path, task_id: str, output_text: str):
    content = f"""---\ntask_id: {task_id}\ncompleted: {datetime.now().isoformat()}\n---\n\n{output_text}\n"""
    done_path.write_text(content, encoding="utf-8")


def _create_approval_request(vault_path: Path, pending_dir: Path, task: TaskContext) -> Path:
    pending = pending_dir
    pending.mkdir(parents=True, exist_ok=True)
    approval_name = f"APPROVAL_{task.task_id}.md"
    approval_path = pending / approval_name
    approval_content = f"""---\ntype: approval_request\naction: task_execution\ncreated: {datetime.now().isoformat()}\nstatus: pending\ntask_path: {task.task_path}\n---\n\n## Approval Required\n\nTask `{task.task_id}` was flagged as sensitive.\n\n## To Approve\nMove this file to `/APPROVED/`.\n\n## To Reject\nMove this file to `/REJECTED/`.\n"""
    approval_path.write_text(approval_content, encoding="utf-8")
    return approval_path


def _plan_path(plan_dir: Path, task_id: str) -> Path:
    return plan_dir / f"{task_id}_plan.md"


def process_needs_action():
    config = load_config()
    vault_path = Path(config.vault_path)
    needs_action = vault_path / config.folders["needs_action"]
    plan_dir = vault_path / config.folders["plan"]
    done_dir = vault_path / config.folders.get("done", "DONE")
    archive_dir = vault_path / config.folders["archived"] / "processed"
    pending_dir = vault_path / config.folders["pending_approval"]

    plan_dir.mkdir(parents=True, exist_ok=True)
    done_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)

    handbook_text = _extract_handbook_sections(_load_handbook(vault_path))

    for task_path in sorted(needs_action.glob("*.md")):
        task_text = _read_text(task_path)
        task_brief = _extract_task_brief(task_text)
        task_id = _extract_task_id(task_path)
        task = TaskContext(task_path=task_path, task_text=task_text, task_id=task_id)

        if _is_sensitive(task_text):
            goal = "Create a plan only. Do NOT execute the task or provide the final deliverable."
            prompt = _render_prompt(task_brief, handbook_text, goal)
            response = _call_claude(
                prompt,
                config.claude_timeout_seconds,
                config.claude_entry,
                config.claude_mode,
            )
            plan_text, _ = _split_plan_output(response)

            plan_path = _plan_path(plan_dir, task_id)
            _write_plan(plan_path, task_id, plan_text)

            approval_path = _create_approval_request(vault_path, pending_dir, task)
            task_path.rename(pending_dir / task_path.name)
            append_event(
                vault_path,
                {
                    "event": "task_pending_approval",
                    "component": "task_processor",
                    "task_id": task_id,
                    "approval_file": str(approval_path),
                    "plan_file": str(plan_path),
                },
            )
            continue

        goal = "Create a plan only. Do NOT execute the task or provide the final deliverable."
        prompt = _render_prompt(task_brief, handbook_text, goal)
        response = _call_claude(
            prompt,
            config.claude_timeout_seconds,
            config.claude_entry,
            config.claude_mode,
        )
        plan_text, _ = _split_plan_output(response)

        plan_path = _plan_path(plan_dir, task_id)
        _write_plan(plan_path, task_id, plan_text)
        task_path.rename(plan_dir / task_path.name)

        append_event(
            vault_path,
            {
                "event": "task_planned",
                "component": "task_processor",
                "task_id": task_id,
                "plan_file": str(plan_path),
                "task_location": str(plan_dir / task_path.name),
            },
        )


def process_plans():
    config = load_config()
    vault_path = Path(config.vault_path)
    plan_dir = vault_path / config.folders["plan"]
    done_dir = vault_path / config.folders.get("done", "DONE")
    archive_dir = vault_path / config.folders["archived"] / "processed"

    done_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)

    handbook_text = _extract_handbook_sections(_load_handbook(vault_path))

    for plan_file in sorted(plan_dir.glob("*_plan.md")):
        task_id = plan_file.stem.replace("_plan", "")
        task_file = plan_dir / f"{task_id}.md"
        if not task_file.exists():
            continue

        task_text = _read_text(task_file)
        task_brief = _extract_task_brief(task_text)
        plan_text = _read_text(plan_file)
        goal = "Execute the plan and provide the final deliverable. Do NOT include the plan in the output."
        prompt = _render_prompt(task_brief, handbook_text, goal, plan_text=plan_text)
        response = _call_claude(
            prompt,
            config.claude_timeout_seconds,
            config.claude_entry,
            config.claude_mode,
        )
        _, output_text = _split_plan_output(response)

        done_path = done_dir / f"{task_id}.md"
        _write_done(done_path, task_id, output_text)

        task_file.rename(archive_dir / task_file.name)
        plan_file.rename(archive_dir / plan_file.name)

        append_event(
            vault_path,
            {
                "event": "task_completed",
                "component": "task_processor",
                "task_id": task_id,
                "done_file": str(done_path),
            },
        )


def process_approved():
    config = load_config()
    vault_path = Path(config.vault_path)
    approved = vault_path / config.folders["approved"]
    done_dir = vault_path / config.folders.get("done", "DONE")
    archive_dir = vault_path / config.folders["archived"] / "processed"
    plan_dir = vault_path / config.folders["plan"]

    done_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)

    handbook_text = _extract_handbook_sections(_load_handbook(vault_path))

    for approval_file in sorted(approved.glob("APPROVAL_*.md")):
        approval_text = _read_text(approval_file)
        match = re.search(r"task_path:\\s*(.+)", approval_text)
        if not match:
            continue
        task_path = Path(match.group(1).strip())
        if not task_path.exists():
            continue

        task_text = _read_text(task_path)
        task_brief = _extract_task_brief(task_text)
        task_id = _extract_task_id(task_path)
        plan_path = _plan_path(plan_dir, task_id)
        plan_text = _read_text(plan_path) if plan_path.exists() else ""
        goal = "Execute the task now that approval is granted, and provide the final deliverable."
        prompt = _render_prompt(task_brief, handbook_text, goal, plan_text=plan_text)
        response = _call_claude(
            prompt,
            config.claude_timeout_seconds,
            config.claude_entry,
            config.claude_mode,
        )
        _, output_text = _split_plan_output(response)

        done_path = done_dir / f"{task_id}.md"
        _write_done(done_path, task_id, output_text)

        task_path.rename(archive_dir / task_path.name)
        if plan_path.exists():
            plan_path.rename(archive_dir / plan_path.name)
        approval_file.rename(archive_dir / approval_file.name)

        append_event(
            vault_path,
            {
                "event": "approved_task_completed",
                "component": "task_processor",
                "task_id": task_id,
                "done_file": str(done_path),
            },
        )


if __name__ == "__main__":
    mode = os.getenv("TASK_PROCESSOR_MODE", "needs_action")
    if mode == "approved":
        process_approved()
    elif mode == "plans":
        process_plans()
    else:
        process_needs_action()
