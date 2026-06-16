"""
JARVIS — Email Agent
Gmail read, send, draft, and manage via IMAP/SMTP.
Refactored from gmail_agent.py — now integrated as the 5th agent.
"""

import imaplib
import smtplib
import ssl
from email import message_from_bytes
from email.header import decode_header, make_header

from backend.agents.base import BaseAgent
from backend.config import llm, GMAIL_EMAIL, GMAIL_APP_PASSWORD, GROQ_API_KEY
from backend.logger import get_logger

logger = get_logger("agents.email")


class EmailAgent(BaseAgent):
    name = "email"
    description = "Read, send, draft, summarize, or manage emails via Gmail. Handle inbox queries, compose messages, and email-related tasks."

    def __init__(self):
        self.email = GMAIL_EMAIL
        self.password = GMAIL_APP_PASSWORD

    def _connect_imap(self):
        """Connect to Gmail IMAP."""
        if not self.email or not self.password:
            raise RuntimeError("Set GMAIL_EMAIL and GMAIL_APP_PASSWORD in your .env file")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(self.email, self.password)
        return mail

    def _extract_body(self, msg) -> str:
        """Extract plain text body from an email message."""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode(errors="ignore")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode(errors="ignore")
        return ""

    def list_emails(self, limit: int = 5) -> str:
        """List recent emails from inbox."""
        logger.info(f"Fetching {limit} recent emails...")
        mail = self._connect_imap()
        mail.select("INBOX")
        status, messages = mail.search(None, "ALL")
        if status != "OK":
            mail.close()
            mail.logout()
            return "Could not search inbox."

        ids = list(reversed(messages[0].split()))[:limit]
        results = []
        for msg_id in ids:
            status, data = mail.fetch(msg_id, "(BODY.PEEK[HEADER])")
            if status == "OK":
                msg = message_from_bytes(data[0][1])
                subject = str(make_header(decode_header(msg.get("Subject", ""))))
                sender = msg.get("From", "")
                results.append(f"• [{msg_id.decode()}] From: {sender} | Subject: {subject}")

        mail.close()
        mail.logout()
        return "\n".join(results) if results else "No emails found."

    def read_email(self, message_id: str) -> str:
        """Read a specific email by ID."""
        logger.info(f"Reading email ID: {message_id}")
        mail = self._connect_imap()
        mail.select("INBOX")
        status, data = mail.fetch(message_id, "(RFC822)")
        if status != "OK":
            mail.close()
            mail.logout()
            return f"Could not read message {message_id}"

        msg = message_from_bytes(data[0][1])
        mail.close()
        mail.logout()

        subject = str(make_header(decode_header(msg.get("Subject", ""))))
        body = self._extract_body(msg)
        return f"Subject: {subject}\nFrom: {msg.get('From', '')}\nTo: {msg.get('To', '')}\n\n{body}"

    def send_email(self, to: str, subject: str, body: str) -> str:
        """Send an email via Gmail SMTP."""
        if not self.email or not self.password:
            return "Error: Set GMAIL_EMAIL and GMAIL_APP_PASSWORD in your .env file"

        logger.info(f"Sending email to: {to}")
        msg_content = f"Subject: {subject}\n\n{body}".encode("utf-8")
        context = ssl.create_default_context()
        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls(context=context)
                server.login(self.email, self.password)
                server.sendmail(self.email, to, msg_content)
            logger.info("Email sent successfully.")
            return f"Email sent to {to} with subject: {subject}"
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return f"Email send error: {str(e)}"

    def run(self, query: str) -> str:
        """
        Process email-related queries using LLM to determine intent.
        Falls back to listing recent emails if intent is unclear.
        """
        logger.info(f"Processing email task: {query[:80]}...")
        query_lower = query.lower()

        try:
            # Simple intent routing
            if any(word in query_lower for word in ["list", "inbox", "recent", "unread", "check"]):
                return self.list_emails()
            elif "send" in query_lower or "compose" in query_lower:
                # Use LLM to extract email details
                from langchain_core.prompts import ChatPromptTemplate
                from langchain_core.output_parsers import StrOutputParser

                extract_prompt = ChatPromptTemplate.from_messages([
                    (
                        "system",
                        "Extract email details from the user query. Return in this exact format:\n"
                        "TO: <email address>\nSUBJECT: <subject line>\nBODY: <email body>\n"
                        "If any field is missing, use MISSING as the value.",
                    ),
                    ("human", "{query}"),
                ])
                chain = extract_prompt | llm | StrOutputParser()
                result = chain.invoke({"query": query})

                # Parse the LLM output
                lines = result.strip().split("\n")
                details = {}
                for line in lines:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        details[key.strip().upper()] = value.strip()

                to = details.get("TO", "MISSING")
                subject = details.get("SUBJECT", "MISSING")
                body = details.get("BODY", "MISSING")

                if to == "MISSING":
                    return "Could not determine recipient email address. Please specify who to send the email to."
                return self.send_email(to, subject, body)
            elif "read" in query_lower or "open" in query_lower:
                # Try to extract message ID
                words = query.split()
                for word in words:
                    if word.isdigit():
                        return self.read_email(word)
                return "Please specify an email ID to read. Use 'list emails' first to see IDs."
            else:
                # Default: list recent emails
                return self.list_emails()
        except Exception as e:
            logger.error(f"Email agent failed: {e}")
            return f"Email error: {str(e)}"
