"""Deterministic, domain-neutral planning benchmark aggregation."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


@dataclass(frozen=True)
class BenchmarkCaseResult:
    case_id: str
    success: bool
    latency_ms: float
    safety_violations: int = 0

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id must not be empty")
        if not isfinite(self.latency_ms) or self.latency_ms < 0:
            raise ValueError("latency_ms must be finite and non-negative")
        if self.safety_violations < 0:
            raise ValueError("safety_violations must be non-negative")


@dataclass(frozen=True)
class BenchmarkSummary:
    case_count: int
    success_rate: float
    mean_latency_ms: float
    total_safety_violations: int


def summarize_benchmark(results: Iterable[BenchmarkCaseResult]) -> BenchmarkSummary:
    items = tuple(results)
    if not items:
        raise ValueError("at least one benchmark result is required")
    if len({item.case_id for item in items}) != len(items):
        raise ValueError("case_id values must be unique")
    return BenchmarkSummary(
        case_count=len(items),
        success_rate=sum(item.success for item in items) / len(items),
        mean_latency_ms=sum(item.latency_ms for item in items) / len(items),
        total_safety_violations=sum(item.safety_violations for item in items),
    )
