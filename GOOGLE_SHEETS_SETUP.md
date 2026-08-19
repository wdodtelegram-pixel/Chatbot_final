# Setting up Google Sheets as the data source

This replaces the OneDrive Excel file with a Google Sheet.
The FM Officer edits the sheet in a browser; the bot downloads
it automatically before each command.

---

## Part 1 — Google Cloud setup (one-time, ~15 minutes)

### Step 1: Create a Google Cloud project

1. Go to https://console.cloud.google.com
2. Click the project dropdown at the top → **New Project**
3. Name it anything, e.g. "FM Chatbot"
4. Click **Create** and wait ~30 seconds

### Step 2: Enable the APIs

1. In the left menu → **APIs & Services** → **Library**
2. Search for **Google Sheets API** → click it → **Enable**
3. Go back to Library, search for **Google Drive API** → **Enable**

Both must be enabled. The Drive API is needed to export the sheet as
Excel format.

### Step 3: Create a Service Account

A service account is a non-human Google identity the bot uses to
read the sheet. It has its own email address.

1. Left menu → **APIs & Services** → **Credentials**
2. **Create Credentials** → **Service Account**
3. Fill in:
   - Service account name: `fm-bot-reader` (or anything)
   - Service account ID: auto-filled, note it down
   - Description: optional
4. Click **Create and Continue**
5. Skip the optional role and user access steps → **Done**

### Step 4: Download the JSON key

1. On the Credentials page, click the service account you just created
2. **Keys** tab → **Add Key** → **Create new key** → **JSON** → **Create**
3. A `.json` file downloads automatically
4. **Rename it to `service_account.json`**
5. **Move it into your `fm_telegram_bot` folder**, next to `bot.py`

> ⚠️  Keep this file private. Anyone who has it can read your sheet.
> It is already in `.gitignore` — never commit it.

---

## Part 2 — Create the Google Sheet

### Step 5: Create the sheet

1. Go to https://sheets.google.com → **Blank spreadsheet**
2. Rename it (click "Untitled spreadsheet" at the top): **FM Maintenance Jobs**
3. Rename the first tab (bottom left): **Jobs**

### Step 6: Add the column headers

Click cell A1 and type these headers across row 1, one per cell:

```
Job ID | Category | Job Description | Location | Maintenance Type | Status | Estimated Completion | Next Job Date
```

Exact spelling matters — these must match `config.py` exactly.

You can copy the sample data from `data/maintenance_jobs.xlsx` into
the sheet if you want a starting point. In Excel: select all → copy.
In Google Sheets: paste. The data comes across cleanly.

### Step 7: Add dropdown validation (recommended)

For the Status column (column F):
1. Select F2:F500
2. **Data** → **Data validation** → **Add rule**
3. Criteria: **Dropdown** → type the three options:
   - `Yet to Start`
   - `In Progress`
   - `Completed`
4. Under "If the data is invalid": **Show a warning**
5. Save

Repeat for Maintenance Type (column E): `Preventive`, `Corrective`

Repeat for Category (column B): `ACMV`, `Lift & Escalator`,
`Electrical`, `Fire Protection`, `Plumbing & Sanitary`

### Step 8: Share the sheet with the service account

1. Click **Share** (top right of the sheet)
2. Paste the service account email — it looks like:
   ```
   fm-bot-reader@fm-chatbot-123456.iam.gserviceaccount.com
   ```
   Find it in the JSON file under `"client_email"`, or on the
   GCP Credentials page.
3. Permission: **Viewer** (the bot only reads; writing goes through
   `/update` if you enable `updater.py`)
4. Untick "Notify people" → **Share**

### Step 9: Copy the Sheet ID

The Sheet ID is in the URL when you have the sheet open:

```
https://docs.google.com/spreadsheets/d/ THIS_IS_THE_ID /edit
```

Copy everything between `/d/` and `/edit`.

---

## Part 3 — Configure the bot

### Step 10: Update .env

Add this one line to your `.env` file:

```
GOOGLE_SHEET_ID=paste-your-sheet-id-here
```

Leave `EXCEL_PATH=` blank (the bot will use `data/maintenance_jobs.xlsx`
as the local cache file, overwriting it each sync).

### Step 11: Install the Google client library

```powershell
pip install google-auth google-auth-httplib2 google-api-python-client
```

### Step 12: Wire it into excel_loader.py

Open `excel_loader.py`. Find this section inside `load_jobs()`:

```python
if config.ONEDRIVE_SHARE_LINK:
    _download_from_onedrive(path)
```

Replace it with:

```python
from google_sheets_loader import download_sheet
download_sheet(path)
```

That is the only code change needed. Every other file stays the same.

---

## Part 4 — Verify

### Step 13: Run the setup checker

```powershell
python check_setup.py
```

If the sheet ID and service account are correct, the checker will
download the sheet and show the row count. If it fails, the error
message tells you which step to revisit.

### Step 14: Test offline

```powershell
python test_offline.py
```

The messages should show the data from your Google Sheet.

### Step 15: Run the bot

```powershell
python bot.py
```

---

## How updates work

**FM Officer edits the sheet** → saves (auto-save in Google Sheets) →
**bot downloads the latest version** on the next command or within
5 minutes (the background refresh job).

There is no desktop client to install. The sync is pull-based: the bot
asks Google "give me the latest version" and Google returns it.

If you also enable `updater.py`, the bot writes changes to the local
Excel cache file. Those changes do NOT propagate back to Google Sheets
automatically — the Google Sheet remains the master copy and overwrites
the cache on the next sync. To avoid this conflict, either:

- Use `/update` only for changes you will also make in the sheet, or
- Disable the background sync when using `/update` heavily

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `service_account.json not found` | File in wrong folder | Move it next to `bot.py` |
| `HttpError 403 forbidden` | Sheet not shared with service account | Step 8 |
| `HttpError 404 not found` | Wrong Sheet ID | Re-copy from URL |
| `google.auth not found` | Library not installed | Step 11 |
| Bot shows old data | Sheet not auto-saved | Google Sheets auto-saves; wait 2s and retry |
| `/update` changes disappear | Google Sheet overwrites cache | Expected behaviour — edit in the sheet too |
