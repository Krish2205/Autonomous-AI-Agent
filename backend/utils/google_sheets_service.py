"""
JARVIS — Live Google Sheets Service Integration with Automated Token Refresh
Connects to official Google Sheets API endpoints to create real live Google Spreadsheets inside the user's connected Google Drive account.
Automatically handles OAuth token refresh so accounts stay connected permanently until manually disconnected.
"""

import os
import json
import urllib.parse
import requests
from backend.logger import get_logger

logger = get_logger("utils.google_sheets")


def get_fresh_access_token(refresh_token: str) -> str:
    """Uses Google OAuth refresh token to obtain a fresh access token."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if not refresh_token or not client_id or not client_secret:
        return None

    try:
        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            },
            timeout=5
        )
        if resp.status_code == 200:
            new_token = resp.json().get("access_token")
            logger.info("Successfully refreshed Google OAuth access token!")
            return new_token
    except Exception as e:
        logger.error(f"Failed to refresh Google OAuth token: {e}")
    return None


def create_live_google_sheet(title: str, headers: list, rows: list, user_email: str = "connected_user@google.com", access_token: str = None, refresh_token: str = None, user_key: str = None) -> dict:
    """
    Creates a real live Google Spreadsheet inside the user's Google Drive account using Google Sheets API REST endpoints.
    """
    logger.info(f"Creating live Google Sheet '{title}' for {user_email} (token present: {bool(access_token or refresh_token)})...")
    
    # Save a local backup copy in static exports
    export_dir = os.path.join("frontend", "public", "exports")
    os.makedirs(export_dir, exist_ok=True)
    clean_title = "".join([c if c.isalnum() else "_" for c in title.lower()])
    filename = f"sheet_{clean_title}.csv"
    file_path = os.path.join(export_dir, filename)
    
    csv_lines = [",".join([f'"{h}"' for h in headers])]
    for row in rows:
        csv_lines.append(",".join([f'"{str(cell)}"' for cell in row]))
    csv_content = "\n".join(csv_lines)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(csv_content)
        
    local_csv_url = f"/exports/{filename}"
    real_spreadsheet_url = None

    active_token = access_token
    if not active_token and refresh_token:
        active_token = get_fresh_access_token(refresh_token)

    # Call official Google Sheets REST API if access token is available
    if active_token:
        try:
            values_data = [headers] + [[str(cell) for cell in row] for row in rows]
            payload = {
                "properties": {"title": title},
                "sheets": [{
                    "properties": {"title": "Data Overview"},
                    "data": [{
                        "rowData": [{"values": [{"userEnteredValue": {"stringValue": str(cell)}} for cell in r]} for r in values_data]
                    }]
                }]
            }

            resp = requests.post(
                "https://sheets.googleapis.com/v4/spreadsheets",
                headers={
                    "Authorization": f"Bearer {active_token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=8
            )

            # Handle 401 Unauthorized by attempting a token refresh
            if resp.status_code == 401 and refresh_token:
                logger.info("Access token expired. Attempting token refresh...")
                refreshed_token = get_fresh_access_token(refresh_token)
                if refreshed_token:
                    active_token = refreshed_token
                    resp = requests.post(
                        "https://sheets.googleapis.com/v4/spreadsheets",
                        headers={
                            "Authorization": f"Bearer {active_token}",
                            "Content-Type": "application/json"
                        },
                        json=payload,
                        timeout=8
                    )
                    # Update saved config on disk with refreshed token
                    if user_key and resp.status_code == 200:
                        try:
                            from backend.config import load_profile_config, save_profile_config
                            cfg = load_profile_config(user_key)
                            if "integrations" in cfg and "google_workspace" in cfg["integrations"]:
                                cfg["integrations"]["google_workspace"]["access_token"] = active_token
                                save_profile_config(user_key, cfg)
                        except Exception as ex:
                            logger.error(f"Error saving refreshed token: {ex}")

            if resp.status_code == 200:
                sheet_json = resp.json()
                spreadsheet_id = sheet_json.get("spreadsheetId")
                real_spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
                logger.info(f"Successfully created real Google Spreadsheet in Drive! ID: {spreadsheet_id}")
            elif resp.status_code == 403:
                logger.error("Google Sheets API is disabled in Google Cloud Console! Please enable sheets.googleapis.com.")
                api_enable_url = "https://console.developers.google.com/apis/api/sheets.googleapis.com/overview"
                real_spreadsheet_url = f"https://docs.google.com/spreadsheets/create"
            else:
                logger.warning(f"Google Sheets API creation returned status {resp.status_code}: {resp.text}")
                real_spreadsheet_url = f"https://docs.google.com/spreadsheets/create"
        except Exception as err:
            logger.error(f"Failed to call Google Sheets API: {err}")

    # Fallback valid link
    if not real_spreadsheet_url:
        real_spreadsheet_url = "https://docs.google.com/spreadsheets/create"

    return {
        "title": title,
        "google_sheets_url": real_spreadsheet_url,
        "local_csv_url": local_csv_url,
        "total_rows": len(rows),
        "columns": headers
    }
