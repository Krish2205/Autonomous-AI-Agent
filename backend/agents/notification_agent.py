"""
JARVIS — Notification Agent
Sends push notifications, alerts, and integrates with Slack webhooks.
"""

import requests
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from backend.agents.base import BaseAgent
from backend.config import llm, SLACK_WEBHOOK_URL
from backend.core.notifications import notification_manager
from backend.logger import get_logger

logger = get_logger("agents.notification")


class AlertDetails(BaseModel):
    title: str = Field(description="Short, descriptive title of the alert or notification (e.g. 'Build Success')")
    message: str = Field(description="Detailed alert message or notification description")
    level: str = Field(
        default="info",
        description="Priority/urgency level of the notification. Must be 'info', 'success', 'warning', or 'error'."
    )
    send_to_slack: bool = Field(
        default=True,
        description="Whether this alert warrants posting to the configured Slack webhook channel."
    )


class NotificationAgent(BaseAgent):
    name = "notification"
    description = (
        "Send push notifications, alerts, or status updates. Displays immediate in-app notifications "
        "and posts updates to Slack if requested. Ideal for notifying the user when tasks finish, "
        "errors occur, or thresholds are crossed."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running Notification Agent with query: {query[:80]}...")

        # Step 1: Parse alert parameters using LLM
        parser = JsonOutputParser(pydantic_object=AlertDetails)

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are JARVIS's central notification and alert controller. "
                "Deconstruct the user's notification request. Standardize the alert level, "
                "extract the title, summarize the message, and determine if it should post to Slack. "
                "Format the output as a JSON matching this schema:\n{format_instructions}",
            ),
            ("human", "{query}"),
        ]).partial(format_instructions=parser.get_format_instructions())

        try:
            chain = prompt | llm | parser
            details = chain.invoke({"query": query})
        except Exception as e:
            logger.error(f"Failed to parse alert details: {e}")
            return f"Error: Failed to parse notification inputs. Details: {str(e)}"

        title = details.get("title", "JARVIS Alert")
        message = details.get("message", query)
        level = details.get("level", "info").lower()
        send_to_slack = details.get("send_to_slack", True)

        # Standardize level
        if level not in {"info", "success", "warning", "error"}:
            level = "info"

        logger.info(f"Notification details: Title='{title}', Level='{level}', Slack={send_to_slack}")

        # Step 2: Trigger In-App Notification (broadcast via SSE)
        notification_payload = {
            "title": title,
            "message": message,
            "level": level,
        }
        
        try:
            notification_manager.broadcast(notification_payload)
            in_app_status = "✓ Triggered in-app toast notification."
        except Exception as e:
            logger.error(f"Failed to broadcast local alert: {e}")
            in_app_status = f"✕ Failed to trigger in-app alert locally: {e}"

        # Look up Slack integration
        from backend.config import get_user_integration
        slack_integ = get_user_integration("slack_teams")
        
        webhook_url = SLACK_WEBHOOK_URL
        slack_account = None
        if slack_integ.get("connected"):
            slack_account = slack_integ.get("account")
            if slack_integ.get("api_key"):
                webhook_url = slack_integ.get("api_key")

        # Step 3: Trigger Slack Notification (via Webhook)
        slack_status = "Not requested."
        if send_to_slack:
            if not webhook_url or "YOUR/WEBHOOK/URL" in webhook_url:
                slack_status = (
                    "✕ Slack webhook URL is not configured. "
                    "To enable, connect Slack & Microsoft Teams under Integrations or set `SLACK_WEBHOOK_URL` in your `.env` file."
                )
                logger.warning("Slack webhook URL not configured.")
            else:
                try:
                    # Construct Slack block message payload
                    slack_emoji = {
                        "success": "✅",
                        "warning": "⚠️",
                        "error": "🚨",
                        "info": "ℹ️"
                    }.get(level, "🔔")

                    slack_payload = {
                        "text": f"{slack_emoji} *{title}*\n{message}"
                    }
                    response = requests.post(webhook_url, json=slack_payload, timeout=10)
                    if response.status_code == 200:
                        account_info = f" (Workspace account: `{slack_account}`)" if slack_account else ""
                        slack_status = f"✓ Posted notification to connected Slack channel{account_info}."
                        logger.info("Successfully posted to Slack webhook.")
                    else:
                        slack_status = f"✕ Slack API returned status code {response.status_code}: {response.text}"
                        logger.error(f"Slack post failed: {response.text}")
                except Exception as e:
                    slack_status = f"✕ Failed to post to Slack: {str(e)}"
                    logger.error(f"Slack post failed with exception: {e}")

        # Compile final response report
        level_emojis = {
            "success": "🟢 SUCCESS",
            "warning": "🟡 WARNING",
            "error": "🔴 ERROR",
            "info": "🔵 INFO"
        }
        
        report = (
            f"🔔 **Notification Dispatched!**\n\n"
            f"* **Title**: {title}\n"
            f"* **Severity**: {level_emojis.get(level, level.upper())}\n"
            f"* **Message**: {message}\n\n"
            f"**Delivery Channels:**\n"
            f"- In-App Alerts: {in_app_status}\n"
            f"- Slack Webhook: {slack_status}"
        )
        return report
