"""Lightweight startup update checker.

Queries the PyPI JSON API for the latest published release and compares it
against the running version. Everything here is best-effort: network errors,
timeouts, or unexpected payloads never raise — they just report "no update".
Uses only the standard library so it works without extra dependencies.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.request
from typing import Callable

PACKAGE_NAME = "ezseedfinder"
PYPI_JSON_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
RELEASE_URL = f"https://pypi.org/project/{PACKAGE_NAME}/"
DEFAULT_TIMEOUT = 4.0

# Set this env var to any non-empty value to skip the network check entirely.
DISABLE_ENV_VAR = "EZSF_NO_UPDATE_CHECK"


def _version_tuple(version: str) -> tuple[int, ...]:
    """Parse a dotted version into a comparable tuple of ints.

    Non-numeric suffixes (e.g. release candidates) are truncated so that
    comparisons stay stable rather than raising on unexpected formats.
    """
    parts: list[int] = []
    for piece in version.strip().lstrip("vV").split("."):
        digits = ""
        for ch in piece:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer(latest: str, current: str) -> bool:
    try:
        return _version_tuple(latest) > _version_tuple(current)
    except Exception:
        return False


def get_latest_version(
    *, url: str = PYPI_JSON_URL, timeout: float = DEFAULT_TIMEOUT
) -> str | None:
    """Return the latest version string published on PyPI, or None on failure."""
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": f"{PACKAGE_NAME}-update-checker"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
        version = payload.get("info", {}).get("version")
        return version or None
    except Exception:
        return None


def check_for_update(
    current_version: str,
    *,
    url: str = PYPI_JSON_URL,
    timeout: float = DEFAULT_TIMEOUT,
) -> str | None:
    """Return the latest version if it is newer than ``current_version``.

    Returns None when up to date, when the check is disabled, or on any error.
    """
    if os.environ.get(DISABLE_ENV_VAR):
        return None
    latest = get_latest_version(url=url, timeout=timeout)
    if latest and is_newer(latest, current_version):
        return latest
    return None


def check_for_update_async(
    current_version: str,
    callback: Callable[[str | None], None],
    *,
    url: str = PYPI_JSON_URL,
    timeout: float = DEFAULT_TIMEOUT,
) -> threading.Thread:
    """Run :func:`check_for_update` on a daemon thread and invoke ``callback``.

    ``callback`` receives the newer version string, or None. It runs on the
    worker thread, so GUI callers must marshal back to their UI thread.
    """

    def worker() -> None:
        result = check_for_update(current_version, url=url, timeout=timeout)
        try:
            callback(result)
        except Exception:
            pass

    thread = threading.Thread(target=worker, name="ezsf-update-check", daemon=True)
    thread.start()
    return thread
