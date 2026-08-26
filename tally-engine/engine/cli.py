"""Argparse CLI.

Supports both flag style (``python -m engine --json``) and a
positional command (``python -m engine json``). Legacy no-op flags from the
single-file script (``--no-sync-snapshot``, ``--write-sync``) are accepted.

Usage:
    python -m engine --json
    python -m engine projects
    python -m engine dashboard --period all
    python -m engine update-prices
"""
from __future__ import annotations

import argparse
import sys

from . import main

_COMMANDS = ["json", "projects", "dashboard", "daily-costs", "wrapped",
             "quota-detail", "update-prices"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="engine", description="Tolly cross-platform usage engine")
    p.add_argument("command", nargs="?", default="json", choices=_COMMANDS,
                   help="subcommand (defaults to 'json')")
    # Flag alias retained for desktop-shell compatibility.
    p.add_argument("--json", dest="command", action="store_const", const="json",
                   help="alias for the 'json' command")
    p.add_argument("--period", default="all",
                   choices=["today", "week", "month", "year", "all"])
    # Legacy no-ops accepted for backwards compatibility.
    p.add_argument("--no-sync-snapshot", action="store_true", help="legacy no-op")
    p.add_argument("--write-sync", action="store_true", help="legacy no-op")
    return p


DISPATCH = {
    "json": main.cmd_json,
    "projects": main.cmd_projects,
    "dashboard": main.cmd_dashboard,
    "daily-costs": main.cmd_daily_costs,
    "wrapped": main.cmd_wrapped,
    "quota-detail": main.cmd_quota_detail,
    "update-prices": main.cmd_update_prices,
}


def main_cli(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    fn = DISPATCH.get(args.command)
    if fn is None:
        parser.print_help()
        return 2
    fn(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
