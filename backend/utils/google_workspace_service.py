"""
JARVIS — Live Google Workspace Integration (Docs, Calendar with Meet, and Gmail)
Provides full live cloud capabilities for Google Docs creation, Google Calendar event scheduling with Google Meet links, and Gmail broadcasting.
"""

import os
import json
import base64
import urllib.parse
import requests
from email.mime.text import MIMEText
from backend.logger import get_logger
from backend.utils.google_sheets_service import get_fresh_access_token

logger = get_logger("utils.google_workspace")


def create_live_google_doc(title: str, text_body: str, user_email: str = "connected_user@google.com", access_token: str = None, refresh_token: str = None, user_key: str = None) -> dict:
    """
    Creates a real live Google Document inside the user's Google Drive account using Google Docs API REST endpoints.
    """
    logger.info(f"Creating live Google Doc '{title}' for {user_email} (token present: {bool(access_token or refresh_token)})...")
    
    active_token = access_token
    if not active_token and refresh_token:
        active_token = get_fresh_access_token(refresh_token)

    real_doc_url = None

    if active_token:
        try:
            # Step 1: Create blank document
            resp = requests.post(
                "https://docs.googleapis.com/v1/documents",
                headers={
                    "Authorization": f"Bearer {active_token}",
                    "Content-Type": "application/json"
                },
                json={"title": title},
                timeout=8
            )

            # Handle 401 token refresh
            if resp.status_code == 401 and refresh_token:
                active_token = get_fresh_access_token(refresh_token)
                if active_token:
                    resp = requests.post(
                        "https://docs.googleapis.com/v1/documents",
                        headers={
                            "Authorization": f"Bearer {active_token}",
                            "Content-Type": "application/json"
                        },
                        json={"title": title},
                        timeout=8
                    )

            if resp.status_code == 200:
                doc_json = resp.json()
                document_id = doc_json.get("documentId")
                real_doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
                logger.info(f"Successfully created real Google Doc in Drive! ID: {document_id}")

                # Step 2: Insert text body into document
                if text_body and document_id:
                    insert_payload = {
                        "requests": [
                            {
                                "insertText": {
                                    "location": {"index": 1},
                                    "text": text_body
                                }
                            }
                        ]
                    }
                    requests.post(
                        f"https://docs.googleapis.com/v1/documents/{document_id}:batchUpdate",
                        headers={
                            "Authorization": f"Bearer {active_token}",
                            "Content-Type": "application/json"
                        },
                        json=insert_payload,
                        timeout=8
                    )
            else:
                logger.warning(f"Google Docs API returned status {resp.status_code}: {resp.text}")
        except Exception as err:
            logger.error(f"Failed to call Google Docs API: {err}")

    if not real_doc_url:
        real_doc_url = "https://docs.google.com/document/create"

    return {
        "title": title,
        "google_docs_url": real_doc_url,
        "document_id": document_id if 'document_id' in locals() else None
    }


def create_google_calendar_event(summary: str, start_time_iso: str, end_time_iso: str, description: str = "", attendees: list = None, user_email: str = "connected_user@google.com", access_token: str = None, refresh_token: str = None, user_key: str = None) -> dict:
    """
    Schedules a real event on the user's primary Google Calendar with an automated Google Meet video conference link.
    """
    logger.info(f"Scheduling Google Calendar Event '{summary}' for {user_email}...")
    
    active_token = access_token
    if not active_token and refresh_token:
        active_token = get_fresh_access_token(refresh_token)

    event_url = None
    meet_link = None

    if active_token:
        try:
            payload = {
                "summary": summary,
                "description": description,
                "start": {"dateTime": start_time_iso, "timeZone": "Asia/Kolkata"},
                "end": {"dateTime": end_time_iso, "timeZone": "Asia/Kolkata"},
                "conferenceData": {
                    "createRequest": {
                        "requestId": f"jarvis_meet_{int(os.times()[4]*1000)}",
                        "conferenceSolutionKey": {"type": "hangoutsMeet"}
                    }
                }
            }
            if attendees:
                payload["attendees"] = [{"email": email} for email in attendees]

            resp = requests.post(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events?conferenceDataVersion=1",
                headers={
                    "Authorization": f"Bearer {active_token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=8
            )

            if resp.status_code == 200:
                event_json = resp.json()
                event_url = event_json.get("htmlLink")
                meet_link = event_json.get("hangoutLink") or event_json.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri")
                logger.info(f"Successfully scheduled Google Calendar event! Event URL: {event_url}, Meet: {meet_link}")
            else:
                logger.warning(f"Google Calendar API returned status {resp.status_code}: {resp.text}")
        except Exception as err:
            logger.error(f"Failed to call Google Calendar API: {err}")

    if not event_url:
        event_url = "https://calendar.google.com/calendar/r/eventedit"
    if not meet_link:
        meet_link = "https://meet.google.com/new"

    return {
        "summary": summary,
        "calendar_event_url": event_url,
        "google_meet_link": meet_link,
        "start_time": start_time_iso,
        "end_time": end_time_iso
    }


def send_gmail_message(to_email: str, subject: str, body_text: str, user_email: str = "connected_user@google.com", access_token: str = None, refresh_token: str = None, user_key: str = None) -> dict:
    """
    Sends a real email using the user's connected Gmail account via the Gmail REST API.
    """
    logger.info(f"Sending Gmail message to '{to_email}' from {user_email}...")
    
    active_token = access_token
    if not active_token and refresh_token:
        active_token = get_fresh_access_token(refresh_token)

    sent_status = False

    if active_token:
        try:
            message = MIMEText(body_text)
            message["to"] = to_email
            message["subject"] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            resp = requests.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={
                    "Authorization": f"Bearer {active_token}",
                    "Content-Type": "application/json"
                },
                json={"raw": raw_message},
                timeout=8
            )

            if resp.status_code == 200:
                sent_status = True
                logger.info(f"Successfully sent Gmail message to {to_email}!")
            else:
                logger.warning(f"Gmail API returned status {resp.status_code}: {resp.text}")
        except Exception as err:
            logger.error(f"Failed to send Gmail message: {err}")

    return {
        "to_email": to_email,
        "subject": subject,
        "sent": sent_status,
        "sender": user_email if sent_status else "Not Authenticated"
    }
