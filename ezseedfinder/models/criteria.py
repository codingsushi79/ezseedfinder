"""Data models for seed search configuration and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SeedResult:
    seed: int
    details: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        parts = [str(self.seed)]
        if self.details:
            parts.append(str(self.details))
        return " | ".join(parts)


@dataclass
class SearchConfig:
    """Complete search configuration from GUI and/or .ezsf file."""

    version: str = "26.2"
    threads: int = 0  # 0 = auto
    max_results: int = 10
    seed_start: int | None = None
    seed_end: int | None = None
    random_search: bool = True
  # Parsed AST root from .ezsf (optional)
    criteria_ast: Any = None
  # Quick GUI filters (merged with .ezsf when both present)
    gui_filters: dict[str, Any] = field(default_factory=dict)
