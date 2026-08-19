"""
graph_loader.py  (OPTIONAL — replaces the OneDrive share link fallback)
=======================================================================
PURPOSE
    Downloads maintenance_jobs.xlsx directly from OneDrive/SharePoint
    using the Microsoft Graph API. No OneDrive desktop client needed.

SETUP (one-time, 5 minutes)
    1. Go to https://portal.azure.com -> "App registrations" -> New
    2. Name it anything, choose "Accounts in this org only"
    3. After creation: Certificates & secrets -> New client secret -> copy it
    4. API permissions -> Add -> Microsoft Graph -> Application ->
       Files.Read.All -> Grant admin consent
    5. Copy the Application (client) ID and Directory (tenant) ID from Overview

    Add these five lines to your .env:
        GRAPH_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        GRAPH_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        GRAPH_CLIENT_SECRET=your-secret-value
        GRAPH_USER_EMAIL=fmofficer@yourcompany.com
        GRAPH_FILE_PATH=FM/maintenance_jobs.xlsx

    Then in excel_loader.py, replace the _download_from_onedrive() call
    with graph_loader.download_if_changed().
"""

from __future__ import annotations
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Read config from .env (already loaded by config.py before this runs)
TENANT_ID     = os.getenv("GRAPH_TENANT_ID", "")
CLIENT_ID     = os.getenv("GRAPH_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GRAPH_CLIENT_SECRET", "")
USER_EMAIL    = os.getenv("GRAPH_USER_EMAIL", "")   # whose OneDrive holds the file
FILE_PATH     = os.getenv("GRAPH_FILE_PATH", "")    # path inside that OneDrive

_token_cache: dict = {}


def _get_access_token() -> str:
    """
    PURPOSE: get a bearer token from Azure AD using client-credentials flow.

    Tokens are valid for 3600 seconds. We cache the token and only request
    a new one when the old one is about to expire, to avoid hammering the
    auth endpoint on every bot command.
    """
    import requests

    now = time.time()
    if _token_cache.get("expires_at", 0) > now + 60:
        return _token_cache["access_token"]

    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    resp = requests.post(url, data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    }, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    return _token_cache["access_token"]


def download_if_changed(destination: Path) -> bool:
    """
    PURPOSE: download the workbook only if it changed since last time.

    Uses the ETag header: on first call we download unconditionally and save
    the ETag. On subsequent calls we send If-None-Match; if the server replies
    304 Not Modified, we skip the download and return False. This keeps network
    usage minimal even when the bot polls every 5 minutes.

    Returns True if the file was updated, False if it was unchanged or failed.
    """
    import requests

    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET, USER_EMAIL, FILE_PATH]):
        return False

    etag_file = destination.parent / ".graph_etag"
    etag = etag_file.read_text().strip() if etag_file.exists() else None

    try:
        token = _get_access_token()
        # Graph URL to download a file from a specific user's OneDrive by path.
        url = (
            f"https://graph.microsoft.com/v1.0"
            f"/users/{USER_EMAIL}/drive/root:/{FILE_PATH}:/content"
        )
        headers = {"Authorization": f"Bearer {token}"}
        if etag:
            headers["If-None-Match"] = etag

        resp = requests.get(url, headers=headers, timeout=30)

        if resp.status_code == 304:
            logger.debug("Graph: workbook unchanged (304).")
            return False

        resp.raise_for_status()

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(resp.content)

        if new_etag := resp.headers.get("ETag"):
            etag_file.write_text(new_etag)

        logger.info("Graph: workbook downloaded (%d bytes).", len(resp.content))
        return True

    except Exception as exc:
        logger.warning("Graph download failed: %s", exc)
        return False
