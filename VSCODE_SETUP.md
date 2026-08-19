# Running this project in VS Code (Windows)

Follow in order. Steps 1–3 are what fix the `requirements.txt not found` error and the 32-bit pandas problem.

## 1. Install 64-bit Python

Your current interpreter (`Python314-32`) is 32-bit, and **pandas publishes no 32-bit Windows wheels for Python 3.12+**. The install will fail no matter what you do in VS Code.

Download the **Windows installer (64-bit)** from [python.org](https://www.python.org/downloads/windows/). Python 3.13 is the safest choice.

During install, tick **"Add python.exe to PATH"**.

You can keep the 32-bit one installed — VS Code will let you choose between them.

## 2. Open the folder (not the file)

`File → Open Folder…` → select the `fm_telegram_bot` folder itself.

You should see `bot.py`, `config.py`, `requirements.txt` etc. in the sidebar.

**This is what fixed your pip error.** VS Code's integrated terminal opens in whatever folder you have open. If you opened a single file instead, the terminal starts somewhere else and `pip install -r requirements.txt` can't see the file.

Confirm with a new terminal (`Ctrl + \``):

```powershell
dir requirements.txt
```

If that lists the file, pip will find it too.

## 3. Select the 64-bit interpreter

`Ctrl+Shift+P` → type **Python: Select Interpreter** → Enter.

Pick the entry **without** `-32` in its path. You want something like:

```
C:\Users\limju\AppData\Local\Programs\Python\Python313\python.exe
```

NOT `...\Python314-32\python.exe`.

Verify in the terminal:

```powershell
python -c "import sys; print(sys.maxsize > 2**32)"
```

`True` means 64-bit. If it still says `False`, the wrong interpreter is selected — the active one shows in the blue status bar at the bottom right.

## 4. Create a virtual environment

`Ctrl+Shift+P` → **Python: Create Environment** → **Venv** → pick your 64-bit interpreter → tick `requirements.txt` when it offers.

That creates `.venv` and installs everything in one step. If it offers to install requirements, you can skip step 5.

Doing it manually instead:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**If PowerShell blocks activation** with a "running scripts is disabled" error, run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Or sidestep it by switching the terminal to Command Prompt (dropdown next to the `+` in the terminal panel) and using `venv\Scripts\activate.bat`.

You'll know the venv is active when the prompt shows `(venv)` or `(.venv)`.

## 5. Install dependencies

```powershell
pip install -r requirements.txt
```

This should now succeed. If pandas still tries to compile from source, you're on the 32-bit interpreter — go back to step 3.

## 6. Create your .env

In the VS Code explorer, right-click → **New File** → name it exactly `.env` (leading dot, no extension).

Paste in:

```
TELEGRAM_BOT_TOKEN=paste-your-token-from-BotFather-here
EXCEL_PATH=
SHEET_NAME=Jobs
REFRESH_INTERVAL_SECONDS=300
```

VS Code may warn about creating a dotfile — that's fine.

## 7. Test before going live

Open the Run and Debug panel (`Ctrl+Shift+D`), pick **"Test offline (no token needed)"** from the dropdown, press F5.

Every message prints in the terminal. Proofread the layout here — much faster than messaging yourself.

## 8. Run the bot

Same panel, select **"Run bot"**, press F5.

Open Telegram, find your bot, send `/start`.

Stop it with the red square in the debug toolbar, or `Ctrl+C` in the terminal.

## Debugging tips

**Set a breakpoint** by clicking the gutter left of a line number — try line 1 of `service_command` in `bot.py`. Send `/service` from your phone and VS Code will pause there, letting you inspect the DataFrame in the Variables panel.

**Inspect the data live**: with the bot paused, open the Debug Console and type `df.head()` or `df[config.COL_STATUS].value_counts()`.

**"Bot ignores everything"** usually means a second copy is still running from an earlier F5. Telegram allows only one poller per token. Check the terminal dropdown for orphaned sessions and kill them, or run `taskkill /F /IM python.exe` to clear all of them.

## Files in .vscode

| File | Purpose |
|---|---|
| `launch.json` | The three F5 run configurations |
| `settings.json` | Encoding, venv auto-activation, type checking |
| `extensions.json` | Prompts you to install the Python extension |

`settings.json` is gitignored because "Select Interpreter" writes your personal machine path into it.
