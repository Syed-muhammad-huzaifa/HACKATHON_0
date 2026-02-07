# Watcher Output Formats

Expected inbox item formats created by watchers (Gmail, WhatsApp, Filesystem).

## General Rules

All inbox items MUST:
1. Be markdown files (`.md` extension)
2. Have YAML frontmatter with required fields
3. Use naming pattern: `{SOURCE}_{id}.md`
4. Be placed in `/vault/Inbox/`

## EMAIL Format (from Gmail Watcher)

**Filename:** `EMAIL_{message_id}.md`

**Required Frontmatter:**
```yaml
---
type: email
from: sender@example.com
subject: "Email subject line"
received: "2026-02-06T10:00:00+05:00"
priority: high | medium | low
status: pending
---
```

**Body:**
```markdown
## Email Content

[Email body text or snippet]

## Attachments
- filename1.pdf
- filename2.xlsx
```

**Full Example:**
```markdown
---
type: email
from: client@company.com
subject: "Need invoice for January"
received: "2026-02-06T10:30:00+05:00"
priority: high
status: pending
---

## Email Content

Hi,

Can you send me the invoice for January's work on the website project?

Thanks,
John

## Attachments
None
```

## WHATSAPP Format (from WhatsApp Watcher)

**Filename:** `WHATSAPP_{timestamp}.md`

**Required Frontmatter:**
```yaml
---
type: whatsapp
from: "+15551234567"
contact_name: "John Smith" 
received: "2026-02-06T10:00:00+05:00"
priority: high | medium | low
status: pending
keywords: ["urgent", "invoice"]  # Matched keywords
---
```

**Body:**
```markdown
## Message Content

[WhatsApp message text]

## Media
- image.jpg
- document.pdf
```

**Full Example:**
```markdown
---
type: whatsapp
from: "+15551234567"
contact_name: "Client A - John"
received: "2026-02-06T10:45:00+05:00"
priority: high
status: pending
keywords: ["urgent", "invoice"]
---

## Message Content

Hey, urgent! Need the invoice by EOD today. Can you send ASAP?

## Media
None
```

## FILE Format (from Filesystem Watcher)

**Filename:** `FILE_{original_filename_stem}.md`

**Required Frontmatter:**
```yaml
---
type: file_drop
filename: "contract_review.pdf"
size: 245678  # bytes
received: "2026-02-06T10:00:00+05:00"
priority: medium
status: pending
file_path: "/vault/Inbox/contract_review.pdf"  # Actual file location
---
```

**Body:**
```markdown
## File Dropped

New file for processing: `contract_review.pdf`

**Size:** 240 KB  
**Type:** PDF Document

## Context
File dropped in watched folder for review.
```

**Full Example:**
```markdown
---
type: file_drop
filename: "Q4_Report.xlsx"
size: 1234567
received: "2026-02-06T11:00:00+05:00"
priority: medium
status: pending
file_path: "/vault/Inbox/Q4_Report.xlsx"
---

## File Dropped

New file for processing: `Q4_Report.xlsx`

**Size:** 1.2 MB  
**Type:** Excel Spreadsheet

## Context
Quarterly financial report dropped for review and analysis.
```

## Optional Fields

These fields are helpful but not required:

```yaml
# Email-specific
cc: ["person1@example.com", "person2@example.com"]
bcc: ["person3@example.com"]
reply_to: "noreply@example.com"
thread_id: "abc123"

# WhatsApp-specific
chat_id: "123456789@c.us"
group_name: "Project Team"  # If group message
quoted_message: "Previous message being replied to"

# File-specific
file_type: "pdf" | "xlsx" | "docx" | "jpg"
mime_type: "application/pdf"
tags: ["contract", "legal", "urgent"]
```

## Validation

Inbox items will be rejected if:

1. **No YAML frontmatter** - File must start with `---`
2. **Missing required field** - Must have: type, from/filename, received, status
3. **Invalid type** - Must be: email, whatsapp, or file_drop
4. **Malformed YAML** - Syntax errors in frontmatter

Rejected items are moved to `/vault/Archive/malformed/`

## Testing Your Watcher

Create a test inbox item:

```bash
cat > /vault/Inbox/EMAIL_test_123.md << 'EOF'
---
type: email
from: test@example.com
subject: "Test email"
received: "2026-02-06T12:00:00+05:00"
priority: medium
status: pending
---

## Email Content

This is a test email to verify the watcher format.
EOF

# Run triage
python scripts/triage_inbox.py /vault

# Verify task created
ls /vault/Needs_Action/TASK_*
```

## Watcher Implementation Examples

### Gmail Watcher (Simplified)

```python
def create_email_inbox_item(message_id, message_data):
    inbox_file = Path(f'/vault/Inbox/EMAIL_{message_id}.md')
    
    content = f'''---
type: email
from: {message_data['from']}
subject: "{message_data['subject']}"
received: "{datetime.now().isoformat()}"
priority: high
status: pending
---

## Email Content

{message_data['body']}

## Attachments
{message_data['attachments'] or 'None'}
'''
    
    inbox_file.write_text(content)
```

### WhatsApp Watcher (Simplified)

```python
def create_whatsapp_inbox_item(phone, name, text, keywords):
    timestamp = int(datetime.now().timestamp())
    inbox_file = Path(f'/vault/Inbox/WHATSAPP_{timestamp}.md')
    
    content = f'''---
type: whatsapp
from: "{phone}"
contact_name: "{name}"
received: "{datetime.now().isoformat()}"
priority: high
status: pending
keywords: {keywords}
---

## Message Content

{text}
'''
    
    inbox_file.write_text(content)
```

### Filesystem Watcher (Simplified)

```python
def create_file_inbox_item(file_path):
    file_stat = file_path.stat()
    inbox_file = Path(f'/vault/Inbox/FILE_{file_path.stem}.md')
    
    # Copy actual file to inbox
    shutil.copy(file_path, Path(f'/vault/Inbox/{file_path.name}'))
    
    content = f'''---
type: file_drop
filename: "{file_path.name}"
size: {file_stat.st_size}
received: "{datetime.now().isoformat()}"
priority: medium
status: pending
file_path: "/vault/Inbox/{file_path.name}"
---

## File Dropped

New file for processing: `{file_path.name}`

**Size:** {file_stat.st_size // 1024} KB  
**Type:** {file_path.suffix}
'''
    
    inbox_file.write_text(content)
```

## Troubleshooting

**Inbox items not being processed:**
1. Check YAML syntax with online validator
2. Verify all required fields present
3. Check filename follows pattern
4. Ensure file is in `/vault/Inbox/`

**Tasks created with wrong data:**
1. Review frontmatter field names (case-sensitive)
2. Check date format (ISO 8601)
3. Verify 'from' field has valid email/phone

**Watcher creating duplicate items:**
1. Track processed message IDs
2. Check before creating new file
3. Use unique identifiers in filename