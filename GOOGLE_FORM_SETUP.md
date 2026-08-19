# Option C — Google Form → Published CSV (no Google Cloud)

The FM Officer fills a Google Form on their phone or browser. Responses
land in a Google Sheet, which is "published to web" as a plain CSV link.
The bot downloads that link over normal HTTP. **No Google Cloud project,
no service account, no credentials file.**

```
FM Officer fills Google Form
        ↓
Responses auto-append to a Google Sheet
        ↓
Sheet "Published to web" as CSV   ← one toggle, no Google Cloud
        ↓
Bot fetches the public CSV URL over HTTP
        ↓
Newest submission per Job ID wins → same messages as before
```

---

## Important: how "updating" works with a Form

A Google Form **only ever adds rows** — it cannot edit an old one. So to
change a job's status, the FM Officer **submits the form again with the
same Job ID**. The bot automatically keeps only the newest submission for
each Job ID and ignores the older ones.

Example:
- Morning: submit `ACMV-001`, status `In Progress`
- Afternoon: submit `ACMV-001` again, status `Completed`
- The bot shows `ACMV-001` as `Completed` (newest wins)

This behaviour is controlled by `DEDUPE_BY_JOB_ID=true` in `.env`
(the default).

---

## Part 1 — Build the Google Form

### Step 1: Create the form

1. Go to https://forms.google.com → **Blank form**
2. Name it "FM Maintenance Update"

### Step 2: Add these questions IN THIS ORDER

The question titles must match the bot's column names **exactly**.
Set each to the type shown, and mark all as **Required** (click the
toggle at the bottom-right of each question).

| # | Question title (type exactly) | Type | Notes |
|---|---|---|---|
| 1 | `Job ID` | Short answer | e.g. ACMV-001 |
| 2 | `Category` | Dropdown | Add the 5 category options below |
| 3 | `Job Description` | Short answer | |
| 4 | `Location` | Short answer | |
| 5 | `Maintenance Type` | Dropdown | Options: Preventive, Corrective |
| 6 | `Status` | Dropdown | Options: Yet to Start, In Progress, Completed |
| 7 | `Estimated Completion` | Short answer | Type: `Week 1 January 2026` |
| 8 | `Next Job Date` | Short answer | Or `-` for one-off jobs |

For the **Category** dropdown (question 2), add exactly these 5 options:
```
ACMV
Lift & Escalator
Electrical
Fire Protection
Plumbing & Sanitary
```

> These must match `config.CATEGORIES[...]['excel']` exactly, including the
> `&` and spacing. If you changed the categories in `config.py`, use those.

### Step 3: Link the form to a sheet

1. In the form, click the **Responses** tab
2. Click the green Sheets icon (**Link to Sheets**)
3. Choose **Create a new spreadsheet** → **Create**

A new Google Sheet opens. It has a **Timestamp** column plus your 8
questions as columns. Every form submission adds a row here.

---

## Part 2 — Publish the sheet as CSV

### Step 4: Publish to web

1. In the linked Google Sheet: **File** → **Share** → **Publish to web**
2. In the dialog:
   - First dropdown (which content): select the **Form Responses 1** tab
     (NOT "Entire Document")
   - Second dropdown (format): select **Comma-separated values (.csv)**
3. Click **Publish** → confirm **OK**
4. Copy the URL it shows. It looks like:
   ```
   https://docs.google.com/spreadsheets/d/e/2PACX-.../pub?gid=0&single=true&output=csv
   ```

> ⚠️  Anyone with this link can read the response data. For maintenance
> schedules this is normally fine, but do not put confidential information
> in the form if that matters to you.

### Step 5: Test the link

Paste the URL into a browser. It should download or display raw CSV text.
If you see a web page instead, redo Step 4 and make sure format is CSV.

---

## Part 3 — Point the bot at the CSV

### Step 6: Edit .env

Add these lines to your `.env` file (create it from `.env.example` if needed):

```
TELEGRAM_BOT_TOKEN=your-real-token
DATA_SOURCE=google_csv
GOOGLE_CSV_URL=https://docs.google.com/spreadsheets/d/e/2PACX-.../pub?gid=0&single=true&output=csv
```

That is the **only** configuration change. You do not touch `EXCEL_PATH`,
and you do not need `create_workbook.py` or any Excel file at all in this mode.

Optional extra settings (defaults shown — only add if you want to change them):

```
DEDUPE_BY_JOB_ID=true          # newest submission per Job ID wins
FORM_TIMESTAMP_DAYFIRST=true   # SG/UK date format in the Timestamp column
FORM_TIMESTAMP_COLUMN=Timestamp
```

### Step 7: Verify

```
python check_setup.py
```

You should see:
```
[ -- ]  Data source: google_csv
[ OK ]  GOOGLE_CSV_URL is set
[ OK ]  CSV URL looks correct
[ OK ]  Data loads and parses    N responses loaded
[ OK ]  All required columns present
```

If "All required columns present" fails, a form question title does not
match a column name exactly — recheck Step 2.

### Step 8: Run

```
python bot.py
```

Submit a test response through the form, wait a few seconds, then send
`/service` or `/acmv` in Telegram. Send `/refresh` to force an immediate
re-fetch if you don't want to wait for the 5-minute auto-refresh.

---

## What changed in the code (summary)

You do **not** need to edit any Python. Everything is driven by `.env`.
For reference, the changes that make this work are:

- **config.py** — added `DATA_SOURCE`, `GOOGLE_CSV_URL`, and the dedupe
  settings.
- **excel_loader.py** — `load_jobs()` now branches: `google_csv` fetches
  the CSV over HTTP, dedupes to newest-per-Job-ID, then runs the same
  cleaning as Excel. Every other function calls `load_jobs()`, so the whole
  bot follows automatically.
- **check_setup.py** — validates the CSV URL when in `google_csv` mode.

`bot.py`, `formatters.py`, and `date_utils.py` are unchanged.

---

## Switching back to Excel

Set `DATA_SOURCE=excel` (or remove the line) in `.env`. The bot reads the
local workbook again. Nothing else to undo.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "returned a web page, not CSV" | Publish format wasn't CSV | Redo Step 4, pick CSV |
| "GOOGLE_CSV_URL is not set" | Missing from `.env` | Add the line from Step 6 |
| Columns missing | Form question titles don't match | Match them exactly (Step 2) |
| A job shows twice | `DEDUPE_BY_JOB_ID` off, or two different Job IDs | Check spelling of Job ID in submissions |
| Old status still showing | Bot hasn't re-fetched yet | Send `/refresh`, or wait 5 min |
| Wrong job shown as newest | Timestamp parsed wrong | Set `FORM_TIMESTAMP_DAYFIRST` to match your locale |
| Category shows no jobs | Dropdown option ≠ config category | Match `config.CATEGORIES[...]['excel']` exactly |

---

## Trade-offs vs the other options

| | Google Form + CSV | Excel + SFTP uploader |
|---|---|---|
| Google Cloud needed | No | No |
| Editing tool | Google Form (phone-friendly) | Excel |
| Updating a job | Resubmit form (adds row) | Edit cell, save |
| Bot runs anywhere | Yes (just HTTP) | Yes |
| Data privacy | Published link is public | Stays on your VPS |
| History kept | Yes — every submission is a row | No — overwrites |

The published-link visibility is the main thing to weigh. If the schedule
is not sensitive, this is the simplest zero-infrastructure option.
