# Task Template

Output format for tasks created by inbox-orchestrator.

## File Location
`/vault/Needs_Action/TASK_{date}_{id}.md`

## Complete Template

```markdown
---
task_id: TASK_2026-02-06_abc123
created: "2026-02-06T10:30:00+05:00"
source_type: email | whatsapp | file_drop
source_id: EMAIL_12345
status: pending

# Business Context (filled by inbox-orchestrator)
entity_type: known_client | new_lead | vendor | unknown
entity_name: "Client A"
entity_ref: /vault/Clients/ClientA.md
related_project: /vault/Projects/ProjectName.md

# Classification (filled by task-classifier skill)
category: null
priority: null
estimated_effort: null
---

## Source: Email

**From:** sender@example.com  
**Subject:** Email subject  
**Received:** 2026-02-06 10:00

## Raw Content

[Original email/message content]

## AI Analysis

### Entity Context
- **Type:** known_client
- **Name:** Client A
- **Tier:** premium
- **Profile:** [ClientA.md](/vault/Clients/ClientA.md)

### Intent Recognition
- **Type:** invoice_request
- **Confidence:** high

## Suggested Actions

- [ ] Review and classify priority
- [ ] Determine appropriate response
- [ ] Execute action or seek approval

---
*Processed by: inbox-orchestrator v1.0*  
*Phase: Triage Complete*
```

## Field Descriptions

### Metadata (YAML Frontmatter)

**task_id** (required)
- Format: `TASK_{YYYY-MM-DD}_{random_id}`
- Example: `TASK_2026-02-06_abc123`
- Unique identifier for this task

**created** (required)
- ISO 8601 timestamp with timezone
- When task was created

**source_type** (required)
- Values: `email`, `whatsapp`, `file_drop`
- Origin of the inbox item

**source_id** (required)
- Original inbox filename stem
- Example: `EMAIL_12345`, `WHATSAPP_1738823400`

**status** (required)
- Initial: `pending`
- Later: `in_progress`, `awaiting_approval`, `done`

**entity_type** (required)
- Values: `known_client`, `new_lead`, `vendor`, `unknown`
- Result of entity identification

**entity_name** (required)
- Human-readable name
- From client profile or extracted from email

**entity_ref** (optional)
- Path to client/entity profile file
- Example: `/vault/Clients/ClientA.md`
- null if unknown entity

**related_project** (optional)
- Path to related project file
- null if no project match

**category** (null initially)
- Filled by task-classifier skill
- Values: `finance`, `sales`, `support`, `operations`, `personal`

**priority** (null initially)
- Filled by task-classifier skill
- Values: `high`, `medium`, `low`

**estimated_effort** (null initially)
- Filled by task-classifier skill
- Format: `15_minutes`, `30_minutes`, `1_hour`, `2_hours`

### Body Content

**## Source Section**
- Shows source type and key metadata
- Formatted for human readability

**## Raw Content**
- Unmodified original message/file description
- Preserves formatting

**## AI Analysis**
- Entity context from identification
- Intent detection results
- Helps human reviewer understand AI reasoning

**## Suggested Actions**
- Checkbox list of next steps
- Filled based on intent type
- Can be customized by human

**## Context Links** (optional)
- References to related vault files
- Makes it easy to load full context

## Intent-Specific Variations

### Invoice Request Task

```markdown
## Suggested Actions

- [ ] Verify amount against /vault/Accounting/Rates.md
- [ ] Check project completion status
- [ ] Generate invoice PDF
- [ ] Draft email reply using template
- [ ] Get approval before sending
- [ ] Log transaction after send
```

### Meeting Request Task

```markdown
## Suggested Actions

- [ ] Check calendar availability
- [ ] Propose 2-3 time slots
- [ ] Draft meeting confirmation email
- [ ] Add to calendar after confirmation
```

### Support Question Task

```markdown
## Suggested Actions

- [ ] Review question details
- [ ] Check documentation/past tickets
- [ ] Draft detailed response
- [ ] Follow up to ensure resolved
```

### Sales Inquiry Task

```markdown
## Suggested Actions

- [ ] Qualify lead (budget, timeline, fit)
- [ ] Prepare pricing/proposal
- [ ] Schedule discovery call
- [ ] Add to CRM/follow-up list
```

## Usage in Other Skills

### task-classifier reads this
```python
task_metadata, _ = parse_yaml_frontmatter(task_file)

# Update classification fields
task_metadata['category'] = 'finance'
task_metadata['priority'] = 'high'
task_metadata['estimated_effort'] = '30_minutes'

# Rewrite file with updated metadata
```

### plan-creator reads this
```python
# Load task for planning
task = load_task('/vault/Needs_Action/TASK_abc123.md')

# Use entity and intent to create plan
if task.intent == 'invoice_request':
    create_invoice_plan(task)
```

### dashboard-updater reads this
```python
# Count tasks by priority
for task_file in needs_action.glob('*.md'):
    task = parse_yaml_frontmatter(task_file)
    priority_counts[task['priority']] += 1
```