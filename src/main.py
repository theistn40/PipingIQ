"""
=========================================================
PipingIQ Professional v6.0
main.py
CLI wrapper for the Phase 1 SQLite bootstrap.
=========================================================
"""

from __future__ import annotations

import argparse
from pathlib import Path

from config import PIPE_SPEC_DATABASE, SQLITE_DATABASE
from database import build_sqlite_database


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create the PipingIQ runtime SQLite database from PipeSpec_Master.xlsx."
    )
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=SQLITE_DATABASE,
        help=f"SQLite file to create or replace. Default: {SQLITE_DATABASE}",
    )
    parser.add_argument(
        "--pipe-spec-path",
        type=Path,
        default=PIPE_SPEC_DATABASE,
        help=f"Pipe spec workbook to import. Default: {PIPE_SPEC_DATABASE}",
    )
    return parser


def main() -> int:
    parser = _build_argument_parser()
    args = parser.parse_args()
    sqlite_path = build_sqlite_database(
        sqlite_path=args.sqlite_path,
        pipe_spec_path=args.pipe_spec_path,
    )
    print(f"SQLite database created at {sqlite_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
