"""Small, dependency-free Prometheus metrics for bounded execution outcomes."""

from collections import defaultdict
from threading import Lock

_OPERATIONS = frozenset({"ingestion", "plans", "approvals", "executions"})
_OUTCOMES = frozenset(
    {"created", "duplicate", "existing", "approved", "rejected", "succeeded", "retried", "failed"}
)


class Metrics:
    # ponytail: Process-local metrics omit other API and worker processes; replace this registry
    # with a shared Prometheus/OpenTelemetry exporter before horizontally scaling.
    """Aggregate only bounded operation/outcome labels, never tenant identifiers."""

    def __init__(self) -> None:
        self._counts: dict[tuple[str, str], int] = defaultdict(int)
        self._durations: dict[tuple[str, str], tuple[int, float]] = {}
        self._lock = Lock()

    def observe(self, operation: str, outcome: str, duration_seconds: float) -> None:
        if operation not in _OPERATIONS or outcome not in _OUTCOMES:
            raise ValueError("metrics require a bounded operation and outcome")
        key = (operation, outcome)
        with self._lock:
            self._counts[key] += 1
            count, total = self._durations.get(key, (0, 0.0))
            self._durations[key] = (count + 1, total + max(duration_seconds, 0.0))

    def render(self) -> str:
        with self._lock:
            counts = dict(self._counts)
            durations = dict(self._durations)
        lines = [
            "# HELP flowpilot_operations_total Completed FlowPilot operations.",
            "# TYPE flowpilot_operations_total counter",
        ]
        for (operation, outcome), count in sorted(counts.items()):
            labels = f'operation="{operation}",outcome="{outcome}"'
            lines.append(f"flowpilot_operations_total{{{labels}}} {count}")
        lines.extend(
            [
                "# HELP flowpilot_operation_duration_seconds Operation duration in seconds.",
                "# TYPE flowpilot_operation_duration_seconds summary",
            ]
        )
        for (operation, outcome), (count, total) in sorted(durations.items()):
            labels = f'operation="{operation}",outcome="{outcome}"'
            lines.append(f"flowpilot_operation_duration_seconds_count{{{labels}}} {count}")
            lines.append(f"flowpilot_operation_duration_seconds_sum{{{labels}}} {total}")
        return "\n".join(lines) + "\n"


metrics = Metrics()
