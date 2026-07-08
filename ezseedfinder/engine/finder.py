"""Multi-threaded seed search engine."""

from __future__ import annotations

import os
import random
import threading
import time
from collections.abc import Callable
from typing import Any

from ..models.criteria import SearchConfig, SeedResult
from ..ezsf.parser import parse_ezsf, document_to_config
from .checker import SeedChecker


class SeedFinder:
    """Search for seeds matching criteria using worker threads."""

    def __init__(self, config: SearchConfig):
        self.config = config
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._pause.set()
        self._lock = threading.Lock()
        self.searched = 0
        self.rate = 0.0
        self.results: list[SeedResult] = []
        self._t0 = 0.0

        doc = config.criteria_ast
        if doc is None and config.gui_filters.get("ezsf_enabled", True):
            ezsf_text = config.gui_filters.get("ezsf_text", "")
            if ezsf_text.strip():
                doc = parse_ezsf(ezsf_text)

        self.checker = SeedChecker(doc=doc, gui_filters=config.gui_filters)
        self.max_results = config.max_results
        if doc and doc.max_results:
            self.max_results = doc.max_results
        self.threads = config.threads or max(1, (os.cpu_count() or 4) - 1)
        if doc and doc.threads:
            self.threads = doc.threads

        self.seed_start = config.seed_start
        self.seed_end = config.seed_end
        if doc:
            if doc.seed_start is not None:
                self.seed_start = doc.seed_start
            if doc.seed_end is not None:
                self.seed_end = doc.seed_end
        self.random_search = config.random_search
        if doc:
            self.random_search = doc.random_search

    def stop(self) -> None:
        self._stop.set()
        self._pause.set()

    def pause(self) -> None:
        self._pause.clear()

    def resume(self) -> None:
        self._pause.set()

    @property
    def running(self) -> bool:
        return not self._stop.is_set()

    def search(
        self,
        on_result: Callable[[SeedResult], None] | None = None,
        on_progress: Callable[[int, float], None] | None = None,
    ) -> list[SeedResult]:
        self._stop.clear()
        self._pause.set()
        self.searched = 0
        self.results = []
        self._t0 = time.monotonic()
        workers: list[threading.Thread] = []

        for i in range(self.threads):
            t = threading.Thread(
                target=self._worker,
                args=(i, on_result, on_progress),
                daemon=True,
            )
            workers.append(t)
            t.start()

        for t in workers:
            t.join()

        return self.results

    def _next_seed(self, worker_id: int) -> int | None:
        if self.random_search:
            if self.seed_start is not None and self.seed_end is not None:
                return random.randint(self.seed_start, self.seed_end)
            return random.randint(-(2**63), 2**63 - 1)

        if self.seed_start is None:
            self.seed_start = 0
        if self.seed_end is None:
            self.seed_end = 2**48

        span = self.seed_end - self.seed_start + 1
        idx = (self.searched + worker_id) % span
        return self.seed_start + idx

    def _worker(
        self,
        worker_id: int,
        on_result: Callable[[SeedResult], None] | None,
        on_progress: Callable[[int, float], None] | None,
    ) -> None:
        local = 0
        last_report = time.monotonic()

        while not self._stop.is_set():
            self._pause.wait()
            if self._stop.is_set():
                break

            with self._lock:
                if len(self.results) >= self.max_results:
                    self._stop.set()
                    break

            seed = self._next_seed(worker_id)
            if seed is None:
                break

            ok, details = self.checker.check(seed)
            local += 1

            with self._lock:
                self.searched += 1
                elapsed = max(time.monotonic() - self._t0, 0.001)
                self.rate = self.searched / elapsed

                if ok:
                    result = SeedResult(seed=seed, details=details)
                    self.results.append(result)
                    if len(self.results) > self.max_results:
                        self.results = self.results[: self.max_results]
                    if on_result:
                        on_result(result)
                    if len(self.results) >= self.max_results:
                        self._stop.set()

            now = time.monotonic()
            if on_progress and now - last_report > 0.25:
                with self._lock:
                    on_progress(self.searched, self.rate)
                last_report = now

        with self._lock:
            if on_progress:
                on_progress(self.searched, self.rate)


def load_ezsf_file(path: str) -> SearchConfig:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    doc = parse_ezsf(text)
    meta = document_to_config(doc)
    return SearchConfig(
        version=meta.get("version") or "26.2",
        threads=meta.get("threads") or 0,
        max_results=meta.get("max_results") or 10,
        seed_start=meta.get("seed_start"),
        seed_end=meta.get("seed_end"),
        random_search=meta.get("random_search", True),
        criteria_ast=doc,
    )
