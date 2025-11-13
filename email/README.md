# Email MCP Server

An MCP (Model Context Protocol) server that provides email management capabilities for Gmail, including fetching unread emails, generating AI-powered draft replies using Claude, and saving drafts.

## Features

- **Fetch Unread Emails**: Retrieve unread emails from your Gmail inbox via IMAP
- **Generate AI Draft Replies**: Use Claude AI to generate contextual email replies with customizable tone
- **Save Drafts**: Save draft emails directly to Gmail
- **Send Emails**: Send emails via Gmail SMTP

## Prerequisites

- Python 3.8+
- Gmail account with App Password enabled
- Anthropic API key (for AI-powered draft replies)

## Setup

### 1. Enable Gmail App Password

1. Go to your Google Account settings
2. Navigate to Security > 2-Step Verification
3. At the bottom, select "App passwords"
4. Generate a new app password for "Mail"
5. Save this password securely

### 2. Install Dependencies

```bash
cd email
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set Environment Variables

```bash
export EMAIL_USER="your-email@gmail.com"
export EMAIL_APP_PASSWORD="your-app-password"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

Or create a `.env` file:

```env
EMAIL_USER=your-email@gmail.com
EMAIL_APP_PASSWORD=your-app-password
ANTHROPIC_API_KEY=your-anthropic-api-key
```

### 4. Configure MCP Client

Add to your MCP client configuration (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "email": {
      "command": "python",
      "args": ["/path/to/mcp-servers/email/email_server.py"],
      "env": {
        "EMAIL_USER": "your-email@gmail.com",
        "EMAIL_APP_PASSWORD": "your-app-password",
        "ANTHROPIC_API_KEY": "your-anthropic-api-key"
      }
    }
  }
}
```

## Available Tools

### 1. get_unread_emails

Fetch unread emails from Gmail inbox.

**Parameters:**
- `max_emails` (optional): Maximum number of emails to fetch (default: 10)

**Example:**
```json
{
  "max_emails": 5
}
```

### 2. generate_draft_reply

Generate an AI-powered draft reply using Claude.

**Parameters:**
- `email_from`: The sender's email address
- `email_subject`: The subject of the email
- `email_body`: The body of the email
- `email_date`: The date of the email
- `tone` (optional): Tone of the reply (e.g., "professional", "casual", "friendly")
- `additional_context` (optional): Additional context for the AI to consider

**Example:**
```json
{
  "email_from": "sender@example.com",
  "email_subject": "Project Update",
  "email_body": "How is the project coming along?",
  "email_date": "Mon, 13 Nov 2024 10:30:00",
  "tone": "professional",
  "additional_context": "The project is on track and will be completed by Friday"
}
```

### 3. save_draft

Save a draft email to Gmail.

**Parameters:**
- `to`: Recipient email address
- `subject`: Email subject
- `body`: Email body content
- `in_reply_to` (optional): Message ID of the email being replied to

**Example:**
```json
{
  "to": "recipient@example.com",
  "subject": "Re: Project Update",
  "body": "The project is progressing well...",
  "in_reply_to": "<message-id@example.com>"
}
```

### 4. send_email

Send an email immediately.

**Parameters:**
- `to`: Recipient email address
- `subject`: Email subject
- `body`: Email body content

**Example:**
```json
{
  "to": "recipient@example.com",
  "subject": "Hello",
  "body": "This is a test email."
}
```

## Workflow Example

1. **Fetch unread emails:**
   ```
   Use get_unread_emails tool with max_emails=5
   ```

2. **Generate a draft reply:**
   ```
   Use generate_draft_reply tool with email details and desired tone
   ```

3. **Save the draft to Gmail:**
   ```
   Use save_draft tool with the generated reply
   ```

## Security Notes

- Never commit your `.env` file or credentials to version control
- Use Gmail App Passwords instead of your main password
- Keep your Anthropic API key secure
- Consider using a secrets manager for production deployments

## Troubleshooting

### Connection Issues

If you encounter IMAP connection issues:
1. Verify that IMAP is enabled in Gmail settings
2. Check that your App Password is correct
3. Ensure your firewall allows IMAP connections (port 993)

### Authentication Errors

- Make sure you're using an App Password, not your regular Gmail password
- Verify that 2-Step Verification is enabled on your Google account

### Draft Folder Issues

Gmail uses different folder names in different regions. The server attempts to use `[Gmail]/Drafts` first, then falls back to `Drafts`.

## Development

To run the server in development mode:

```bash
cd email
source venv/bin/activate
python email_server.py
```

## License

MIT License
