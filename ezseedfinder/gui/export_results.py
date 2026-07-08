"""Export seed search results to disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models.criteria import SeedResult


def results_to_json(results: list[SeedResult]) -> str:
    payload = [
        {"seed": r.seed, "details": _json_safe(r.details)} for r in results
    ]
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def results_to_text(results: list[SeedResult]) -> str:
    lines: list[str] = []
    for r in results:
        lines.append(f"Seed: {r.seed}")
        for key, value in sorted(r.details.items()):
            lines.append(f"  {key}: {value}")
        lines.append("")
    return "\n".join(lines)


def write_results(path: Path, results: list[SeedResult], fmt: str) -> None:
    if fmt == "json":
        path.write_text(results_to_json(results), encoding="utf-8")
    else:
        path.write_text(results_to_text(results), encoding="utf-8")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
