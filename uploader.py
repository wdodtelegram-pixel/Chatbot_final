"""
uploader.py  —  runs on the OFFICE PC (not the VPS)
"""
from __future__ import annotations
import logging
import os
import sys
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO,
    handlers=[logging.StreamHandler(), logging.FileHandler("uploader.log", encoding="utf-8")])
logger = logging.getLogger(__name__)

_cfg = Path(__file__).parent / "uploader_config.env"
if _cfg.exists():
    load_dotenv(_cfg, override=True)

def _env(key, default=""):
    v = os.getenv(key, default)
    return v.strip() if v else default

LOCAL_FILE       = Path(_env("LOCAL_EXCEL_PATH", "data/maintenance_jobs.xlsx")).expanduser()
VPS_HOST         = _env("VPS_HOST")
VPS_PORT         = int(_env("VPS_PORT", "22"))
VPS_USER         = _env("VPS_USER")
VPS_PASSWORD     = _env("VPS_PASSWORD")
VPS_KEY_PATH     = _env("VPS_KEY_PATH")
REMOTE_PATH      = _env("REMOTE_PATH")
DEBOUNCE_SECONDS = float(_env("DEBOUNCE_SECONDS", "2"))

def _validate():
    errors = []
    if not LOCAL_FILE.exists():
        errors.append(f"LOCAL_EXCEL_PATH does not exist: {LOCAL_FILE}")
    if not VPS_HOST:
        errors.append("VPS_HOST is empty.")
    if not VPS_USER:
        errors.append("VPS_USER is empty.")
    if not REMOTE_PATH:
        errors.append("REMOTE_PATH is empty.")
    if not VPS_PASSWORD and not VPS_KEY_PATH:
        errors.append("Set either VPS_PASSWORD or VPS_KEY_PATH in uploader_config.env.")
    if VPS_KEY_PATH and not Path(VPS_KEY_PATH).expanduser().exists():
        errors.append(f"VPS_KEY_PATH does not exist: {VPS_KEY_PATH}")
    return errors

def upload_file():
    import paramiko
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = {"hostname": VPS_HOST, "port": VPS_PORT, "username": VPS_USER, "timeout": 15}
        if VPS_KEY_PATH:
            kwargs["key_filename"] = str(Path(VPS_KEY_PATH).expanduser())
        else:
            kwargs["password"] = VPS_PASSWORD
        client.connect(**kwargs)
        with client.open_sftp() as sftp:
            remote_dir = REMOTE_PATH.rsplit("/", 1)[0]
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                parts = remote_dir.split("/")
                for i in range(2, len(parts) + 1):
                    try:  # noqa: SIM105
                        sftp.mkdir("/".join(parts[:i]))
                    except OSError:
                        pass
            sftp.put(str(LOCAL_FILE), REMOTE_PATH)
        client.close()
        logger.info("Uploaded %s -> %s:%s", LOCAL_FILE.name, VPS_HOST, REMOTE_PATH)
        return True
    except Exception as exc:
        logger.error("Upload failed: %s", exc)
        return False

class ExcelChangeHandler:
    def __init__(self):
        self._timer = None
        self._lock = threading.Lock()

    def on_change(self, path):
        if Path(path).name.startswith("~$"):
            return
        if Path(path).resolve() != LOCAL_FILE.resolve():
            return
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(DEBOUNCE_SECONDS, self._do_upload)
            self._timer.start()

    def _do_upload(self):
        logger.info("File changed — uploading...")
        upload_file()

def _build_observer(handler):
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class _Adapter(FileSystemEventHandler):
        def on_any_event(self, event):
            if not event.is_directory:
                handler.on_change(str(event.src_path))
                dest = getattr(event, "dest_path", None)
                if dest:
                    handler.on_change(str(dest))

    observer = Observer()
    observer.schedule(_Adapter(), str(LOCAL_FILE.parent), recursive=False)
    return observer

def main():
    print("=" * 60)
    print("  FM Bot — Excel Auto-Uploader")
    print("=" * 60)

    errors = _validate()
    if errors:
        print("\n[ERROR] Configuration problems:\n")
        for e in errors:
            print(f"  • {e}")
        print("\nEdit uploader_config.env and restart.\n")
        sys.exit(1)

    logger.info("Watching : %s", LOCAL_FILE)
    logger.info("Target   : %s@%s:%s", VPS_USER, VPS_HOST, REMOTE_PATH)
    logger.info("Uploading current file on startup...")
    upload_file()

    handler = ExcelChangeHandler()
    observer = _build_observer(handler)
    observer.start()
    logger.info("Watching for changes. Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping.")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
