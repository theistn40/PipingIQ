"""
=========================================================
PipingIQ Professional v6.0
app.py
Application startup only.
=========================================================
"""

import sys

from ui import run_application


def main() -> int:
    try:
        run_application()
    except Exception as exc:
        print(f"Application failed to start: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
