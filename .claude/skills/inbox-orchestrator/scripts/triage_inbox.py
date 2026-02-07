#!/usr/bin/env python3
"""
inbox-orchestrator: Core triage skill for AI Employee
Processes /Inbox/*.md → /Needs_Action/TASK_*.md
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime
import yaml

def parse_yaml_frontmatter(filepath):
    """Extract YAML frontmatter and body from markdown file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if not content.startswith('---'):
        return {}, content
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content
    
    try:
        metadata = yaml.safe_load(parts[1])
        body = parts[2].strip()
        return metadata or {}, body
    except Exception as e:
        print(f"Warning: Could not parse YAML: {e}")
        return {}, content

def resolve_folder(vault_path: Path, preferred: str, aliases: list[str]) -> Path:
    """Resolve folder path with case-insensitive fallback and aliases."""
    preferred_path = vault_path / preferred
    if preferred_path.exists():
        return preferred_path

    for name in aliases:
        candidate = vault_path / name
        if candidate.exists():
            return candidate

    try:
        existing = {p.name.lower(): p.name for p in vault_path.iterdir() if p.is_dir()}
    except FileNotFoundError:
        return preferred_path

    for name in [preferred] + aliases:
        match = existing.get(name.lower())
        if match:
            return vault_path / match

    return preferred_path


def resolve_file(vault_path: Path, preferred: str, aliases: list[str]) -> Path:
    """Resolve file path with case-insensitive fallback and aliases."""
    preferred_path = vault_path / preferred
    if preferred_path.exists():
        return preferred_path

    for name in aliases:
        candidate = vault_path / name
        if candidate.exists():
            return candidate

    try:
        existing = {p.name.lower(): p.name for p in vault_path.iterdir() if p.is_file()}
    except FileNotFoundError:
        return preferred_path

    for name in [preferred] + aliases:
        match = existing.get(name.lower())
        if match:
            return vault_path / match

    return preferred_path


def load_handbook(vault_path):
    """Load Company_Handbook.md rules."""
    handbook_path = resolve_file(
        vault_path,
        "Company_Handbook.md",
        ["company_handbook.md", "Company_Handbook.MD"]
    )
    
    if not handbook_path.exists():
        print(f"ERROR: Company_Handbook.md not found at {handbook_path}")
        print("This file is REQUIRED for triage logic.")
        sys.exit(1)
    
    metadata, content = parse_yaml_frontmatter(handbook_path)
    
    # Parse rules from content (simplified)
    rules = {
        'spam_keywords': ['unsubscribe', 'newsletter', 'promotion', 'limited time'],
        'spam_domains': ['noreply@', 'do-not-reply@', 'marketing@'],
        'fyi_types': ['bank_statement', 'social_notification', 'system_alert'],
        'high_priority_keywords': ['urgent', 'asap', 'emergency', 'critical', 'overdue'],
        'finance_keywords': ['invoice', 'payment', 'bill', 'receipt'],
        'sales_keywords': ['quote', 'proposal', 'pricing', 'interested'],
        'support_keywords': ['help', 'question', 'issue', 'problem']
    }
    
    return rules

def load_clients_context(vault_path):
    """Load all client profiles."""
    clients_dir = resolve_folder(vault_path, "Clients", ["clients"])
    clients = {}
    
    if not clients_dir.exists():
        return clients
    
    for client_file in clients_dir.glob('*.md'):
        try:
            metadata, _ = parse_yaml_frontmatter(client_file)
            clients[client_file.stem] = metadata
        except Exception as e:
            print(f"Warning: Could not load {client_file.name}: {e}")
    
    return clients

def is_spam(metadata, content, rules):
    """Check if item is spam."""
    subject = metadata.get('subject', '').lower()
    sender = metadata.get('from', '').lower()
    
    # Check subject keywords
    for keyword in rules['spam_keywords']:
        if keyword in subject:
            return True, f"Subject contains spam keyword: {keyword}"
    
    # Check sender domain
    for domain in rules['spam_domains']:
        if domain in sender:
            return True, f"Spam sender domain: {domain}"
    
    return False, None

def is_fyi(metadata, rules):
    """Check if item is FYI only."""
    item_type = metadata.get('type', '').lower()
    
    for fyi_type in rules['fyi_types']:
        if fyi_type in item_type:
            return True, f"FYI type: {item_type}"
    
    return False, None

def identify_entity(sender, content, clients):
    """Identify sender entity."""
    sender_lower = sender.lower()
    
    # Check known clients
    for client_name, client_data in clients.items():
        client_email = client_data.get('email', '').lower()
        if client_email and client_email in sender_lower:
            return {
                'type': 'known_client',
                'name': client_data.get('company_name', client_name),
                'tier': client_data.get('tier', 'standard'),
                'ref': f'/vault/Clients/{client_name}.md'
            }
    
    # Check for lead indicators
    content_lower = content.lower()
    if any(kw in content_lower for kw in ['pricing', 'quote', 'proposal', 'interested']):
        return {
            'type': 'new_lead',
            'name': sender.split('@')[0] if '@' in sender else sender,
            'tier': None,
            'ref': None
        }
    
    # Unknown
    return {
        'type': 'unknown',
        'name': sender,
        'tier': None,
        'ref': None
    }

def detect_intent(subject, content, rules):
    """Detect message intent."""
    text = (subject + ' ' + content).lower()
    
    # Invoice request
    if any(kw in text for kw in rules['finance_keywords']):
        return {
            'type': 'invoice_request' if 'invoice' in text else 'payment_related',
            'confidence': 'high'
        }
    
    # Meeting request
    if any(kw in text for kw in ['meeting', 'call', 'schedule']):
        return {
            'type': 'meeting_request',
            'confidence': 'high'
        }
    
    # Support question
    if any(kw in text for kw in rules['support_keywords']):
        return {
            'type': 'support_question',
            'confidence': 'medium'
        }
    
    # Sales inquiry
    if any(kw in text for kw in rules['sales_keywords']):
        return {
            'type': 'sales_inquiry',
            'confidence': 'high'
        }
    
    # General
    return {
        'type': 'general_inquiry',
        'confidence': 'low'
    }

def create_task_file(vault_path, source_metadata, source_content, source_id, entity, intent):
    """Create normalized task in /Needs_Action/."""
    # Generate task ID
    date_str = datetime.now().strftime('%Y-%m-%d')
    random_id = source_id.replace('EMAIL_', '').replace('FILE_', '').replace('WHATSAPP_', '')[:6]
    task_id = f"TASK_{date_str}_{random_id}"
    
    # Prepare task metadata
    task_metadata = {
        'task_id': task_id,
        'created': datetime.now().isoformat(),
        'source_type': source_metadata.get('type', 'unknown'),
        'source_id': source_id,
        'status': 'pending',
        'entity_type': entity['type'],
        'entity_name': entity['name'],
        'entity_ref': entity.get('ref'),
        'related_project': None,  # Could be matched later
        'category': None,  # Filled by task-classifier
        'priority': None,  # Filled by task-classifier
        'estimated_effort': None
    }
    
    # Build task content
    task_content = f"""---
{yaml.dump(task_metadata, default_flow_style=False, allow_unicode=True)}---

## Source: {source_metadata.get('type', 'Unknown').title()}

**From:** {source_metadata.get('from', 'Unknown')}  
**Subject:** {source_metadata.get('subject', 'N/A')}  
**Received:** {source_metadata.get('received', 'Unknown')}

## Raw Content

{source_content}

## AI Analysis

### Entity Context
- **Type:** {entity['type']}
- **Name:** {entity['name']}
- **Tier:** {entity.get('tier', 'N/A')}
{f"- **Profile:** [{entity['name']}]({entity['ref']})" if entity.get('ref') else ''}

### Intent Recognition
- **Type:** {intent['type']}
- **Confidence:** {intent['confidence']}

## Suggested Actions

- [ ] Review and classify priority
- [ ] Determine appropriate response
- [ ] Execute action or seek approval

---
*Processed by: inbox-orchestrator v1.0*  
*Phase: Triage Complete*
"""
    
    # Write task file
    needs_action = resolve_folder(
        vault_path,
        "Needs_Action",
        ["NEEDS_ACTION", "Needs-Action", "NeedsAction"]
    )
    needs_action.mkdir(parents=True, exist_ok=True)
    task_file = needs_action / f"{task_id}.md"
    
    with open(task_file, 'w', encoding='utf-8') as f:
        f.write(task_content)
    
    return task_id, task_file

def update_dashboard_light(vault_path, task_id, source_type, summary):
    """Light dashboard update - counts and recent activity only."""
    dashboard_path = resolve_file(
        vault_path,
        "Dashboard.md",
        ["dashboard.md", "DASHBOARD.md"]
    )
    
    if not dashboard_path.exists():
        print(f"Warning: Dashboard.md not found at {dashboard_path}")
        return
    
    dashboard = dashboard_path.read_text(encoding='utf-8')
    
    # Update Inbox count (decrement)
    inbox_match = re.search(r'\*\*Inbox:\*\* (\d+)', dashboard)
    if inbox_match:
        inbox_count = max(0, int(inbox_match.group(1)) - 1)
        dashboard = re.sub(
            r'\*\*Inbox:\*\* \d+',
            f'**Inbox:** {inbox_count}',
            dashboard
        )
    
    # Update Pending Tasks count (increment)
    pending_match = re.search(r'\*\*Pending Tasks:\*\* (\d+)', dashboard)
    if pending_match:
        pending_count = int(pending_match.group(1)) + 1
        dashboard = re.sub(
            r'\*\*Pending Tasks:\*\* \d+',
            f'**Pending Tasks:** {pending_count}',
            dashboard
        )
    
    # Add to Recent Activity
    timestamp = datetime.now().strftime('%H:%M')
    activity_line = f"- [{timestamp}] {source_type.upper()} → {task_id} ({summary})\n"
    
    # Insert after Recent Activity header
    activity_section = re.search(
        r'(## 🕒 Recent Activity \(Last 10\)\n)(.*?)(\n## |$)',
        dashboard,
        re.DOTALL
    )
    
    if activity_section:
        existing_activities = activity_section.group(2).strip().split('\n')
        # Keep only last 9 activities
        existing_activities = [a for a in existing_activities if a.strip() and not a.startswith('- —')][:9]
        new_activities = [activity_line.strip()] + existing_activities
        
        dashboard = re.sub(
            r'(## 🕒 Recent Activity \(Last 10\)\n).*?(\n## )',
            f'\\1{chr(10).join(new_activities)}\n\\2',
            dashboard,
            flags=re.DOTALL
        )
    
    # Update last_updated
    dashboard = re.sub(
        r'last_updated: .*',
        f'last_updated: {datetime.now().isoformat()}',
        dashboard
    )
    
    dashboard_path.write_text(dashboard, encoding='utf-8')

def log_action(vault_path, action, source_file, decision, details):
    """Log action to /Logs/YYYY-MM-DD.json."""
    logs_dir = resolve_folder(vault_path, "Logs", ["LOGS", "logs"])
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"
    
    entry = {
        'timestamp': datetime.now().isoformat(),
        'action': action,
        'skill': 'inbox-orchestrator',
        'source_file': source_file,
        'decision': decision,
        **details
    }
    
    # Load existing logs
    logs = []
    if log_file.exists():
        try:
            logs = json.loads(log_file.read_text(encoding='utf-8'))
        except:
            logs = []
    
    logs.append(entry)
    
    log_file.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding='utf-8')

def process_inbox_item(inbox_file, vault_path, rules, clients):
    """Process single inbox item."""
    print(f"\nProcessing: {inbox_file.name}")
    
    # Read item
    metadata, content = parse_yaml_frontmatter(inbox_file)
    source_id = inbox_file.stem
    
    # Check spam
    spam, spam_reason = is_spam(metadata, content, rules)
    if spam:
        print(f"  → SPAM: {spam_reason}")
        archive_root = resolve_folder(vault_path, "Archive", ["ARCHIVE", "ARCHIVED", "Archived", "ARCHIVED"])
        archive_spam = archive_root / 'spam'
        archive_spam.mkdir(parents=True, exist_ok=True)
        inbox_file.rename(archive_spam / inbox_file.name)
        
        log_action(vault_path, 'triage', source_id, 'spam', {
            'reason': spam_reason,
            'destination': str(archive_spam / inbox_file.name)
        })
        return
    
    # Check FYI
    fyi, fyi_reason = is_fyi(metadata, rules)
    if fyi:
        print(f"  → FYI: {fyi_reason}")
        archive_root = resolve_folder(vault_path, "Archive", ["ARCHIVE", "ARCHIVED", "Archived", "ARCHIVED"])
        archive_fyi = archive_root / 'fyi'
        archive_fyi.mkdir(parents=True, exist_ok=True)
        inbox_file.rename(archive_fyi / inbox_file.name)
        
        log_action(vault_path, 'triage', source_id, 'fyi', {
            'reason': fyi_reason,
            'destination': str(archive_fyi / inbox_file.name)
        })
        return
    
    # Actionable - process
    print(f"  → ACTIONABLE")
    
    sender = metadata.get('from', 'unknown')
    subject = metadata.get('subject', '')
    
    entity = identify_entity(sender, content, clients)
    print(f"     Entity: {entity['type']} - {entity['name']}")
    
    intent = detect_intent(subject, content, rules)
    print(f"     Intent: {intent['type']} ({intent['confidence']} confidence)")
    
    # Create task
    task_id, task_file = create_task_file(vault_path, metadata, content, source_id, entity, intent)
    print(f"     Task created: {task_id}")
    
    # Move to processed
    archive_root = resolve_folder(vault_path, "Archive", ["ARCHIVE", "ARCHIVED", "Archived", "ARCHIVED"])
    archive_processed = archive_root / 'processed'
    archive_processed.mkdir(parents=True, exist_ok=True)
    inbox_file.rename(archive_processed / inbox_file.name)
    
    # Update dashboard
    summary = f"{entity['name']} - {intent['type']}"
    update_dashboard_light(vault_path, task_id, metadata.get('type', 'unknown'), summary)
    
    # Log
    log_action(vault_path, 'triage', source_id, 'actionable', {
        'task_created': task_id,
        'entity': entity,
        'intent': intent,
        'destination': str(task_file)
    })

def main():
    if len(sys.argv) < 2:
        print("Usage: python triage_inbox.py /path/to/vault")
        sys.exit(1)
    
    vault_path = Path(sys.argv[1])
    inbox_path = resolve_folder(vault_path, "Inbox", ["INBOX"])
    
    if not inbox_path.exists():
        print(f"Inbox not found: {inbox_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("INBOX ORCHESTRATOR - Triage Processing")
    print("=" * 60)
    
    # Load context
    print("\nLoading context...")
    rules = load_handbook(vault_path)
    clients = load_clients_context(vault_path)
    print(f"  Loaded {len(clients)} client profiles")
    
    # Process inbox
    inbox_items = list(inbox_path.glob('*.md'))
    print(f"\nFound {len(inbox_items)} items in inbox")
    
    if not inbox_items:
        print("  No items to process")
        return
    
    processed = 0
    for inbox_file in inbox_items:
        try:
            process_inbox_item(inbox_file, vault_path, rules, clients)
            processed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"✅ Processed {processed}/{len(inbox_items)} items")
    print("=" * 60)

if __name__ == '__main__':
    main()
