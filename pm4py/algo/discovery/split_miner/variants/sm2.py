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

A faithful re-implementation of the reference ``MineWithSMTC`` pipeline.
It reuses the classic Split Miner machinery (directly-follows graph,
filter, Oracle splits, SESE joins) and differs only where Split Miner
2.0 genuinely differs:

  * **lifecycle-aware log parsing** — the directly-follows graph is built
    from ``complete`` events only, and a log carrying genuine
    ``start``/``complete`` lifecycles (``|start - complete| < 0.5*total``)
    additionally yields an *overlap*-based concurrency oracle;
  * **fixed frequency threshold** — ``eta`` is pinned to ``1.0``;
  * **no OR-replacement** — non-trivial inclusive joins are left as OR
    gateways (``replaceIORs = false``) rather than expanded into
    AND/XOR plus token generators;
  * **compact self-loops** — level-1 loops stay as marked activities
    instead of being expanded into XOR-loop structures;
  * **light reduction** — only trivial XOR gateways are cleaned up; the
    aggressive split/join flattening of the classic exporter is skipped.
"""
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set, Union

import pandas as pd

from pm4py.algo.discovery.split_miner.bpmn_export.lifecycle import (
    LifecycleBPMNExporter,
)
from pm4py.algo.discovery.split_miner.concurrency.classic import (
    ClassicConcurrencyOracle,
    DEFAULT_EPSILON,
    Parameters as ConcParameters,
)
from pm4py.algo.discovery.split_miner.concurrency.lifecycle import (
    apply_overlap_concurrency,
)
from pm4py.algo.discovery.split_miner.dtypes.complex_log import (
    parse_complex_log,
)
from pm4py.algo.discovery.split_miner.dtypes.concurrency import (
    ConcurrencyResult,
)
from pm4py.algo.discovery.split_miner.dtypes.dfg import DFG
from pm4py.algo.discovery.split_miner.dtypes.gateway_map import (
    replace_inclusive_joins,
)
from pm4py.algo.discovery.split_miner.dtypes.loops import LoopInfo
from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.algo.discovery.split_miner.filtering.max_min import (
    Parameters as FilterParameters,
)
from pm4py.algo.discovery.split_miner.or_min.or_split import (
    apply_or_split_heuristic,
)
from pm4py.algo.discovery.split_miner.variants.abc import (
    Parameters as FrameworkParameters,
    SplitMinerFramework,
)
from pm4py.objects.bpmn.obj import BPMN
from pm4py.objects.bpmn.util import reduction
from pm4py.objects.conversion.log import converter as log_conversion
from pm4py.objects.log.obj import EventLog, EventStream
from pm4py.util import constants, exec_utils
from pm4py.util import xes_constants as xes_util

# Split Miner 2.0 pins the percentile frequency threshold to 1.0.
SM2_ETA = 1.0


class Parameters(Enum):
    EPSILON = ConcParameters.EPSILON.value
    # ETA and OR_MINIMISE are accepted for API compatibility with the
    # classic variant but have no effect here: the reference SM 2.0
    # pins eta to 1.0 and always runs its OR handling.
    ETA = FilterParameters.ETA.value
    OR_MINIMISE = FrameworkParameters.OR_MINIMISE.value
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY
    TIMESTAMP_KEY = constants.PARAMETER_CONSTANT_TIMESTAMP_KEY


class SM2SplitMiner(SplitMinerFramework):
    """Split Miner 2.0 — lifecycle-aware, OR-preserving variant."""

    def __init__(self) -> None:
        # Lifecycle metadata captured during trace extraction and
        # consumed by the later concurrency / OR-handling phases.
        self._is_complex: bool = False
        self._overlap: Dict[FrozenSet[str], int] = {}
        self._observed: Dict[str, int] = {}
        self._potential_ors: Set[FrozenSet[str]] = set()

    # ------------------------------------------------------------------
    # Phase 0 — lifecycle-aware trace extraction (getComplexLog)
    # ------------------------------------------------------------------

    def do_extract_traces(
        self,
        log: Union[EventLog, EventStream, pd.DataFrame],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[List[str]]:
        parameters = parameters or {}
        activity_key = exec_utils.get_param_value(
            constants.PARAMETER_CONSTANT_ACTIVITY_KEY,
            parameters,
            xes_util.DEFAULT_NAME_KEY,
        )
        lifecycle_key = exec_utils.get_param_value(
            constants.PARAMETER_CONSTANT_TRANSITION_KEY,
            parameters,
            xes_util.DEFAULT_TRANSITION_KEY,
        )
        timestamp_key = exec_utils.get_param_value(
            constants.PARAMETER_CONSTANT_TIMESTAMP_KEY,
            parameters,
            xes_util.DEFAULT_TIMESTAMP_KEY,
        )
        event_log = (
            log
            if isinstance(log, EventLog)
            else log_conversion.apply(
                log, variant=log_conversion.Variants.TO_EVENT_LOG
            )
        )
        result = parse_complex_log(
            event_log, activity_key, lifecycle_key, timestamp_key
        )
        self._is_complex = result.is_complex
        self._overlap = result.overlap
        self._observed = result.observed
        self._potential_ors = result.potential_ors
        return result.traces

    # ------------------------------------------------------------------
    # Phase 2 — concurrency: overlap (complex log) or classic imbalance
    # ------------------------------------------------------------------

    def do_concurrency(
        self,
        dfg: DFG,
        traces,
        loops: LoopInfo,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ConcurrencyResult:
        if self._is_complex:
            eps = exec_utils.get_param_value(
                ConcParameters.EPSILON, parameters or {}, DEFAULT_EPSILON
            )
            return apply_overlap_concurrency(
                dfg, self._overlap, self._observed, eps
            )
        return ClassicConcurrencyOracle.apply(dfg, traces, loops, parameters)

    # ------------------------------------------------------------------
    # Phase 3 — filter, with eta pinned to 1.0
    # ------------------------------------------------------------------

    def do_filter(self, pdfg, parameters=None):
        params = dict(parameters or {})
        params[FilterParameters.ETA.value] = SM2_ETA
        return super().do_filter(pdfg, params)

    # ------------------------------------------------------------------
    # Phase 7 — OR handling: replaceIORs = false (keep inclusive joins)
    # ------------------------------------------------------------------

    def or_handling_is_mandatory(self) -> bool:
        # The reference SM 2.0 pipeline always runs ``replaceIORs(false)``;
        # there is no Java equivalent of skipping it, so SM 2.0 ignores the
        # ``minimize_or_joins`` flag (just as it ignores ``eta``).
        return True

    def do_minimize_or_joins(self, wg: WorkingGraph, parameters=None):
        replace_inclusive_joins(wg, apply_hagen=False)
        # replaceIORs == false also runs the OR-split heuristic: AND
        # splits over potential-OR branches become OR-splits, matched by
        # OR-joins. Only fires on complex logs (potential_ors non-empty).
        apply_or_split_heuristic(wg, self._potential_ors)

    # ------------------------------------------------------------------
    # Phase 8 — export: compact self-loops, light reduction only
    # ------------------------------------------------------------------

    def do_export_bpmn(self, wg: WorkingGraph, parameters=None) -> BPMN:
        bpmn = LifecycleBPMNExporter.apply(wg, parameters)
        # Split Miner 2.0 only removes trivial XOR gateways; it does not
        # flatten nested same-type split/join gateways.
        return reduction.apply(bpmn, {})


def apply(
    log: Union[EventLog, EventStream, pd.DataFrame, DFG, str],
    parameters: Optional[Dict[str, Any]] = None,
) -> BPMN:
    """Discover a BPMN model using Split Miner 2.0."""
    return SM2SplitMiner().apply(log, parameters)
