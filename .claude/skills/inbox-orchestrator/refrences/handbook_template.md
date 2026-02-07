# Company Handbook Template

This file provides the template for `/vault/Company_Handbook.md` which is **REQUIRED** for inbox-orchestrator to function.

## Complete Template

Save this as `/vault/Company_Handbook.md`:

```markdown
# Company Handbook

---
last_updated: 2026-02-06
version: 1.0
---

## Email Processing Rules

### Auto-Delete (Spam)

Emails matching these patterns will be filtered to `/Archive/spam/`:

**Subject Keywords:**
- unsubscribe
- newsletter
- promotion
- limited time offer
- click here now
- act now
- buy now

**Sender Domains:**
- noreply@*
- do-not-reply@*
- marketing@*
- *.spam.com

### Auto-Archive (FYI Only)

Items that don't require action, moved to `/Archive/fyi/`:

**Types:**
- bank_statement (already logged in accounting)
- social_notification (Facebook, Twitter alerts)
- system_alert (server notifications, cron outputs)
- automated_report (weekly/monthly summaries)

### High Priority Triggers

Messages matching these get flagged for immediate attention:

**Keywords:**
- urgent
- asap
- emergency
- critical
- overdue
- past due
- deadline today

**Client-Based:**
- Any message from premium tier clients
- Payment-related issues from any client
- Contract or legal matters

**Financial:**
- Amounts > $1,000
- Payment disputes
- Invoice issues

### Medium Priority

Standard business communications:

- Invoice requests from any client
- Meeting scheduling requests
- Proposal or quote requests
- Support questions from qualified leads
- Project status inquiries

### Low Priority

General inquiries and non-urgent matters:

- Information requests from unknown senders
- First-time contact (cold outreach)
- General "how do I..." questions
- Newsletter-style updates from partners

## Client Communication Rules

### Response Time Targets

- **Premium clients:** < 4 hours
- **Standard clients:** < 24 hours
- **New leads:** < 48 hours
- **General inquiries:** < 72 hours

### Approval Requirements

Always require human approval for:

- **Payments > $500**
- **New payees** (any amount)
- **Bulk emails** (> 5 recipients)
- **Contract modifications**
- **Sensitive client communications**

### Tone Guidelines

- **Premium clients:** Personalized, proactive
- **Standard clients:** Professional, helpful
- **New leads:** Friendly, concise
- **Support cases:** Patient, detailed

## Financial Rules

### Invoice Generation

1. Always verify amount against `/vault/Accounting/Rates.md`
2. Check project completion status
3. Use client-specific payment terms (from client profile)
4. Include project reference in invoice

### Payment Processing

1. Never auto-execute payments > $100
2. New payees require manual approval (any amount)
3. Log all transactions immediately
4. Flag unusual amounts for review (±20% from expected)

### Subscription Audit

Flag for review if:
- No login/usage in 30 days
- Cost increased > 20%
- Duplicate functionality with another tool
- Annual renewal approaching

## Categories

Used by task-classifier skill to categorize tasks:

### Finance
- invoice, payment, bill, receipt
- expense report, budget
- subscription review
- tax matters

### Sales
- quote, proposal, pricing
- new leads, cold outreach
- contract negotiation
- partnership opportunities

### Support
- help, question, issue, problem
- bug report, error
- how-to, troubleshooting
- feature request

### Operations
- meeting, schedule, calendar
- file review, admin task
- internal updates
- team coordination

### Personal
- personal errands
- family matters
- health appointments
- personal finance

## Intent Keywords

Mapping for intent detection:

### Invoice/Payment
- invoice, bill, receipt, statement
- payment, pay, paid
- outstanding, due, overdue

### Meeting/Schedule
- meeting, call, video call
- schedule, calendar, availability
- reschedule, cancel

### Support/Help
- help, assist, support
- question, wondering, curious
- issue, problem, bug, error
- how to, how do I

### Sales/Proposal
- pricing, quote, quotation
- proposal, bid
- interested, looking for
- want to hire, need service

## Entity Recognition

### Known Client Indicators
- Email address in `/vault/Clients/*.md`
- Domain matches client domain
- CC'd email in client profile

### New Lead Indicators
- Keywords: pricing, quote, proposal, interested
- Professional email domain (not Gmail/Yahoo)
- Mentions specific services

### Vendor Indicators
- Invoice from known vendor
- Recurring payment patterns
- Service provider domains

## Automation Rules

### Auto-Create Tasks For
- Client emails (known clients)
- Invoices and payments
- Meeting requests
- Support questions from active projects
- Sales inquiries mentioning specific services

### Auto-Archive Without Task
- Spam (as defined above)
- FYI items (as defined above)
- Duplicate messages
- Out of office replies
- Delivery status notifications
```

## Customization Guide

### Adding New Spam Patterns

```markdown
### Auto-Delete (Spam)

**Subject Keywords:**
- unsubscribe
- YOUR_NEW_KEYWORD_HERE
```

### Defining Client Tiers

Create client profiles in `/vault/Clients/ClientName.md`:

```markdown
---
tier: premium | standard | basic
---
```

Then reference in handbook:

```markdown
### High Priority Triggers

**Client-Based:**
- Any message from premium tier clients
```

### Custom Categories

Add new categories:

```markdown
## Categories

### Marketing
- social media, content
- campaign, analytics
- SEO, ads
```

Then task-classifier will use them automatically.

## Validation

Test your handbook:

```bash
# Create test inbox item
cat > /vault/Inbox/EMAIL_test.md << 'EOF'
---
type: email
from: spam@marketing.com
subject: Limited time offer - buy now!
---
Test spam email
EOF

# Run triage
python scripts/triage_inbox.py /vault

# Check: Should be in /Archive/spam/
ls /vault/Archive/spam/EMAIL_test.md
```

## Troubleshooting

**Everything going to spam:**
- Check spam keywords aren't too broad
- Review sender domain patterns
- Add known clients to `/vault/Clients/`

**Nothing being filtered:**
- Verify handbook syntax is valid YAML/Markdown
- Check keywords are lowercase
- Test with obvious spam message

**Wrong categories:**
- Review category keyword mappings
- Add more specific keywords
- Use exact phrases that appear in your emails