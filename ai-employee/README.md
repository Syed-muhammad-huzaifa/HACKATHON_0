# AI Employee Automation System

An automated vault management system that watches for file changes and processes them through Claude's inbox-orchestrator skill.

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Create your environment file from the example:
```bash
cp .env.example .env
```
Then edit `.env` with your specific vault path and settings.

## Configuration

The system uses:
- `config/vault_config.yaml` - Defines vault folder structure
- `.env` - Runtime configuration and secrets

## Running Manually

Run the watcher (monitors file changes):
```bash
uv run ai-watch
```

Run the orchestrator (processes changes):
```bash
uv run ai-orchestrate
```

## Running with PM2

For persistent operation:
```bash
# Start both services
pm2 start pm2.config.cjs

# View logs
pm2 logs

# Restart all services
pm2 restart all

# Stop all services
pm2 stop all
```

## Testing

Drop any file into your `/INBOX` directory and watch:
- `STATE_CHANGED.flag` appears in `/LOGS/`
- Orchestrator runs Claude inbox skill
- INBOX items move to ARCHIVED
- Tasks appear in NEEDS_ACTION
- Logs append to `/LOGS/YYYY-MM-DD.jsonl`

## Architecture

- **Filesystem Watcher**: Monitors INBOX, NEEDS_ACTION, PENDING-APPROVAL, APPROVED, REJECTED, PLAN folders
- **Orchestrator**: Runs continuously, polls for state changes, executes Claude skill
- **Non-Interactive Runner**: Handles Claude's yes/no prompts automatically
- **JSONL Logging**: All events logged in append-only format
- **State Management**: Tracks human-in-the-loop state transitions (PENDING-APPROVAL → APPROVED/REJECTED)

## File Structure

```
src/
  app/
    __init__.py
    config.py          # Configuration loading
    paths.py           # Path definitions
    log_jsonl.py       # JSONL logging
    watcher.py         # Filesystem watcher
    orchestrator.py    # Orchestrator loop
    claude_runner.py   # Non-interactive Claude runner
    state_events.py    # State transition detection
  cli/
    run_watcher.py     # CLI entry point for watcher
    run_orchestrator.py # CLI entry point for orchestrator
config/
  vault_config.yaml    # Vault folder configuration
scripts/
  claude_run.sh        # Non-interactive Claude wrapper
pm2.config.cjs         # PM2 configuration
.env.example           # Environment variables example
```

## Prerequisites

Make sure your vault directory structure exists with the following folders:
```
/mnt/c/AI_Hackthon/ (or your chosen vault path)
├── INBOX/
├── NEEDS_ACTION/
├── PLAN/
├── PENDING-APPROVAL/
├── APPROVED/
├── REJECTED/
├── ARCHIVED/
└── LOGS/
```

And the following files:
- `Company_Handbook.md`
- `dashboard.md`