"""
console.py
==========
PURPOSE
    Makes terminal output safe on Windows.

    Windows Python writes console output using the system's legacy code page
    (cp1252 for most Western installs) whenever stdout is NOT a real console --
    which happens when you redirect to a file, pipe to another command, or run
    under some VS Code debug configurations.

    cp1252 has no mapping for emoji or box-drawing characters, so a line like

        print("🟡 In Progress")

    raises UnicodeEncodeError and kills the script. That is a confusing crash
    when the actual program logic is fine.

    Importing this module once at the top of any script that prints non-ASCII
    switches stdout and stderr to UTF-8 and removes the whole problem.

USAGE
    import console  # noqa: F401  -- import for side effect, before any print
"""

import sys


def enable_utf8_output() -> None:
    """
    PURPOSE: reconfigure stdout/stderr to UTF-8, failing silently if it cannot.

    errors="replace" is a deliberate second layer of safety: if a terminal
    still cannot render a character, it prints a placeholder instead of
    raising. Losing one glyph is always better than losing the whole run.

    reconfigure() exists on Python 3.7+. The try/except means this module is
    harmless on any platform or Python version where it is unavailable.
    """
    for stream in (sys.stdout, sys.stderr):
        try:  # noqa: SIM105 -- explicit form kept; the comments below matter
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            # AttributeError: Python < 3.7, or a stream replaced by a test
            #                 harness / IDE that is not a TextIOWrapper.
            # OSError/ValueError: stream already detached or closed.
            pass


# Run on import so a single "import console" is all a script needs.
enable_utf8_output()
