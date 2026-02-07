# AI Employee Automation System

An automated vault management system that watches for file changes and processes them through Claude's inbox-orchestrator skill.

## Overview

This project implements a "Digital FTE" (Full-Time Equivalent) - an autonomous AI employee that works 24/7 to manage personal and business affairs. The AI employee is built using Claude Code as the reasoning engine and Obsidian as the management dashboard, following a local-first, privacy-focused approach.

The system operates on the principle of "Your life and business on autopilot" - it proactively manages emails, WhatsApp messages, banking transactions, social media, and business tasks without constant user input.

## Architecture

The system follows a sophisticated architecture that separates concerns into distinct layers:

### Core Components

- **The Brain**: Claude Code acts as the reasoning engine with a "Ralph Wiggum" stop hook to ensure continuous iteration until tasks are complete
- **The Memory/GUI**: Obsidian (local Markdown) serves as the dashboard, keeping data local and accessible
- **The Senses (Watchers)**: Lightweight Python scripts monitor Gmail, WhatsApp, and filesystems to trigger the AI
- **The Hands (MCP)**: Model Context Protocol (MCP) servers handle external actions like sending emails or clicking buttons

### System Flow

1. **Perception**: Watchers detect changes in external systems (emails, messages, transactions)
2. **Reasoning**: Claude Code processes the information and creates plans
3. **Action**: MCP servers execute external actions based on Claude's decisions
4. **Persistence**: The "Ralph Wiggum" loop ensures tasks continue until completion

## Features

- **24/7 Operation**: Unlike traditional chatbots, this AI employee works continuously
- **Proactive Management**: Automatically monitors and responds to business/personal affairs
- **Human-in-the-Loop**: Critical actions require human approval to prevent unwanted behavior
- **Privacy-Focused**: All data stored locally using Obsidian vault
- **Extensible Architecture**: Easy to add new watchers and MCP servers
- **Audit Trail**: Complete logging of all AI actions for review

## Technology Stack

- **Reasoning Engine**: Claude Code
- **Knowledge Base**: Obsidian (local Markdown files)
- **Programming Language**: Python 3.13+
- **Automation Protocol**: Model Context Protocol (MCP)
- **Process Management**: PM2 for persistent operations
- **Frontend**: Obsidian dashboard for monitoring

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

## Security & Privacy

- Local-first architecture keeps sensitive data on your machine
- Environment variables for credential management
- Human-in-the-loop approval for sensitive actions
- Comprehensive audit logging
- Credential rotation recommendations

## Use Cases

- **Email Management**: Automatic triage, response drafting, and follow-up
- **Client Communication**: Respond to inquiries, schedule meetings, send invoices
- **Financial Monitoring**: Track transactions, flag unusual activity, categorize expenses
- **Social Media**: Automated posting and engagement
- **Task Management**: Prioritize and execute routine business operations
- **Business Reporting**: Generate weekly CEO briefings with revenue and bottleneck analysis

## Development Status

This project is part of the Personal AI Employee Hackathon 0, focused on building autonomous agents that function as full-time employees. The architecture solves the "lazy agent" problem by using watchers to trigger the AI rather than waiting for user input.

## Contributing

This project welcomes contributions that enhance the autonomous capabilities while maintaining security and privacy standards. Contributions should align with the local-first philosophy and maintain the human-in-the-loop safety mechanisms.

## License

This project is developed as part of the Panaversity hackathon series. See the accompanying documentation for specific licensing terms.