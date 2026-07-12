'''
PM4Py – A Process Mining Library for Python
Copyright (C) 2026 Process Intelligence Solutions GmbH

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see this software project's root or
visit <https://www.gnu.org/licenses/>.

Website: https://processintelligence.solutions
Contact: info@processintelligence.solutions
'''
"""Lifecycle-aware log parsing for Split Miner 2.0.

The directly-follows graph is built from ``complete`` events
only (mirroring ``lastComplete -> LID``); when the log carries genuine
``start``/``complete`` lifecycle information (``|start - complete| <
0.5 * total``) the log is treated as a *complex* log and an
overlap-based concurrency matrix is computed (two activities are
concurrent when one ``start`` arrives while the other is still
executing). A ``potential OR`` relation is recorded for every activity
pair that is observed both concurrently *and* exclusively.

The trace projection keeps activity *labels*;
ordering-sensitive downstream phases sort by label, so
the integer encoding is unnecessary for a result.
"""
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Set

from pm4py.algo.discovery.split_miner.dtypes.log import (
    END_LABEL,
    LabelTrace,
    START_LABEL,
)

_LIFECYCLE_START = "start"
_LIFECYCLE_COMPLETE = "complete"


@dataclass
class ComplexLogResult:
    """Outcome of :func:`parse_complex_log`."""

    traces: List[LabelTrace]
    is_complex: bool
    # overlap[(a, b)] = number of times a and b were executing
    # simultaneously (symmetric); only populated for complex logs.
    overlap: Dict[FrozenSet[str], int] = field(default_factory=dict)
    # observed[a] = number of completes of a.
    observed: Dict[str, int] = field(default_factory=dict)
    # potential_ors: activity pairs seen both concurrently and
    # exclusively (the Java ``potentialORs`` matrix, > 0 cells).
    potential_ors: Set[FrozenSet[str]] = field(default_factory=set)


def _lifecycle(ev, lifecycle_key: str) -> str:
    # Deliberate deviation: the Java reference assumes the attribute is
    # always present (and aborts otherwise). Treating a missing value as
    # ``complete`` lets lifecycle-free logs degrade to the simple-log
    # path instead of failing; for logs with uniform lifecycle data the
    # behaviour is identical.
    val = ev.get(lifecycle_key)
    return str(val).strip().lower() if val is not None else _LIFECYCLE_COMPLETE


def parse_complex_log(
    event_log,
    activity_key: str,
    lifecycle_key: str,
    timestamp_key: str = "time:timestamp",
) -> ComplexLogResult:
    """Project a pm4py event log onto Split Miner 2.0's complex log.

    Returns the per-trace ``complete``-event label sequences (wrapped in
    the start/end sentinels) together with the lifecycle metadata needed
    by the concurrency oracle and the OR-split heuristic.

    The reference implementation assumes a timestamp-ordered XES log;
    events within each trace are therefore sorted by timestamp (stably,
    so equal-timestamp events keep their recorded order) before the
    overlap-based concurrency is derived.
    """
    start_events = 0
    complete_events = 0
    total_events = 0

    overlap: Dict[FrozenSet[str], int] = {}
    observed: Dict[str, int] = {}

    all_labels: Set[str] = set()
    traces: List[LabelTrace] = []
    # One ``executed`` label set per trace, retained so exclusiveness can
    # be computed in a second pass for complex logs only (it is quadratic
    # in the activity count and never needed for simple logs).
    executed_per_trace: List[Set[str]] = []

    for trace in event_log:
        executing: Set[str] = set()
        executed: Set[str] = set()
        seq: List[str] = []
        events = [ev for ev in trace if activity_key in ev]
        if events and all(
            ev.get(timestamp_key) is not None for ev in events
        ):
            # Stable sort keeps equal-timestamp events in recorded order.
            events = sorted(events, key=lambda ev: ev[timestamp_key])
        for ev in events:
            label = str(ev[activity_key])
            all_labels.add(label)
            phase = _lifecycle(ev, lifecycle_key)
            total_events += 1
            if phase == _LIFECYCLE_START:
                start_events += 1
                for other in executing:
                    if other != label:
                        key = frozenset((other, label))
                        overlap[key] = overlap.get(key, 0) + 1
                executing.add(label)
                executed.add(label)
            elif phase == _LIFECYCLE_COMPLETE:
                complete_events += 1
                executing.discard(label)
                observed[label] = observed.get(label, 0) + 1
                seq.append(label)
                executed.add(label)

        traces.append([START_LABEL, *seq, END_LABEL])
        executed_per_trace.append(executed)

    is_complex = abs(start_events - complete_events) < total_events * 0.5

    potential_ors: Set[FrozenSet[str]] = set()
    if is_complex:
        # exclusiveness[(a, b)]: traces where exactly one of a, b ran.
        exclusiveness: Dict[FrozenSet[str], int] = {}
        for executed in executed_per_trace:
            not_executed = all_labels - executed
            for a in executed:
                for b in not_executed:
                    key = frozenset((a, b))
                    exclusiveness[key] = exclusiveness.get(key, 0) + 1
        for key, ov in overlap.items():
            if ov > 0 and exclusiveness.get(key, 0) > 0:
                potential_ors.add(key)
    else:
        # A non-complex log carries no overlap-based concurrency.
        overlap = {}

    return ComplexLogResult(
        traces=traces,
        is_complex=is_complex,
        overlap=overlap,
        observed=observed,
        potential_ors=potential_ors,
    )
