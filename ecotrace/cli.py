"""Command line interface for EcoTrace AI."""

from __future__ import annotations

import argparse
import sys

from ecotrace.dashboard.app import run_dashboard


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ecotrace",
        description="EcoTrace AI — LLM Observability & Workload Optimization SDK",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Dashboard subcommand
    dashboard_parser = subparsers.add_parser(
        "dashboard", help="Launch the EcoTrace AI Observability Dashboard"
    )
    dashboard_parser.add_argument(
        "--host",
        "-H",
        default="127.0.0.1",
        help="Host interface to bind (default: 127.0.0.1)",
    )
    dashboard_parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    dashboard_parser.add_argument(
        "--db",
        default="ecotrace.db",
        help="Path to SQLite database file (default: ecotrace.db)",
    )
    dashboard_parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed realistic sample data into database if empty",
    )

    args = parser.parse_args()

    if args.command == "dashboard":
        run_dashboard(
            host=args.host,
            port=args.port,
            db_path=args.db,
            auto_seed=args.seed,
        )
    elif args.command is None:
        # If run as 'ecotrace dashboard' or default launch
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
