# VPS Setup Guide

No OneDrive. The FM Officer edits a local Excel file; a small background
script on the office PC uploads it to your VPS whenever it is saved.

```
FM Officer saves Excel on office PC
           ↓  (uploader.py detects save, ~2 seconds)
SFTP upload to VPS
           ↓  (bot detects file change)
Telegram users see updated data
```

---

## Part 1 — Set up the VPS

### Step 1: Get a VPS

Any provider works. Cheap options that are fine for a Telegram bot:

| Provider | Cheapest plan | Notes |
|---|---|---|
| DigitalOcean | ~$6/month | "Droplet", easy setup |
| Vultr | ~$6/month | Similar to DigitalOcean |
| Hetzner | ~€4/month | Good value, EU servers |
| Linode (Akamai) | ~$5/month | |

Choose Ubuntu 22.04 or 24.04 when asked for an OS.
You will get a public IP address, a username (usually `ubuntu` or `root`),
and either a password or an SSH key.

### Step 2: Connect to the VPS

From your office PC, open a terminal (PowerShell or Command Prompt):

```powershell
ssh ubuntu@YOUR_VPS_IP
```

Replace `ubuntu` with your actual username and `YOUR_VPS_IP` with the
IP address from your provider dashboard.

### Step 3: Install Python on the VPS

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
python3 --version   # should be 3.10 or newer
```

### Step 4: Copy the bot files to the VPS

Back on your office PC:

```powershell
# Create the bot folder on the VPS
ssh ubuntu@YOUR_VPS_IP "mkdir -p ~/fm_bot/data"

# Copy the bot files (run from inside your fm_telegram_bot folder)
scp bot.py config.py console.py excel_loader.py formatters.py ^
    date_utils.py create_workbook.py check_setup.py test_offline.py ^
    requirements.txt .env.example ^
    ubuntu@YOUR_VPS_IP:~/fm_bot/
```

On Mac/Linux, replace `^` with `\` for line continuation.

Or use VS Code's Remote SSH extension to drag and drop the files.

### Step 5: Install bot dependencies on the VPS

```bash
cd ~/fm_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 6: Create the starter workbook on the VPS

```bash
cd ~/fm_bot
source venv/bin/activate
python create_workbook.py
```

This creates `data/maintenance_jobs.xlsx` on the VPS. The uploader
will overwrite it with the office copy shortly.

### Step 7: Create the .env on the VPS

```bash
cd ~/fm_bot
cp .env.example .env
nano .env
```

Set your bot token. Leave `EXCEL_PATH=` blank (defaults to
`data/maintenance_jobs.xlsx`, which is where the uploader writes it).

Save with Ctrl+X → Y → Enter.

### Step 8: Run the setup checker

```bash
cd ~/fm_bot
source venv/bin/activate
python check_setup.py
```

Fix any failures before continuing.

### Step 9: Run the bot as a background service

This keeps the bot running after you close the terminal.

```bash
sudo nano /etc/systemd/system/fmbot.service
```

Paste this (replace `ubuntu` with your actual username if different):

```ini
[Unit]
Description=FM Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/fm_bot
ExecStart=/home/ubuntu/fm_bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save, then enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable fmbot
sudo systemctl start fmbot
sudo systemctl status fmbot   # should show "active (running)"
```

Check the logs anytime with:

```bash
sudo journalctl -u fmbot -f
```

---

## Part 2 — Set up the office PC uploader

These steps run on the **office PC**, not the VPS.

### Step 10: Install uploader dependencies

Open a terminal in the `fm_telegram_bot` folder:

```powershell
pip install -r requirements_uploader.txt
```

### Step 11: Configure the uploader

```powershell
copy uploader_config.env.example uploader_config.env
notepad uploader_config.env
```

Fill in:

```
LOCAL_EXCEL_PATH=C:/Users/limju/Documents/FM/maintenance_jobs.xlsx
VPS_HOST=YOUR_VPS_IP
VPS_PORT=22
VPS_USER=ubuntu
VPS_PASSWORD=your-vps-password
REMOTE_PATH=/home/ubuntu/fm_bot/data/maintenance_jobs.xlsx
```

If using SSH key instead of password, leave `VPS_PASSWORD=` blank and set:
```
VPS_KEY_PATH=C:/Users/limju/.ssh/id_rsa
```

### Step 12: Test the uploader

```powershell
python uploader.py
```

You should see:
```
FM Bot — Excel Auto-Uploader
Watching : C:\...\maintenance_jobs.xlsx
Target   : ubuntu@123.456.789.0:/home/ubuntu/fm_bot/data/maintenance_jobs.xlsx
Uploading current file on startup...
Uploaded maintenance_jobs.xlsx -> 123.456.789.0:/home/ubuntu/fm_bot/data/...
Watching for changes. Press Ctrl+C to stop.
```

Now edit and save the Excel file — you should see "File changed — uploading..."
appear within 2 seconds.

### Step 13: Run the uploader at Windows startup (optional)

So it starts automatically when the office PC boots:

1. Press `Win + R`, type `shell:startup`, press Enter
2. In that folder, right-click → **New** → **Shortcut**
3. Target: `pythonw.exe "C:\full\path\to\fm_telegram_bot\uploader.py"`
   (`pythonw` runs without a console window)
4. Click **Next** → name it "FM Bot Uploader" → **Finish**
5. Right-click the shortcut → **Properties**
6. Set "Start in" to `C:\full\path\to\fm_telegram_bot`

---

## Part 3 — Network drive setup (if the file is on a shared drive)

If the Excel file lives on a shared network drive (e.g. `Z:\FM\maintenance_jobs.xlsx`
or `\\server\share\FM\maintenance_jobs.xlsx`):

Change `LOCAL_EXCEL_PATH` in `uploader_config.env`:

```
LOCAL_EXCEL_PATH=Z:/FM/maintenance_jobs.xlsx
```

Or using the UNC path:
```
LOCAL_EXCEL_PATH=//server/share/FM/maintenance_jobs.xlsx
```

The uploader watches the network path exactly like a local path.
watchdog uses the Windows file notification API, which works on
mapped drives as long as the drive is connected.

**One caveat:** if the drive disconnects (VPN drops, server restarts),
the uploader loses its watch. It does not automatically reconnect.
Restarting `uploader.py` re-establishes the watch. If reliability
matters, map the drive permanently rather than on-demand.

---

## How updates reach Telegram users

1. FM Officer opens `maintenance_jobs.xlsx` (local or network drive)
2. Makes changes, saves (`Ctrl+S`)
3. **Within ~2 seconds:** uploader detects the save, uploads via SFTP
4. **On VPS:** bot detects the file's modification time changed
5. **Next Telegram command:** bot reads the new data, sends updated reply

The 5-minute background refresh in the bot also re-reads the file
periodically, so even if the bot is quiet, it stays current.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Connection refused` on upload | VPS firewall blocking port 22 | Open port 22 in your VPS provider's firewall/security group |
| `Authentication failed` | Wrong password or key | Double-check `VPS_PASSWORD` or `VPS_KEY_PATH` |
| `No such file` on remote | `REMOTE_PATH` directory doesn't exist | The uploader creates it — check `VPS_USER` has write permission to `~` |
| Bot shows old data | Upload succeeded but bot hasn't reread | Send `/refresh` to force an immediate reload |
| Upload fires on every keystroke | `DEBOUNCE_SECONDS` too low | Increase to 3 or 5 in `uploader_config.env` |
| Uploader stops working after reboot | Not in startup folder | Redo Step 13 |
| Network drive path not working | Drive letter changed after reconnect | Use UNC path (`//server/share/...`) instead of drive letter |

---

## Security notes

- The uploader stores your VPS password in a plain text file.
  Set appropriate file permissions or use SSH key auth instead.
- The `service_account.json` (if using Google Sheets) and `uploader_config.env`
  are both in `.gitignore` and should never be committed to git.
- If your VPS provider has a firewall panel, consider restricting
  SSH access (port 22) to your office IP address only.
