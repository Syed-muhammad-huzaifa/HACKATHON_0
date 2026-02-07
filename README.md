# Personal AI Employee - Digital FTE (Full-Time Equivalent)

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

## Security & Privacy

- Local-first architecture keeps sensitive data on your machine
- Environment variables for credential management
- Human-in-the-loop approval for sensitive actions
- Comprehensive audit logging
- Credential rotation recommendations

## Achievement Tiers

The project follows a tiered approach for development:

### Bronze Tier (Foundation)
- Obsidian vault with Dashboard.md and Company_Handbook.md
- One working Watcher script (Gmail OR file system monitoring)
- Claude Code successfully reading from and writing to the vault
- Basic folder structure: /Inbox, /Needs_Action, /Done

### Silver Tier (Functional Assistant)
- All Bronze requirements plus multiple watchers
- MCP server for external actions
- Human-in-the-loop approval workflows
- Automatic scheduling capabilities

### Gold Tier (Autonomous Employee)
- Full cross-domain integration (Personal + Business)
- Integration with business systems like Odoo
- Multi-platform social media posting
- Advanced error recovery and audit logging

## Use Cases

- **Email Management**: Automatic triage, response drafting, and follow-up
- **Client Communication**: Respond to inquiries, schedule meetings, send invoices
- **Financial Monitoring**: Track transactions, flag unusual activity, categorize expenses
- **Social Media**: Automated posting and engagement
- **Task Management**: Prioritize and execute routine business operations
- **Business Reporting**: Generate weekly CEO briefings with revenue and bottleneck analysis

## Getting Started

1. Install prerequisites: Claude Code, Obsidian, Python 3.13+, Node.js v24+
2. Clone this repository
3. Set up your Obsidian vault
4. Configure MCP servers for your desired integrations
5. Implement watchers for your preferred communication channels
6. Define your Company_Handbook.md with business rules

## The "Monday Morning CEO Briefing"

One standout feature is the autonomous business audit that generates weekly briefings including:
- Revenue analysis
- Task completion metrics
- Bottleneck identification
- Proactive suggestions for optimization

## Development Status

This project is part of the Personal AI Employee Hackathon 0, focused on building autonomous agents that function as full-time employees. The architecture solves the "lazy agent" problem by using watchers to trigger the AI rather than waiting for user input.

## Contributing

This project welcomes contributions that enhance the autonomous capabilities while maintaining security and privacy standards. Contributions should align with the local-first philosophy and maintain the human-in-the-loop safety mechanisms.

## License

This project is developed as part of the Panaversity hackathon series. See the accompanying documentation for specific licensing terms.
