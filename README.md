# Chatbot_final
wdod fm chatbot

# Facilities Management Telegram Bot

A real-time service enquiry bot. Staff check maintenance job status from Telegram; the FM Officer updates a single Excel Online workbook and every user sees the change within seconds.

## How the files fit together

| File | Purpose |
|---|---|
| `config.py` | All settings: token, file paths, column names, the category list. **The only file you normally edit.** |
| `date_utils.py` | Converts any date cell into `Week 1 January 2026` format. |
| `excel_loader.py` | Reads the workbook into pandas, caches it, re-reads when the file changes. |
| `formatters.py` | Builds every message the user sees. |
| `bot.py` | Telegram command handlers. Run this to start the bot. |
| `create_workbook.py` | Generates the starter `maintenance_jobs.xlsx`. Run once. |
| `test_offline.py` | Prints every message in a terminal without needing a token. |

The layering matters: `bot.py` never touches pandas, and `excel_loader.py` never touches Telegram. You can change either side without breaking the other.

## Setup

**1. Install**

```bash
pip install -r requirements.txt
```

**2. Get a bot token**

Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` → follow the prompts → copy the token.

**3. Configure**

```bash
cp .env.example .env
```

Edit `.env` and paste your token into `TELEGRAM_BOT_TOKEN`.

**4. Create the workbook**

```bash
python create_workbook.py
```

This writes `data/maintenance_jobs.xlsx` with sample rows and dropdown validation.

**5. Test without Telegram**

```bash
python test_offline.py
```

Proofread the output. Fix any wording in `formatters.py` before going live.

**6. Run**

```bash
python bot.py
```

Open Telegram, find your bot, send `/start`.

## Connecting to OneDrive

The bot reads a **local** file. OneDrive's desktop client keeps that local file in sync with Excel Online — the bot needs no Microsoft credentials at all.

1. Upload `data/maintenance_jobs.xlsx` to your OneDrive folder.
2. Make sure the OneDrive desktop app is installed and signed in on the machine running the bot.
3. Set the file to **"Always keep on this device"** (right-click → Always keep on this device). Without this, OneDrive may leave it as a cloud-only placeholder and pandas will fail to read it.
4. Put the full local path in `.env` as `EXCEL_PATH`.

The FM Officer now edits in Excel Online. OneDrive syncs down, the file's modification time changes, and the next Telegram command reads fresh data.

**No OneDrive desktop client?** (e.g. a cloud VM) Create a "anyone with the link can view" share link and put it in `ONEDRIVE_SHARE_LINK` instead. The loader downloads the file over HTTP before each read.

## Commands

| Command | Result |
|---|---|
| `/start`, `/help` | Welcome menu |
| `/service` | Dashboard: status counts for all categories |
| `/acmv` | ACMV jobs in full detail |
| `/lift` | Lift and escalator jobs |
| `/electrical` | Electrical jobs |
| `/fire` | Fire protection jobs |
| `/plumbing` | Plumbing and sanitary jobs |
| `/pending` | Every job across all categories not yet completed |
| `/refresh` | Force an immediate re-read of the spreadsheet |

Inline buttons under each message do the same thing with one tap.

## Adding a sixth category

Your brief says "6 main jobs" but lists five. To add the sixth, add one entry to `CATEGORIES` in `config.py`:

```python
"pest": {
    "name": "Pest Control",
    "excel": "Pest Control",
    "blurb": "Pest control services",
    "emoji": "🐜",
},
```

That single edit creates the `/pest` command, adds it to the `/start` menu, adds a button, adds it to the dashboard, and registers it in Telegram's command dropdown. Then re-run `create_workbook.py` so the Category dropdown includes it — or add the value manually in Excel's Data Validation settings.

## Spreadsheet rules

- Only edit the **Jobs** sheet. Do not rename it or any column header.
- Use the dropdowns for Category, Maintenance Type and Status.
- Dates: type `Week 1 January 2026`. A real Excel date also works — the bot converts it.
- Use `-` in Next Job Date for one-off corrective jobs.
- Never leave a blank row in the middle of the data.

The bot tolerates messy input where it can — it strips stray spaces and accepts `ongoing`/`done` as `In Progress`/`Completed` — but the dropdowns prevent the problem entirely.

## Keeping it running

`python bot.py` stops when you close the terminal. For production:

- **Windows**: Task Scheduler, "Run whether user is logged on or not"
- **Linux**: a `systemd` service with `Restart=always`
- **Either**: `nssm` or `pm2` as a lightweight service wrapper

## Troubleshooting

| Symptom | Cause |
|---|---|
| `TELEGRAM_BOT_TOKEN is not set` | No `.env` file, or it sits in a different folder than `bot.py`. |
| "Cannot reach the maintenance spreadsheet" | Wrong `EXCEL_PATH`, or OneDrive left the file as a cloud-only placeholder. |
| Bot shows stale data | The officer edited but did not save, or OneDrive has not finished syncing. Send `/refresh`. |
| A category shows no jobs | The `excel` value in `config.CATEGORIES` does not match the Category column text exactly. |
| Bot ignores everything | Another copy is already running. Telegram allows only one poller per token — kill the other process. |
