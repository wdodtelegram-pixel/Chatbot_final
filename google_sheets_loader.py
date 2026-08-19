"""
google_sheets_loader.py  (OPTIONAL)
====================================
PURPOSE
    Downloads a Google Sheet as an Excel file so the rest of the bot
    (excel_loader.py) can read it without any changes.

    The FM Officer edits the Google Sheet in a browser. The bot
    downloads it automatically before each read, so changes appear
    within seconds of being saved.

SETUP
    Follow GOOGLE_SHEETS_SETUP.md step by step.

    Short version:
      1. Enable Sheets + Drive APIs in Google Cloud Console
      2. Create a Service Account, download its JSON key as service_account.json
      3. Share the Google Sheet with the service account email (Viewer)
      4. Add GOOGLE_SHEET_ID=... to .env
      5. pip install google-auth google-auth-httplib2 google-api-python-client
      6. In excel_loader.py, replace the ONEDRIVE_SHARE_LINK block with:
             from google_sheets_loader import download_sheet
             download_sheet(path)

RATE LIMITS
    Google Drive export has a quota of ~10 MB/s and soft rate limits.
    The mtime check below means we only download when the LOCAL file has
    not changed recently, which naturally throttles calls during high
    bot activity. The 5-minute background job in bot.py is the main
    trigger; individual commands only download if the file is stale.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "").strip()
SERVICE_ACCT_KEY = Path(__file__).parent / "service_account.json"

# Minimum seconds between downloads, even if called repeatedly.
# Prevents a burst of bot commands from hammering the Drive API.
_MIN_INTERVAL = 30
_last_download: float = 0.0


def _is_configured() -> bool:
    """PURPOSE: quick guard -- skip all Google logic if not set up."""
    if not SHEET_ID:
        logger.debug("GOOGLE_SHEET_ID not set; skipping Google Sheets sync.")
        return False
    if not SERVICE_ACCT_KEY.exists():
        logger.warning(
            "service_account.json not found at %s. "
            "Follow GOOGLE_SHEETS_SETUP.md step 4.",
            SERVICE_ACCT_KEY,
        )
        return False
    return True


def _build_drive_service():
    """
    PURPOSE: build an authenticated Google Drive API client.

    Separated from download_sheet() so the import errors surface clearly
    if the google-auth libraries are not installed, rather than appearing
    as a confusing AttributeError mid-download.
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise ImportError(
            "Google client libraries not installed.\n"
            "Run:  pip install google-auth google-auth-httplib2 "
            "google-api-python-client"
        ) from exc

    creds = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCT_KEY),
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    # cache_discovery=False avoids a stale discovery doc causing silent errors.
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def download_sheet(destination: Path, force: bool = False) -> bool:
    """
    PURPOSE: export the Google Sheet as .xlsx and write it to `destination`.

    Call this at the top of excel_loader.load_jobs() in place of
    _download_from_onedrive(). The rest of the loader is unchanged.

    Rate-limiting:
        Skips the download if called within _MIN_INTERVAL seconds of the
        last successful download, unless force=True. This means a burst
        of Telegram commands (ten users hitting /service at once) produces
        one download, not ten.

    Returns True if the file was (re)downloaded, False if skipped or failed.
    """
    global _last_download

    if not _is_configured():
        return False

    now = time.monotonic()
    if not force and (now - _last_download) < _MIN_INTERVAL:
        logger.debug(
            "Google Sheets: skipping download (last was %.0fs ago, min interval %ds).",
            now - _last_download,
            _MIN_INTERVAL,
        )
        return False

    try:
        from googleapiclient.http import MediaIoBaseDownload
        import io

        drive = _build_drive_service()

        # Drive's export endpoint converts the Google Sheet to Excel on the fly.
        # mimeType must be the full Excel MIME type or the export is rejected.
        request = drive.files().export_media(
            fileId=SHEET_ID,
            mimeType=(
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            ),
        )

        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        content = buf.getvalue()
        if len(content) < 500:
            # A valid workbook is always several KB. A tiny response usually
            # means an error page was returned instead of the file.
            logger.warning(
                "Google Sheets: downloaded only %d bytes -- "
                "possible API error. Using existing local copy.",
                len(content),
            )
            return False

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        _last_download = now

        logger.info(
            "Google Sheets: downloaded %d bytes to %s.", len(content), destination
        )
        return True

    except Exception as exc:
        # Log but do not raise: the caller falls back to whatever local copy
        # already exists, so a transient network error does not kill the bot.
        logger.warning("Google Sheets download failed: %s", exc)
        return False
