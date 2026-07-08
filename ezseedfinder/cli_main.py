"""Headless CLI for EZ Seed Finder."""

from __future__ import annotations

import argparse
import sys

from ezseedfinder.engine.finder import SeedFinder, load_ezsf_file
from ezseedfinder.models.criteria import SearchConfig


def cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ezsf",
        description="EZ Seed Finder — search Minecraft Java Edition seeds",
    )
    parser.add_argument("-f", "--file", help="Path to .ezsf criteria file")
    parser.add_argument("-v", "--version", default="26.2", help="Minecraft version")
    parser.add_argument("-n", "--max-results", type=int, default=5)
    parser.add_argument("-t", "--threads", type=int, default=0)
    parser.add_argument("--village", type=int, default=0, help="Village max distance from spawn")
    parser.add_argument(
        "--stronghold", type=int, default=0, help="Stronghold max distance from spawn"
    )
    args = parser.parse_args(argv)

    if args.file:
        config = load_ezsf_file(args.file)
        config.max_results = args.max_results
        if args.threads:
            config.threads = args.threads
    else:
        gui_filters = {"version": args.version}
        if args.village:
            gui_filters["village_dist"] = args.village
            gui_filters["village_dist_enabled"] = True
        if args.stronghold:
            gui_filters["stronghold_dist"] = args.stronghold
            gui_filters["stronghold_dist_enabled"] = True
        config = SearchConfig(
            version=args.version,
            max_results=args.max_results,
            threads=args.threads,
            gui_filters=gui_filters,
        )

    finder = SeedFinder(config)

    def on_progress(n: int, rate: float) -> None:
        print(f"\rSearched {n:,} @ {rate:,.0f}/s", end="", flush=True)

    print("Searching...")
    results = finder.search(on_progress=on_progress)
    print()

    if not results:
        print("No seeds found.")
        return 1

    for r in results:
        print(f"Seed: {r.seed}")
        for k, v in r.details.items():
            print(f"  {k}: {v}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
