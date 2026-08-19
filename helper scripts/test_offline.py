"""
test_offline.py
===============
PURPOSE
    Lets you check the data pipeline and every message WITHOUT a Telegram token
    and without an internet connection.

    Run this first whenever you change the spreadsheet or the formatting. It
    prints the exact text the bot would send, so you can proofread the layout in
    a terminal instead of by messaging yourself on your phone.

RUN WITH
    python test_offline.py
"""

import re

import console  # noqa: F401 -- imported for its side effect: UTF-8 console output
import config
import excel_loader
import formatters
from date_utils import to_week_format


def strip_html(text: str) -> str:
    """PURPOSE: remove <b>/<i> tags so terminal output reads like the phone view."""
    return re.sub(r"<[^>]+>", "", text)


def main():
    print("=" * 70)
    print("1. LOADING WORKBOOK")
    print("=" * 70)
    df = excel_loader.load_jobs()
    print(f"Path    : {config.EXCEL_PATH}")
    print(f"Rows    : {len(df)}")
    print(f"Columns : {list(df.columns)}")
    print(f"\nStatus values found : {sorted(df[config.COL_STATUS].unique())}")
    print(f"Type values found   : {sorted(df[config.COL_TYPE].unique())}")
    print(f"Categories found    : {sorted(df[config.COL_CATEGORY].unique())}")

    print("\n" + "=" * 70)
    print("2. DATE FORMATTING CHECK")
    print("=" * 70)
    # PURPOSE: prove the week-format converter handles all the input shapes
    # staff might realistically produce.
    import datetime
    samples = [
        "Week 1 January 2026",   # already correct
        "week 3 march 2026",     # wrong case
        datetime.date(2026, 1, 5),    # real date -> week 1
        datetime.date(2026, 1, 12),   # real date -> week 2
        "5/1/2026",              # dd/mm/yyyy text
        "TBC",                   # deliberate free text
        None,                    # blank cell
    ]
    for s in samples:
        print(f"  {str(s):<24} -> {to_week_format(s)}")

    print("\n" + "=" * 70)
    print("3. /start")
    print("=" * 70)
    print(strip_html(formatters.welcome_message()))

    print("\n" + "=" * 70)
    print("4. /service")
    print("=" * 70)
    print(strip_html(formatters.dashboard_message(excel_loader.get_summary_counts())))

    for key in config.CATEGORIES:
        print("\n" + "=" * 70)
        print(f"5. /{key}")
        print("=" * 70)
        rows = excel_loader.get_jobs_for_category(key)
        print(strip_html(formatters.category_message(key, rows)))

    print("\n" + "=" * 70)
    print("6. /pending")
    print("=" * 70)
    print(strip_html(formatters.pending_message(df)))

    print("\n" + "=" * 70)
    print("7. MESSAGE LENGTH CHECK (Telegram limit is 4096 characters)")
    print("=" * 70)
    checks = {
        "/start": formatters.welcome_message(),
        "/service": formatters.dashboard_message(excel_loader.get_summary_counts()),
        "/pending": formatters.pending_message(df),
    }
    for key in config.CATEGORIES:
        checks[f"/{key}"] = formatters.category_message(
            key, excel_loader.get_jobs_for_category(key)
        )

    for name, text in checks.items():
        flag = "OK" if len(text) < 4096 else "TOO LONG!"
        print(f"  {name:<14} {len(text):>5} chars   {flag}")

    print("\nAll checks complete.")


if __name__ == "__main__":
    main()
