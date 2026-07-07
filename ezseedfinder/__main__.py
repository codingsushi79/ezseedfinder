"""Unified entry point: ``ezsf`` CLI or ``ezsf -gui``."""

from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] in ("-gui", "--gui"):
        from ezseedfinder.gui import run_app

        run_app()
        return 0

    from ezseedfinder.cli_main import cli_main

    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
