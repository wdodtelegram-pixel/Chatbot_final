"""
date_utils.py
=============
PURPOSE
    You asked for every date to read as 'week 1 january 2026'. Excel, however,
    will happily hand pandas three different things depending on how the FM
    Officer typed the cell:

        1. a real datetime      -> Timestamp('2026-01-05')
        2. the text you want    -> "week 1 january 2026"
        3. something messy      -> "5/1/2026", "Jan 2026", "TBC", blank

    This module normalises all three into ONE consistent output string so the
    Telegram message always looks the same. Keeping this logic in its own file
    means the formatting rule lives in exactly one place.
"""

from __future__ import annotations

import re
from datetime import date, datetime

import pandas as pd

# Regex that recognises text a user already typed in the target format.
# PURPOSE: if the cell already says "Week 2 March 2026" we should trust it and
# just tidy the capitalisation instead of trying to re-parse it as a date.
_ALREADY_FORMATTED = re.compile(
    r"^\s*week\s*([1-5])\s+([a-z]+)\s+(\d{4})\s*$", re.IGNORECASE
)

_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _week_of_month(day: int) -> int:
    """
    PURPOSE: convert a day-of-month number into a week number 1-5.

    Days 1-7 are week 1, 8-14 week 2, and so on. This is the simple
    "calendar block" definition facilities teams normally mean when they say
    'week 1', rather than the ISO week-number definition.
    """
    return min(5, (day - 1) // 7 + 1)


def to_week_format(value) -> str:
    """
    PURPOSE: the single public function of this module. Takes anything from an
    Excel cell and returns a display string.

    Returns "-" for blanks so the message never shows the ugly word "NaT" or
    "nan" to a user, and returns unrecognised text unchanged (so a deliberate
    "TBC" or "On hold" written by staff still shows through).
    """
    # 1. Blank / NaN / NaT -> a neutral dash.
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    if pd.isna(value):
        return "-"

    # 2. Real date types coming out of a properly formatted Excel date cell.
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return f"Week {_week_of_month(value.day)} {_MONTH_NAMES[value.month - 1]} {value.year}"

    text = str(value).strip()
    if not text:
        return "-"

    # 3. Text that is already in the desired shape -> just normalise casing.
    match = _ALREADY_FORMATTED.match(text)
    if match:
        week, month, year = match.groups()
        return f"Week {week} {month.capitalize()} {year}"

    # 4. Anything date-like that pandas can understand ("5 Jan 2026",
    #    "2026-01-05", "05/01/2026"). dayfirst=True suits SG/UK date entry.
    try:
        parsed = pd.to_datetime(text, dayfirst=True, errors="raise")
        return f"Week {_week_of_month(parsed.day)} {_MONTH_NAMES[parsed.month - 1]} {parsed.year}"
    except Exception:
        # 5. Give up gracefully -- show exactly what staff typed.
        return text
