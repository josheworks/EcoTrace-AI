"""CLI entrypoint for running the EcoTrace Observability Dashboard."""

import argparse
from ecotrace.dashboard.app import run_dashboard


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch the EcoTrace AI Observability & Analytics Dashboard."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface to bind (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--db",
        default="ecotrace.db",
        help="Path to SQLite database file (default: ecotrace.db)",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed realistic developer sample workloads if database is empty or requested",
    )

    args = parser.parse_args()
    run_dashboard(
        host=args.host,
        port=args.port,
        db_path=args.db,
        auto_seed=args.seed,
    )


if __name__ == "__main__":
    main()
