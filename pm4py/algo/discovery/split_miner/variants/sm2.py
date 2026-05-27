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
"""Split Miner 2.0.

Differs from the classic pipeline in four phases:

  * trace extraction is lifecycle-aware — each event keeps its
    ``start`` / ``end`` phase and its timestamp;
  * the directly-follows graph uses the refined definition that
    requires a ``start`` of ``b`` after the ``end`` of ``a`` with no
    intervening end event;
  * the concurrency oracle compares lifecycle overlaps rather than
    directly-follows frequencies;
  * two heuristics run between split and join discovery: an
    improper-completion fix and an OR-split identification.
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from pm4py.algo.discovery.split_miner.concurrency.refined import (
    Parameters as ConcParameters,
    RefinedConcurrencyOracle,
)
from pm4py.algo.discovery.split_miner.dfg_discovery.refined import (
    RefinedDFGDiscoverer,
)
from pm4py.algo.discovery.split_miner.dtypes.concurrency import (
    ConcurrencyResult,
)
from pm4py.algo.discovery.split_miner.dtypes.dfg import DFG
from pm4py.algo.discovery.split_miner.dtypes.log import (
    END_LABEL,
    RefinedEvent,
    RefinedTrace,
    START_LABEL,
)
from pm4py.algo.discovery.split_miner.dtypes.loops import LoopInfo
from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.algo.discovery.split_miner.filtering.max_min import (
    Parameters as FilterParameters,
)
from pm4py.algo.discovery.split_miner.heuristics.improper_completion import (
    ImproperCompletionHeuristic,
)
from pm4py.algo.discovery.split_miner.heuristics.or_split import (
    OrSplitHeuristic,
)
from pm4py.algo.discovery.split_miner.variants.abc import (
    Parameters as FrameworkParameters,
    SplitMinerFramework,
)
from pm4py.objects.bpmn.obj import BPMN
from pm4py.objects.conversion.log import converter as log_conversion
from pm4py.objects.log.obj import EventLog, EventStream
from pm4py.objects.log.util import interval_lifecycle
from pm4py.util import constants, exec_utils
from pm4py.util import xes_constants as xes_util


class Parameters(Enum):
    EPSILON = ConcParameters.EPSILON.value
    ETA = FilterParameters.ETA.value
    OR_MINIMISE = FrameworkParameters.OR_MINIMISE.value
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY
    TIMESTAMP_KEY = constants.PARAMETER_CONSTANT_TIMESTAMP_KEY


class SM2SplitMiner(SplitMinerFramework):
    """Split Miner 2.0 — lifecycle-aware variant with post-split heuristics."""

    # ------------------------------------------------------------------
    # Phase 0 — lifecycle-aware trace extraction
    # ------------------------------------------------------------------

    def do_extract_traces(
        self,
        log: Union[EventLog, EventStream, pd.DataFrame],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[RefinedTrace]:
        parameters = parameters or {}
        activity_key = exec_utils.get_param_value(
            constants.PARAMETER_CONSTANT_ACTIVITY_KEY,
            parameters,
            xes_util.DEFAULT_NAME_KEY,
        )
        timestamp_key = exec_utils.get_param_value(
            constants.PARAMETER_CONSTANT_TIMESTAMP_KEY,
            parameters,
            xes_util.DEFAULT_TIMESTAMP_KEY,
        )
        start_timestamp_key = xes_util.DEFAULT_START_TIMESTAMP_KEY

        event_log = (
            log
            if isinstance(log, EventLog)
            else log_conversion.apply(
                log, variant=log_conversion.Variants.TO_EVENT_LOG
            )
        )

        # Delegate the standard XES lifecycle handling to pm4py: this
        # pairs ``start``/``complete`` events into interval events that
        # expose both a ``start_timestamp`` and a ``time:timestamp``,
        # short-circuits when the log is already in interval form, and
        # honours the same parameter conventions as the rest of pm4py.
        interval_log = interval_lifecycle.to_interval(
            event_log, parameters=parameters
        )

        traces: List[RefinedTrace] = []
        for raw_trace, conv_trace in zip(event_log, interval_log):
            events: List[RefinedEvent] = self._refined_from_interval(
                conv_trace, activity_key, start_timestamp_key, timestamp_key
            )
            if not events:
                # Fall back to the raw trace and treat every event as
                # instantaneous — SM 2.0 then degenerates to the classic
                # pipeline rather than crashing on the empty log.
                events = self._refined_from_raw(
                    raw_trace, activity_key, timestamp_key
                )

            # Stable sort keeps the synthesised start before its matching
            # end when both share a timestamp.
            events_idx = sorted(
                enumerate(events),
                key=lambda p: (p[1][2] if p[1][2] is not None else 0, p[0]),
            )
            events = [e for _, e in events_idx]
            if events:
                wrapped: RefinedTrace = [
                    (START_LABEL, "start", None),
                    (START_LABEL, "end", None),
                    *events,
                    (END_LABEL, "start", None),
                    (END_LABEL, "end", None),
                ]
                traces.append(wrapped)
        return traces

    @staticmethod
    def _refined_from_interval(
        trace,
        activity_key: str,
        start_timestamp_key: str,
        timestamp_key: str,
    ) -> List[RefinedEvent]:
        """Convert a pm4py interval-format trace into refined events."""
        events: List[RefinedEvent] = []
        for ev in trace:
            if activity_key not in ev:
                continue
            label = str(ev[activity_key])
            end_ts = ev.get(timestamp_key)
            start_ts = ev.get(start_timestamp_key, end_ts)
            events.append((label, "start", start_ts))
            events.append((label, "end", end_ts))
        return events

    @staticmethod
    def _refined_from_raw(
        trace,
        activity_key: str,
        timestamp_key: str,
    ) -> List[RefinedEvent]:
        """Fallback: every raw event becomes an instantaneous interval."""
        events: List[RefinedEvent] = []
        for ev in trace:
            if activity_key not in ev:
                continue
            label = str(ev[activity_key])
            ts = ev.get(timestamp_key)
            events.append((label, "start", ts))
            events.append((label, "end", ts))
        return events

    # ------------------------------------------------------------------
    # Phase 1 — refined DFG
    # ------------------------------------------------------------------

    def do_dfg_discovery(
        self,
        traces: List[RefinedTrace],
        parameters: Optional[Dict[str, Any]] = None,
    ):
        return RefinedDFGDiscoverer.apply(traces, parameters)

    # ------------------------------------------------------------------
    # Phase 2 — lifecycle-overlap concurrency oracle
    # ------------------------------------------------------------------

    def do_concurrency(
        self,
        dfg: DFG,
        traces: Optional[List[RefinedTrace]],
        loops: LoopInfo,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ConcurrencyResult:
        return RefinedConcurrencyOracle.apply(dfg, traces, loops, parameters)

    # ------------------------------------------------------------------
    # Phase 6 — lifecycle-driven heuristics
    # ------------------------------------------------------------------

    def do_apply_heuristics(
        self,
        wg: WorkingGraph,
        traces: List[RefinedTrace],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        ImproperCompletionHeuristic.apply(wg, traces, parameters)
        OrSplitHeuristic.apply(wg, traces, parameters)


def apply(
    log: Union[EventLog, EventStream, pd.DataFrame],
    parameters: Optional[Dict[str, Any]] = None,
) -> BPMN:
    """Discover a BPMN model using Split Miner 2.0."""
    return SM2SplitMiner().apply(log, parameters)
