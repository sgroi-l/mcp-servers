#!/usr/bin/env python3

import asyncio
import os
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from imapclient import IMAPClient
import email
from email.header import decode_header
from email_reply_parser import EmailReplyParser
import anthropic


async def send_email(to: str, subject: str, body: str):
    email_user = os.environ['EMAIL_USER']
    email_password = os.environ['EMAIL_APP_PASSWORD']

    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(email_user, email_password)
        server.send_message(msg)


def decode_mime_words(s):
    """Decode MIME encoded-word strings"""
    if s is None:
        return ""
    decoded_fragments = decode_header(s)
    return ''.join(
        str(fragment, encoding or 'utf-8') if isinstance(fragment, bytes) else str(fragment)
        for fragment, encoding in decoded_fragments
    )


async def get_unread_emails(max_emails: int = 10):
    """Fetch unread emails from Gmail via IMAP"""
    email_user = os.environ['EMAIL_USER']
    email_password = os.environ['EMAIL_APP_PASSWORD']

    # Connect to Gmail IMAP
    with IMAPClient('imap.gmail.com', ssl=True) as client:
        client.login(email_user, email_password)
        client.select_folder('INBOX', readonly=True)

        # Search for unread messages
        messages = client.search(['UNSEEN'])

        if not messages:
            return []

        # Limit to max_emails
        messages = messages[:max_emails]

        # Fetch message data
        response = client.fetch(messages, ['RFC822', 'FLAGS'])

        emails = []
        for msg_id, data in response.items():
            raw_email = data[b'RFC822']
            msg = email.message_from_bytes(raw_email)

            # Extract email details
            from_addr = decode_mime_words(msg.get('From', ''))
            subject = decode_mime_words(msg.get('Subject', ''))
            date = msg.get('Date', '')
            message_id = msg.get('Message-ID', '')

            # Extract email body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition', ''))

                    if content_type == 'text/plain' and 'attachment' not in content_disposition:
                        try:
                            body = part.get_payload(decode=True).decode()
                            break
                        except:
                            pass
            else:
                try:
                    body = msg.get_payload(decode=True).decode()
                except:
                    body = str(msg.get_payload())

            # Parse reply using email_reply_parser
            parsed_body = EmailReplyParser.parse_reply(body)

            emails.append({
                'id': str(msg_id),
                'message_id': message_id,
                'from': from_addr,
                'subject': subject,
                'date': date,
                'body': parsed_body,
                'full_body': body
            })

        return emails


async def generate_draft_reply(email_content: dict, tone: str = "professional", additional_context: str = ""):
    """Generate an AI-powered draft reply using Claude"""
    anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required")

    client = anthropic.Anthropic(api_key=anthropic_api_key)

    # Construct the prompt
    prompt = f"""You are helping draft a reply to an email. Generate a {tone} response.

Original Email:
From: {email_content['from']}
Subject: {email_content['subject']}
Date: {email_content['date']}

Body:
{email_content['body']}

{f"Additional Context: {additional_context}" if additional_context else ""}

Please generate a clear, concise, and {tone} reply to this email. Only provide the email body text, without any subject line or greetings like "Dear [Name]" unless specifically needed for the context."""

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text


async def save_draft_to_gmail(to: str, subject: str, body: str, in_reply_to: str = None):
    """Save a draft email to Gmail"""
    email_user = os.environ['EMAIL_USER']
    email_password = os.environ['EMAIL_APP_PASSWORD']

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = to
    msg['Subject'] = subject
    if in_reply_to:
        msg['In-Reply-To'] = in_reply_to
        msg['References'] = in_reply_to
    msg.attach(MIMEText(body, 'plain'))

    # Connect to Gmail IMAP and save as draft
    with IMAPClient('imap.gmail.com', ssl=True) as client:
        client.login(email_user, email_password)

        # Gmail uses [Gmail]/Drafts folder
        try:
            client.select_folder('[Gmail]/Drafts')
        except:
            # Try alternative draft folder names
            client.select_folder('Drafts')

        # Append the message to the Drafts folder
        client.append('[Gmail]/Drafts', msg.as_bytes(), flags=['\\Draft'])

    return True


server = Server("email-server")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="send_email",
            description="Send an email",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body content"},
                },
                "required": ["to", "subject", "body"],
            },
        ),
        types.Tool(
            name="get_unread_emails",
            description="Fetch unread emails from Gmail inbox",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_emails": {
                        "type": "number",
                        "description": "Maximum number of unread emails to fetch (default: 10)",
                        "default": 10
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="generate_draft_reply",
            description="Generate an AI-powered draft reply to an email using Claude",
            inputSchema={
                "type": "object",
                "properties": {
                    "email_from": {"type": "string", "description": "The sender of the email to reply to"},
                    "email_subject": {"type": "string", "description": "The subject of the email to reply to"},
                    "email_body": {"type": "string", "description": "The body of the email to reply to"},
                    "email_date": {"type": "string", "description": "The date of the email to reply to"},
                    "tone": {
                        "type": "string",
                        "description": "The tone of the reply (e.g., professional, casual, friendly)",
                        "default": "professional"
                    },
                    "additional_context": {
                        "type": "string",
                        "description": "Additional context or instructions for the reply",
                        "default": ""
                    },
                },
                "required": ["email_from", "email_subject", "email_body", "email_date"],
            },
        ),
        types.Tool(
            name="save_draft",
            description="Save a draft email to Gmail",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body content"},
                    "in_reply_to": {
                        "type": "string",
                        "description": "Message ID of the email being replied to (optional)"
                    },
                },
                "required": ["to", "subject", "body"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "send_email":
        to = arguments["to"]
        subject = arguments["subject"]
        body = arguments["body"]

        await send_email(to, subject, body)
        return [types.TextContent(type="text", text=f"✓ Email sent to {to}")]

    elif name == "get_unread_emails":
        max_emails = arguments.get("max_emails", 10)
        emails = await get_unread_emails(max_emails)

        if not emails:
            return [types.TextContent(type="text", text="No unread emails found.")]

        # Format emails for display
        result = f"Found {len(emails)} unread email(s):\n\n"
        for i, email in enumerate(emails, 1):
            result += f"--- Email {i} ---\n"
            result += f"From: {email['from']}\n"
            result += f"Subject: {email['subject']}\n"
            result += f"Date: {email['date']}\n"
            result += f"Message ID: {email['message_id']}\n"
            result += f"Body:\n{email['body']}\n\n"

        return [types.TextContent(type="text", text=result)]

    elif name == "generate_draft_reply":
        email_content = {
            'from': arguments['email_from'],
            'subject': arguments['email_subject'],
            'body': arguments['email_body'],
            'date': arguments['email_date']
        }
        tone = arguments.get('tone', 'professional')
        additional_context = arguments.get('additional_context', '')

        draft_reply = await generate_draft_reply(email_content, tone, additional_context)

        result = f"Generated Draft Reply:\n\n{draft_reply}\n\n"
        result += f"(Tone: {tone})"

        return [types.TextContent(type="text", text=result)]

    elif name == "save_draft":
        to = arguments["to"]
        subject = arguments["subject"]
        body = arguments["body"]
        in_reply_to = arguments.get("in_reply_to")

        await save_draft_to_gmail(to, subject, body, in_reply_to)
        return [types.TextContent(type="text", text=f"✓ Draft saved to Gmail for {to}")]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="email-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())