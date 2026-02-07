import time
import logging
import json
import os
import base64
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from google.auth.transport.requests import Request # type: ignore
from google.oauth2.credentials import Credentials # type: ignore
from google_auth_oauthlib.flow import InstalledAppFlow # type: ignore
from googleapiclient.discovery import build # type: ignore
from googleapiclient.errors import HttpError # type: ignore
from .config import load_config
from .log_jsonl import append_event

# Scopes required for reading Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailWatcher:
    def __init__(self):
        load_dotenv()
        self.config = load_config()
        self.vault_path = Path(self.config.vault_path)
        self.inbox_path = self.vault_path / self.config.folders["inbox"]
        self.logs_path = self.vault_path / self.config.folders["logs"]

        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Initialize Gmail service
        self.service = self._authenticate_gmail()

        # Track processed emails to avoid duplicates
        self.processed_emails_file = self.logs_path / "processed_emails.json"
        self.processed_emails = self._load_processed_emails()
        self.poll_seconds = int(os.getenv("GMAIL_POLL_SECONDS", "60"))
        self.query = os.getenv("GMAIL_QUERY", "is:unread")
        self.max_results = int(os.getenv("GMAIL_MAX_RESULTS", "10"))

    def _authenticate_gmail(self):
        """Authenticate and return Gmail service object"""
        creds = None

        # Token file stores the user's access and refresh tokens
        token_path = Path(os.getenv("GMAIL_TOKEN_JSON", str(Path.home() / ".token.gmail.json")))

        # Load existing credentials
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    self.logger.error(f"Could not refresh credentials: {e}")
                    # If refresh fails, delete the token and start fresh
                    if token_path.exists():
                        token_path.unlink()
                    creds = None

            if not creds:
                client_id = os.getenv("GMAIL_CLIENT_ID")
                client_secret = os.getenv("GMAIL_CLIENT_SECRET")

                if not client_id or not client_secret:
                    raise Exception("GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET must be set")

                client_config = {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["http://localhost"],
                    }
                }
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

                use_console = os.getenv("GMAIL_OAUTH_CONSOLE", "1") == "1"
                if not use_console:
                    try:
                        creds = flow.run_local_server(port=0, open_browser=False)
                    except Exception:
                        use_console = True

                if use_console:
                    flow.redirect_uri = "http://localhost"
                    auth_url, _ = flow.authorization_url(
                        access_type="offline",
                        include_granted_scopes="true",
                        prompt="consent",
                    )
                    print("Please visit this URL to authorize this application:")
                    print(auth_url)
                    try:
                        code = input("Enter the authorization code: ").strip()
                    except EOFError:
                        code = os.getenv("GMAIL_AUTH_CODE", "").strip()
                        if not code:
                            raise Exception(
                                "Authorization code not provided. Run in an interactive terminal or set GMAIL_AUTH_CODE."
                            )
                    flow.fetch_token(code=code)
                    creds = flow.credentials

                # Save the credentials for the next run
                token_path.parent.mkdir(parents=True, exist_ok=True)
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)

    def _load_processed_emails(self) -> set:
        """Load previously processed email IDs from file"""
        if self.processed_emails_file.exists():
            try:
                with open(self.processed_emails_file, 'r') as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def _save_processed_emails(self):
        """Save processed email IDs to file"""
        self.processed_emails_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.processed_emails_file, 'w') as f:
            json.dump(list(self.processed_emails), f)

    def _extract_email_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant content from Gmail message"""
        payload = message.get('payload', {})
        headers = payload.get('headers', [])

        # Extract headers
        header_dict = {}
        for header in headers:
            name = header.get('name', '').lower()
            value = header.get('value', '')
            header_dict[name] = value

        # Extract body content
        body = ""
        parts = payload.get('parts', [])

        if parts:
            # Look for the text/plain part
            for part in parts:
                if part.get('mimeType') == 'text/plain':
                    body_data = part.get('body', {}).get('data', '')
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='replace')
                    break
                elif part.get('mimeType') == 'text/html':
                    # Fallback to HTML if no plain text
                    body_data = part.get('body', {}).get('data', '')
                    if body_data:
                        html_body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='replace')
                        # Simple HTML to text conversion
                        body = re.sub('<[^<]+?>', '', html_body)
                    break
        else:
            # Message might be in the payload body directly
            body_data = payload.get('body', {}).get('data', '')
            if body_data:
                body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='replace')

        return {
            'id': message.get('id'),
            'thread_id': message.get('threadId'),
            'snippet': message.get('snippet', ''),
            'subject': header_dict.get('subject', 'No Subject'),
            'from': header_dict.get('from', 'Unknown Sender'),
            'to': header_dict.get('to', ''),
            'date': header_dict.get('date', ''),
            'body': body[:2000],  # Limit body length
            'labels': message.get('labelIds', [])
        }

    def _is_actionable_email(self, email_data: Dict[str, Any]) -> bool:
        """Determine if an email is actionable based on content and sender"""
        # Define criteria for actionable emails
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        sender = email_data.get('from', '').lower()

        # Keywords that indicate actionability
        actionable_keywords = [
            'urgent', 'asap', 'action', 'required', 'needed', 'deadline',
            'reply', 'response', 'meeting', 'appointment', 'invoice',
            'payment', 'bill', 'contract', 'agreement', 'follow up',
            'remind', 'todo', 'task', 'help', 'support', 'assistance'
        ]

        # Check if any actionable keywords are in subject or body
        for keyword in actionable_keywords:
            if keyword in subject or keyword in body:
                return True

        # Check if from known important contacts
        # This could be extended with a list of important contacts
        if '@client.com' in sender or '@customer.' in sender:
            return True

        # Emails from specific domains might be actionable
        important_domains = ['@client.', '@customer.', '@vendor.', '@supplier.']
        for domain in important_domains:
            if domain in sender:
                return True

        # Default: non-actionable
        return False

    def _create_obsidian_task(self, email_data: Dict[str, Any]):
        """Create an Obsidian task file in the inbox folder"""
        is_actionable = self._is_actionable_email(email_data)
        status = "actionable" if is_actionable else "info_only"

        # Create filename with timestamp and email ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"GMAIL_{timestamp}_{email_data['id'][:8]}.md"
        filepath = self.inbox_path / filename

        # Create markdown content with YAML front matter
        markdown_content = f"""---
type: email
source: gmail
status: {status}
from: "{email_data['from']}"
subject: "{email_data['subject']}"
received: "{email_data['date']}"
gmail_id: "{email_data['id']}"
thread_id: "{email_data['thread_id']}"
labels: {email_data['labels']}
priority: {"high" if is_actionable else "low"}
---

# Email from: {email_data['from']}

**Subject:** {email_data['subject']}

**Received:** {email_data['date']}

## Email Body

{email_data['body']}

## Action Required

{'[ ] Review and respond to this email' if is_actionable else '[x] Read and filed as information'}

## Original Snippet

> {email_data['snippet']}

---
*Processed by AI Employee Gmail Watcher*
"""

        # Write the markdown file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        self.logger.info(f"Created task file: {filepath}")

        # Log the event
        append_event(
            self.vault_path,
            {
                "event": "gmail_email_processed",
                "component": "gmail_watcher",
                "email_id": email_data['id'],
                "subject": email_data['subject'],
                "is_actionable": is_actionable,
                "file_path": str(filepath)
            }
        )

    def check_new_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """Check for new emails and return them"""
        try:
            # Query for unread emails (you can customize this query)
            query = self.query
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            new_emails = []

            for message_info in messages:
                email_id = message_info['id']

                # Skip if already processed
                if email_id in self.processed_emails:
                    continue

                try:
                    # Get full message details
                    message = self.service.users().messages().get(
                        userId='me',
                        id=email_id
                    ).execute()

                    email_data = self._extract_email_content(message)
                    new_emails.append(email_data)

                    # Mark as processed
                    self.processed_emails.add(email_id)

                except HttpError as e:
                    self.logger.error(f"Error retrieving email {email_id}: {e}")

            # Save processed email IDs
            self._save_processed_emails()

            return new_emails

        except HttpError as e:
            self.logger.error(f"Gmail API error: {e}")
            return []

    def run_once(self):
        """Run a single check for new emails"""
        self.logger.info("Checking for new Gmail messages...")

        new_emails = self.check_new_emails()

        if new_emails:
            self.logger.info(f"Found {len(new_emails)} new emails")

            for email_data in new_emails:
                self._create_obsidian_task(email_data)
        else:
            self.logger.info("No new emails found")

    def run_continuous(self):
        """Run continuously, checking for new emails at specified intervals"""
        self.logger.info(f"Starting Gmail watcher (checking every {self.poll_seconds} seconds)")

        while True:
            try:
                self.run_once()
                time.sleep(self.poll_seconds)
            except KeyboardInterrupt:
                self.logger.info("Gmail watcher stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in Gmail watcher: {e}")
                time.sleep(self.poll_seconds)


def main():
    """Main function to run the Gmail watcher"""
    try:
        watcher = GmailWatcher()
        # Run continuously
        watcher.run_continuous()
    except Exception as e:
        print(f"Error initializing Gmail watcher: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
