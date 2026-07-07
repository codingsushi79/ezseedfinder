#!/usr/bin/env python3
"""Legacy dev entry point — prefer ``ezsf`` after install."""

from ezseedfinder.cli_main import cli_main

if __name__ == "__main__":
    raise SystemExit(cli_main())
