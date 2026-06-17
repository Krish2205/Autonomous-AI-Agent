"""
JARVIS — Google Calendar Agent
Read, schedule, and manage calendar events.
"""

import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from backend.agents.base import BaseAgent
from backend.config import DATA_DIR, PROJECT_ROOT, llm
from backend.logger import get_logger

logger = get_logger("agents.calendar")

# Google Calendar Scope
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarAgent(BaseAgent):
    name = "calendar"
    description = "Read, schedule, create, list, delete, or manage calendar events on Google Calendar."

    def __init__(self):
        self.token_path = os.path.join(DATA_DIR, "token_calendar.json")
        self.creds_path = os.path.join(PROJECT_ROOT, "credentials.json")

    def _get_service(self):
        """Authenticate and return Google Calendar service."""
        creds = None
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                logger.warning(f"Failed to load token file: {e}. Re-authenticating...")

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing Google Calendar credentials...")
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}. Re-authenticating...")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.creds_path):
                    raise FileNotFoundError(
                        f"Missing credentials.json at {self.creds_path}. "
                        "Please place your Google OAuth credentials file in the JARVIS root folder."
                    )
                logger.info("Initiating Google OAuth local server flow...")
                flow = InstalledAppFlow.from_client_secrets_file(self.creds_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())
            logger.info("Saved fresh credentials to token_calendar.json")

        return build("calendar", "v3", credentials=creds)

    def list_events(self, max_results: int = 10) -> str:
        """List upcoming calendar events."""
        logger.info(f"Listing upcoming {max_results} calendar events...")
        try:
            service = self._get_service()
            now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])

            if not events:
                return "No upcoming events found in your calendar."

            result = ["📅 **Upcoming Calendar Events:**"]
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                # Format start time beautifully
                try:
                    dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
                    formatted_time = dt.strftime("%Y-%m-%d %I:%M %p")
                except Exception:
                    formatted_time = start
                
                summary = event.get("summary", "(No Title)")
                event_id = event.get("id")
                result.append(f"• **{summary}** at *{formatted_time}* (ID: `{event_id}`)")
            return "\n".join(result)

        except Exception as e:
            logger.error(f"Failed to list calendar events: {e}")
            return f"Error listing calendar events: {str(e)}"

    def create_event(self, summary: str, start_time: str, end_time: str, description: str = None, location: str = None) -> str:
        """Create a new event in Google Calendar."""
        logger.info(f"Creating event '{summary}' from {start_time} to {end_time}...")
        try:
            service = self._get_service()
            event = {
                "summary": summary,
                "location": location,
                "description": description,
                "start": {
                    "dateTime": start_time,
                    "timeZone": "Asia/Kolkata",  # Default local time zone
                },
                "end": {
                    "dateTime": end_time,
                    "timeZone": "Asia/Kolkata",
                },
            }

            event_result = service.events().insert(calendarId="primary", body=event).execute()
            html_link = event_result.get("htmlLink", "#")
            event_id = event_result.get("id")
            return f"✅ **Event Created Successfully!**\n\n* **Title**: {summary}\n* **Start**: {start_time}\n* **End**: {end_time}\n* **Link**: [View in Google Calendar]({html_link})\n* **ID**: `{event_id}`"

        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            return f"Error creating event: {str(e)}"

    def delete_event(self, event_id: str) -> str:
        """Delete an event from Google Calendar."""
        logger.info(f"Deleting event ID: {event_id}...")
        try:
            service = self._get_service()
            service.events().delete(calendarId="primary", eventId=event_id).execute()
            return f"✅ **Event `{event_id}` has been deleted.**"
        except Exception as e:
            logger.error(f"Failed to delete event {event_id}: {e}")
            return f"Error deleting event: {str(e)}"

    def run(self, query: str) -> str:
        """
        Main runner logic. Resolves intent to list, create, or delete calendar events.
        """
        logger.info(f"Processing calendar query: '{query[:80]}'")
        query_lower = query.lower()

        # Check for DELETE intent
        if any(word in query_lower for word in ["delete", "remove", "cancel"]) and any(word in query_lower for word in ["event", "appointment"]):
            # Extract Event ID (alphanumeric string)
            words = query.split()
            event_id = None
            for word in words:
                # Event IDs are usually alphanumeric and long
                if len(word) > 10 and any(char.isdigit() for char in word) and any(char.isalpha() for char in word):
                    event_id = word.strip("`'")
                    break
            if not event_id:
                return "Please specify the Event ID to delete. You can use 'list events' to find the ID."
            return self.delete_event(event_id)

        # Check for LIST intent
        if any(word in query_lower for word in ["list", "show", "upcoming", "get", "check"]):
            return self.list_events()

        # Fallback to CREATE intent using LLM parsing
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import JsonOutputParser
            from pydantic import BaseModel, Field

            class EventParams(BaseModel):
                summary: str = Field(description="Summary or title of the event")
                start_time: str = Field(description="Start time of the event in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)")
                end_time: str = Field(description="End time of the event in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)")
                description: str = Field(default=None, description="Optional description of the event")
                location: str = Field(default=None, description="Optional location of the event")

            parser = JsonOutputParser(pydantic_object=EventParams)
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p (local time)")

            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "Extract calendar event details from the user's query. "
                    "Determine correct dates relative to current time: {current_time}. "
                    "Ensure start_time and end_time are in ISO 8601 format. If no end time is specified, "
                    "make it exactly 1 hour after the start time.\n"
                    "Format output as a JSON object matching this schema:\n{format_instructions}",
                ),
                ("human", "{query}"),
            ]).partial(current_time=current_time, format_instructions=parser.get_format_instructions())

            chain = prompt | llm | parser
            params = chain.invoke({"query": query})

            return self.create_event(
                summary=params["summary"],
                start_time=params["start_time"],
                end_time=params["end_time"],
                description=params.get("description"),
                location=params.get("location"),
            )

        except Exception as e:
            logger.error(f"Calendar planning or execution failed: {e}")
            return f"Calendar error: {str(e)}"
