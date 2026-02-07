---
name: inbox-orchestrator
description: "Core triage skill for AI Employee. Processes raw inbox items (/Inbox/*.md) from watchers (EMAIL_*, FILE_*, WHATSAPP_*), applies Company_Handbook.md rules to decide: spam/fyi/actionable, creates normalized tasks in /Needs_Action/, logs decisions to /Logs/, and updates Dashboard.md with counts. Use this skill when: new items appear in /Inbox folder, orchestrator triggers inbox processing, or manual 'process inbox' command. Bronze tier requirement - proves Claude Code can read/write vault. MUST NOT: create plans, call MCP tools, create approvals, or execute external actions."
---

# Inbox Orchestrator

## Overview

Triage raw inbox items into actionable tasks using business context. This skill implements **Phase 1** of the AI Employee perception-reasoning pipeline: convert unstructured input into structured, normalized tasks.

## Quick Start

```bash
# Process all inbox items
Use inbox-orchestrator skill to process /vault/Inbox/

# What it does:
# 1. Read items from /Inbox/
# 2. Apply triage rules from Company_Handbook.md
# 3. Decide: spam | fyi | actionable
# 4. Create tasks in /Needs_Action/
# 5. Update Dashboard.md (counts)
# 6. Log to /Logs/YYYY-MM-DD.json
```

## Skill Contract

```yaml
Input: /Inbox/*.md
  - EMAIL_{id}.md (from Gmail watcher)
  - FILE_{id}.md (from filesystem watcher)
  - WHATSAPP_{id}.md (from WhatsApp watcher)

Output: /Needs_Action/TASK_{date}_{id}.md

Side Effects:
  - Dashboard.md update (inbox count, recent activity)
  - /Logs/YYYY-MM-DD.json append
  - Move processed items to /Archive/

Decision: spam | fyi | actionable (exactly one)

MUST NOT:
  - Create Plan.md (separate skill)
  - Call MCP tools
  - Create approvals
  - Execute external actions
```

## Workflow Decision Tree

```
/Inbox/*.md detected
    ↓
Read file + parse YAML frontmatter
    ↓
Load Company_Handbook.md rules
    ↓
Check spam patterns?
    YES → Move to /Archive/spam/ → Log "spam_filtered" → DONE
    NO  → Continue
         ↓
    Check FYI patterns?
        YES → Move to /Archive/fyi/ → Log "fyi_archived" → DONE
        NO  → Continue (actionable)
             ↓
        Load business context:
            - /Clients/*.md
            - /Projects/*.md
            - /Accounting/Rates.md
             ↓
        Identify entity (client/lead/vendor/unknown)
             ↓
        Detect intent (invoice/meeting/support/sales)
             ↓
        Create /Needs_Action/TASK_{id}.md
            - Normalized YAML frontmatter
            - Entity context links
            - AI analysis section
            - Suggested actions checklist
             ↓
        Move to /Archive/processed/
             ↓
        Update Dashboard.md:
            - Decrement Inbox count
            - Append to Recent Activity
             ↓
        Log to /Logs/YYYY-MM-DD.json
             ↓
        DONE
```

## Prerequisites

### Required Vault Structure

```
vault/
├── Inbox/                  # INPUT: Raw items from watchers
├── Needs_Action/           # OUTPUT: Normalized tasks
├── Archive/
│   ├── processed/          # Successfully triaged
│   ├── spam/               # Filtered junk
│   └── fyi/                # Reference only
├── Logs/                   # JSON activity logs
│   └── YYYY-MM-DD.json
├── Dashboard.md            # Real-time overview (slight update)
├── Company_Handbook.md     # Triage rules (REQUIRED)
├── Clients/                # Entity context (optional)
├── Projects/               # Project context (optional)
└── Accounting/
    └── Rates.md            # Pricing info (optional)
```

### Required Context File: Company_Handbook.md

See `references/handbook_template.md` for complete template. Minimum required:

```markdown
# Company Handbook

## Email Processing Rules

### Auto-Delete (Spam)
- Subject keywords: ["unsubscribe", "newsletter", "promotion"]
- Sender domains: ["noreply@", "marketing@"]

### Auto-Archive (FYI)
- Bank statements (already logged)
- Social notifications
- System alerts

### High Priority Triggers
- From known clients + "urgent"
- Subject contains "overdue"
- Client tier = premium

## Categories
- Finance: invoice, payment, bill
- Sales: quote, proposal, pricing
- Support: help, question, issue
- Operations: meeting, schedule
```

## Input Format (From Watchers)

Inbox items MUST have YAML frontmatter:

```markdown
---
type: email | whatsapp | file_drop
from: sender@example.com
subject: "Email subject" (if email)
received: "2026-02-06T10:00:00+05:00"
priority: high | medium | low (watcher's guess)
status: pending
---

## Content

[Raw message or file description]
```

## Triage Logic

### 1. Spam Detection

```python
# From Company_Handbook.md
spam_keywords = handbook.auto_delete.subject_keywords
spam_domains = handbook.auto_delete.sender_domains

if any(kw in subject.lower() for kw in spam_keywords):
    decision = "spam"
    reason = f"Subject contains: {kw}"
    destination = "/Archive/spam/"

if any(domain in sender for domain in spam_domains):
    decision = "spam"
    reason = f"Spam domain: {domain}"
    destination = "/Archive/spam/"
```

### 2. FYI Detection

```python
# From Company_Handbook.md
fyi_types = handbook.auto_archive.types

if item.type in fyi_types:
    decision = "fyi"
    reason = f"Type: {item.type}"
    destination = "/Archive/fyi/"
```

### 3. Actionable Item Processing

If not spam or FYI, create task:

```python
# Load context
clients = load_all_files('/vault/Clients/')
projects = load_all_files('/vault/Projects/')
rates = load_file('/vault/Accounting/Rates.md')

# Identify entity
entity = identify_entity(item.from, clients)
# Returns: {type: 'known_client', name: 'Client A', ref: '/vault/Clients/ClientA.md'}

# Detect intent
intent = detect_intent(item.subject, item.content)
# Returns: {type: 'invoice_request', confidence: 'high'}

# Match project
project = match_project(entity, projects)

# Generate task ID
task_id = f"TASK_{date}_{random_id}"

# Create task file in /Needs_Action/
```

## Output Format: Task File

```markdown
# /vault/Needs_Action/TASK_2026-02-06_abc123.md

---
task_id: TASK_2026-02-06_abc123
created: "2026-02-06T10:30:00+05:00"
source_type: email
source_id: EMAIL_12345
status: pending

# Business Context
entity_type: known_client
entity_name: Client A
entity_ref: /vault/Clients/ClientA.md
related_project: /vault/Projects/WebsiteRedesign.md

# Classification (filled by task-classifier skill)
category: null
priority: null
estimated_effort: null
---

## Source: Email

**From:** client@example.com  
**Subject:** Need January invoice  
**Received:** 2026-02-06 10:00

## Raw Content

Can you send the invoice for January's work?

## AI Analysis

### Entity Context
- **Client:** Client A (premium tier, active since 2024)
- **Project:** Website Redesign (milestone 2 complete)
- **Rate:** $1,500/month (per /vault/Accounting/Rates.md)

### Intent Recognition
- **Primary:** Invoice generation request
- **Confidence:** High
- **Timeline:** ASAP

### Matched Rules
From Company_Handbook.md:
- Rule: "Invoice requests → Finance category"
- High Priority: "Premium client + financial request"

## Suggested Actions

- [ ] Verify amount: $1,500
- [ ] Check project status
- [ ] Generate invoice PDF
- [ ] Draft email reply
- [ ] Get approval before sending

## Context Links

- Client: [ClientA.md](/vault/Clients/ClientA.md)
- Project: [WebsiteRedesign.md](/vault/Projects/WebsiteRedesign.md)
- Template: [Invoice_Email.md](/vault/Templates/Invoice_Email.md)

---
*Processed by: inbox-orchestrator v1.0*  
*Phase: Triage Complete*
```

## Dashboard Update (Light)

Update these sections in Dashboard.md:

```markdown
## 📊 Task Pipeline Overview
**Inbox:** 0  ← Decrement by 1
**Pending Tasks:** 1  ← Increment by 1

## 🕒 Recent Activity (Last 10)
- [10:30] EMAIL → TASK_abc123 (Client A invoice) - Pending  ← Add
```

**Implementation:**

```python
def update_dashboard_light(dashboard_path, task_id, source_type, summary):
    """
    Light dashboard update - only counts and recent activity.
    Full dashboard update is done by dashboard-updater skill.
    """
    dashboard = read_file(dashboard_path)
    
    # Parse current counts
    inbox_match = re.search(r'\*\*Inbox:\*\* (\d+)', dashboard)
    pending_match = re.search(r'\*\*Pending Tasks:\*\* (\d+)', dashboard)
    
    inbox_count = int(inbox_match.group(1)) if inbox_match else 0
    pending_count = int(pending_match.group(1)) if pending_match else 0
    
    # Update counts
    inbox_count -= 1  # Processed one item
    pending_count += 1  # Created one task
    
    dashboard = re.sub(
        r'\*\*Inbox:\*\* \d+',
        f'**Inbox:** {inbox_count}',
        dashboard
    )
    dashboard = re.sub(
        r'\*\*Pending Tasks:\*\* \d+',
        f'**Pending Tasks:** {pending_count}',
        dashboard
    )
    
    # Add to recent activity
    timestamp = datetime.now().strftime('%H:%M')
    activity_line = f"- [{timestamp}] {source_type.upper()} → {task_id} ({summary})"
    
    # Insert after "## 🕒 Recent Activity" header
    dashboard = re.sub(
        r'(## 🕒 Recent Activity.*?\n)',
        f'\\1{activity_line}\n',
        dashboard,
        flags=re.DOTALL
    )
    
    # Update last_updated timestamp
    dashboard = re.sub(
        r'last_updated: .*',
        f'last_updated: {datetime.now().isoformat()}',
        dashboard
    )
    
    write_file(dashboard_path, dashboard)
```

## Logging Format

All logging MUST be **append-only** and written to the Obsidian vault.

Logs are stored as **JSON Lines (JSONL)** — one event per line.

**Log file path:**

/vault/LOGS/YYYY-MM-DD.jsonl

The log file must **never be read and rewritten**.  
Each event is appended as a single immutable JSON object.

---

### Actionable Item (Task Created)

```json
{"ts":"2026-02-06T10:30:00+05:00","event":"inbox_triage","skill":"inbox-orchestrator","source_file":"EMAIL_12345.md","source_type":"email","decision":"task_created","task_id":"TASK_2026-02-06_abc123","priority":"high","category":"finance","confidence":"high","destination":"/NEEDS_ACTION/TASK_2026-02-06_abc123.md"}


**Spam or FYI Item**

{"ts":"2026-02-06T10:31:00+05:00","event":"inbox_triage","skill":"inbox-orchestrator","source_file":"EMAIL_12346.md","source_type":"email","decision":"spam","reason":"subject_contains_unsubscribe","destination":"/ARCHIVED/EMAIL_12346.md"}

**Error or Exception**

{"ts":"2026-02-06T10:32:10+05:00","event":"error","skill":"inbox-orchestrator","context":"handbook_parse_failed","severity":"error"}


###  Hard Logging Rules

- Logs **MUST** be written in **append mode only**
- One inbox item **MUST** generate **exactly one** `inbox_triage` log entry
- Log files **MUST NOT** be overwritten or restructured
- Folder paths **MUST** match vault casing **exactly**
- Logs act as the **single source of truth** for audit and debugging


## Entity Identification

```python
def identify_entity(sender_email, content, clients_context):
    """
    Match sender against known entities.
    """
    # Check known clients
    for client_file, client_data in clients_context.items():
        client_emails = [
            client_data.get('email'),
            client_data.get('secondary_email')
        ]
        if sender_email in client_emails:
            return {
                'type': 'known_client',
                'name': client_data.get('company_name'),
                'tier': client_data.get('tier'),
                'ref': f'/vault/Clients/{client_file}.md'
            }
    
    # Check for lead indicators
    if any(kw in content.lower() for kw in ['pricing', 'quote', 'interested']):
        return {
            'type': 'new_lead',
            'name': extract_name_from_email(sender_email),
            'ref': None
        }
    
    # Unknown
    return {
        'type': 'unknown',
        'name': sender_email,
        'ref': None
    }
```

## Intent Detection

```python
def detect_intent(subject, content):
    """
    Classify message intent based on keywords.
    """
    text = (subject + ' ' + content).lower()
    
    # Invoice request
    if any(kw in text for kw in ['invoice', 'bill', 'receipt']):
        return {
            'type': 'invoice_request',
            'confidence': 'high' if 'invoice' in text else 'medium'
        }
    
    # Meeting request
    if any(kw in text for kw in ['meeting', 'call', 'schedule']):
        return {
            'type': 'meeting_request',
            'confidence': 'high'
        }
    
    # Support question
    if any(kw in text for kw in ['help', 'question', 'issue', 'problem']):
        return {
            'type': 'support_question',
            'confidence': 'medium'
        }
    
    # Sales inquiry
    if any(kw in text for kw in ['pricing', 'quote', 'proposal']):
        return {
            'type': 'sales_inquiry',
            'confidence': 'high'
        }
    
    # Default
    return {
        'type': 'general_inquiry',
        'confidence': 'low'
    }
```

## Error Handling

```python
# Missing required file
if not handbook_path.exists():
    log_error("Company_Handbook.md not found - required for triage")
    raise FileNotFoundError("Company_Handbook.md missing")

# Malformed inbox item
try:
    metadata, content = parse_yaml_frontmatter(inbox_file)
except Exception as e:
    log_warning(f"Malformed file: {inbox_file.name}")
    # Move to /Archive/malformed/
    move_file(inbox_file, vault_path / 'Archive' / 'malformed')
    continue

# Context file errors
try:
    clients = load_clients_context()
except Exception as e:
    log_warning(f"Could not load client context: {e}")
    clients = {}  # Continue with empty context
```

## Validation & Testing

```python
# Test with sample inbox item
def test_triage():
    # Create test inbox item
    create_file('/vault/Inbox/EMAIL_test.md', '''---
type: email
from: client@example.com
subject: Need invoice
received: 2026-02-06T10:00:00+05:00
---

Can you send the invoice?
''')
    
    # Run skill
    result = inbox_orchestrator.process('/vault')
    
    # Verify task created
    assert exists('/vault/Needs_Action/TASK_2026-02-06_*.md')
    
    # Verify dashboard updated
    dashboard = read_file('/vault/Dashboard.md')
    assert 'Pending Tasks:** 1' in dashboard
    
    # Verify log entry
    log = read_json('/vault/Logs/2026-02-06.json')
    assert log[-1]['decision'] == 'actionable'
```

## Troubleshooting

**No tasks created:**
- Check Company_Handbook.md exists
- Verify inbox item has valid YAML
- Check not being filtered as spam

**Wrong entity detected:**
- Add client to /Clients/ folder
- Check email address in client profile
- Review entity identification logic

**Dashboard not updating:**
- Verify Dashboard.md exists
- Check file permissions
- Review update_dashboard_light() function

## Resources

### scripts/
- `triage_inbox.py` - Main processing script (see below)

### references/
- `handbook_template.md` - Company_Handbook.md template
- `watcher_formats.md` - Expected inbox item formats

### assets/
- `task_template.md` - Output task structure