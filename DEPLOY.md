# Deploying to a hosting platform

## What caused your crash

```
ModuleNotFoundError: No module named 'pandas'
```

The platform cloned your repo and ran `python bot.py`, but never ran
`pip install -r requirements.txt` first. So pandas — and every other
dependency — was missing when the bot started.

The fix is to give the platform a **build step**. The `Dockerfile` in this
folder does exactly that: it installs `requirements.txt` and even verifies
the imports at build time, so a missing package fails the build with a clear
message instead of crash-looping at runtime.

---

## Two things every platform needs

1. **Build**: install dependencies → the `Dockerfile` handles this.
2. **Environment variable**: `TELEGRAM_BOT_TOKEN` → you set this in the
   platform dashboard, NOT in a `.env` file.

> There is no `.env` file in the cloud. `.env` is for local development and
> is deliberately gitignored. In production, the platform injects the token
> as an environment variable, and `config.py` reads it with `os.getenv`
> either way — so the same code works in both places.

---

## Railway

Railway auto-detects the `Dockerfile` and `railway.json`.

1. **New Project → Deploy from GitHub repo** → pick your repo.
2. Railway builds using the Dockerfile automatically.
3. Go to your service → **Variables** → **New Variable**:
   - `TELEGRAM_BOT_TOKEN` = your token from @BotFather
   - If using Google CSV: add `DATA_SOURCE=google_csv` and `GOOGLE_CSV_URL=...`
4. Railway redeploys. Check **Deployments → View Logs** — you should see
   "All dependencies present." then "FM bot starting (polling)...".

If Railway tries to use Nixpacks instead of the Dockerfile, the `Procfile`
(declaring a `worker` process) is the fallback and still works.

---

## Render

1. **New → Blueprint** → connect your repo. Render reads `render.yaml`
   and creates a **worker** service (correct for a polling bot — it has no
   web port).
2. When prompted, enter `TELEGRAM_BOT_TOKEN`.
3. Deploy. Watch the logs for the startup messages.

If you prefer not to use the Blueprint: **New → Background Worker**, connect
the repo, set **Runtime = Docker**, and add the env var manually.

> Do NOT create a "Web Service" for this bot. A web service expects an open
> HTTP port; the bot has none, so Render's health check would kill it.
> It must be a **Background Worker**.

---

## Fly.io

1. Install `flyctl`, then in the repo folder:
   ```
   fly launch --no-deploy
   ```
   Accept the existing `fly.toml` when asked. Change the `app` name if that
   name is taken.
2. Set the token as a secret:
   ```
   fly secrets set TELEGRAM_BOT_TOKEN=your-real-token
   ```
   (For Google CSV also: `fly secrets set GOOGLE_CSV_URL=... DATA_SOURCE=google_csv`)
3. Deploy:
   ```
   fly deploy
   ```
4. Watch logs:
   ```
   fly logs
   ```

---

## Verifying it worked

In the platform's log viewer you should see, in order:

```
All dependencies present.
... apscheduler ... Adding job tentatively ...
... FM bot starting (polling)...
... Bot commands registered with Telegram.
```

Then message your bot `/start` on Telegram. If it replies, you're live.

---

## The data-source question in the cloud

A container has no OneDrive and no office network drive. Pick one:

- **Google Form → published CSV** (recommended for cloud): set
  `DATA_SOURCE=google_csv` and `GOOGLE_CSV_URL` as env vars. No file needed
  in the container at all. See `GOOGLE_FORM_SETUP.md`.
- **Ship a starter Excel file**: remove `data/` from `.dockerignore` so the
  workbook is copied into the image. Note the container filesystem is
  ephemeral — changes made inside it are lost on redeploy, so this only
  suits read-only/testing use.

For a cloud deploy, the Google CSV route is almost always the right one
because it needs no persistent storage.

---

## Common follow-on errors

| Log message | Cause | Fix |
|---|---|---|
| `TELEGRAM_BOT_TOKEN is empty or missing` | Env var not set on the platform | Add it in the dashboard (see above) |
| `terminated by other getUpdates request` | Two instances polling the same token | You have the bot running twice (e.g. locally AND deployed). Stop one. |
| `Cannot reach the maintenance spreadsheet` | No data source configured in cloud | Set `DATA_SOURCE=google_csv` + `GOOGLE_CSV_URL` |
| Build fails at the import check | A dependency name/version is wrong | Read the build log — it names the missing package |
| Still `ModuleNotFoundError` | Platform ignored the Dockerfile | Ensure the Dockerfile is in the repo ROOT and committed |
