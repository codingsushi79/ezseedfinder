"""Package resource paths."""

from __future__ import annotations

from pathlib import Path


def package_root() -> Path:
    return Path(__file__).resolve().parent


def examples_dir() -> Path:
    """Directory containing bundled .ezsf example files."""
    pkg_examples = package_root() / "examples"
    if pkg_examples.is_dir():
        return pkg_examples
    return package_root().parent / "examples"
