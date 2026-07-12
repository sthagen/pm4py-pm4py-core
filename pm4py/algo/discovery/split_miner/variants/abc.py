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
"""Base class implementing the Split Miner framework.

How to extend:

1. Subclass :class:`SplitMinerFramework`.
2. Override :meth:`do_extract_traces` and any of the other ``do_*`` phase
   methods whose behaviour differs from the default classic pipeline.
3. Expose a top-level ``apply`` function that instantiates the subclass
   and forwards to :meth:`apply`.

The :meth:`apply` driver runs the canonical Split Miner pipeline:
(1) trace extraction, (2) DFG + loop discovery, (3) concurrency,
(4) PDFG filtering, (5) initial BPMN, (6) split discovery,
(7) join discovery, (8) OR handling, (9) BPMN export. The default
implementations of every ``do_*`` method match the classic Split Miner;
subclasses change only the phases that genuinely differ from the
classic flow.
"""
from abc import ABC
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from pm4py.algo.discovery.split_miner.bpmn_export.classic import (
    ClassicBPMNExporter,
)
from pm4py.algo.discovery.split_miner.bpmn_init.classic import (
    ClassicBPMNInitializer,
)
from pm4py.algo.discovery.split_miner.concurrency.classic import (
    ClassicConcurrencyOracle,
)
from pm4py.algo.discovery.split_miner.dfg_discovery.classic import (
    ClassicDFGDiscoverer,
    strip_self_loops,
)
from pm4py.algo.discovery.split_miner.dtypes.concurrency import (
    ConcurrencyResult,
)
from pm4py.objects.bpmn.util import reduction
from pm4py.algo.discovery.split_miner.dtypes.dfg import DFG
from pm4py.algo.discovery.split_miner.dtypes.filtering import FilterResult
from pm4py.algo.discovery.split_miner.dtypes.log import (
    END_LABEL,
    LabelTrace,
    START_LABEL,
)
from pm4py.algo.discovery.split_miner.dtypes.loops import LoopInfo
from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.algo.discovery.split_miner.filtering.max_min import MaxMinFilterer
from pm4py.algo.discovery.split_miner.joins.sese import (
    SeseJoinsDiscoverer,
)
from pm4py.algo.discovery.split_miner.or_min.classic import (
    ClassicOrJoinMinimizer,
)
from pm4py.algo.discovery.split_miner.splits.classic import (
    ClassicSplitsDiscoverer,
)
from pm4py.objects.bpmn.obj import BPMN
from pm4py.objects.conversion.log import converter as log_conversion
from pm4py.objects.log.obj import EventLog, EventStream
from pm4py.util import constants, exec_utils
from pm4py.util import xes_constants as xes_util


class Parameters(Enum):
    OR_MINIMISE = "split_miner_or_minimise"


DEFAULT_OR_MINIMISE = True


class SplitMinerFramework(ABC):
    """Pipeline runner shared by every Split Miner variant."""

    # ------------------------------------------------------------------
    # Phase 0 — log extraction
    # ------------------------------------------------------------------

    def do_extract_traces(
        self,
        log: Union[EventLog, EventStream, pd.DataFrame],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[LabelTrace]:
        """Project a pm4py log onto label sequences wrapped with sentinels.

        Each trace becomes ``[START_LABEL, *activity_labels, END_LABEL]``
        so the resulting BPMN has a single source and a single sink.
        Subclasses that need richer per-event data (e.g. lifecycle phases)
        override this method.
        """
        parameters = parameters or {}
        activity_key = exec_utils.get_param_value(
            constants.PARAMETER_CONSTANT_ACTIVITY_KEY,
            parameters,
            xes_util.DEFAULT_NAME_KEY,
        )
        event_log = (
            log
            if isinstance(log, EventLog)
            else log_conversion.apply(
                log, variant=log_conversion.Variants.TO_EVENT_LOG
            )
        )
        traces: List[LabelTrace] = []
        for trace in event_log:
            labels: LabelTrace = []
            for ev in trace:
                if activity_key in ev:
                    labels.append(str(ev[activity_key]))
            if labels:
                traces.append([START_LABEL, *labels, END_LABEL])
        return traces

    # ------------------------------------------------------------------
    # Phase 1 — DFG + loop discovery
    # ------------------------------------------------------------------

    def do_dfg_discovery(
        self,
        traces: List[Any],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[DFG, LoopInfo]:
        return ClassicDFGDiscoverer.apply(traces, parameters)

    # ------------------------------------------------------------------
    # Phase 2 — concurrency
    # ------------------------------------------------------------------

    def do_concurrency(
        self,
        dfg: DFG,
        traces: Optional[List[Any]],
        loops: LoopInfo,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ConcurrencyResult:
        return ClassicConcurrencyOracle.apply(dfg, traces, loops, parameters)

    # ------------------------------------------------------------------
    # Phase 3 — filter the pruned DFG
    # ------------------------------------------------------------------

    def do_filter(
        self,
        pdfg: DFG,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> FilterResult:
        return MaxMinFilterer.apply(pdfg, parameters)

    # ------------------------------------------------------------------
    # Phase 4 — initialise working BPMN
    # ------------------------------------------------------------------

    def do_build_initial_bpmn(
        self,
        filtered: FilterResult,
        concurrency: ConcurrencyResult,
        loops: LoopInfo,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> WorkingGraph:
        return ClassicBPMNInitializer.apply(
            filtered, concurrency, loops, parameters
        )

    # ------------------------------------------------------------------
    # Phase 5 — split discovery
    # ------------------------------------------------------------------

    def do_discover_splits(
        self,
        wg: WorkingGraph,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        ClassicSplitsDiscoverer.apply(wg, parameters)

    # ------------------------------------------------------------------
    # Phase 6 — join discovery
    # ------------------------------------------------------------------

    def do_discover_joins(
        self,
        wg: WorkingGraph,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        SeseJoinsDiscoverer.apply(wg, parameters)

    # ------------------------------------------------------------------
    # Phase 7 — OR handling
    # ------------------------------------------------------------------

    def do_minimize_or_joins(
        self,
        wg: WorkingGraph,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        ClassicOrJoinMinimizer.apply(wg, parameters)

    def or_handling_is_mandatory(self) -> bool:
        """Whether :meth:`do_minimize_or_joins` runs unconditionally.

        For classic Split Miner the OR-join minimisation is an optional
        post-step governed by the ``minimize_or_joins`` flag. For Split
        Miner 2.0 the OR handling (inclusive joins left in place plus the
        OR-split heuristic) is an intrinsic stage of the reference
        ``replaceIORs`` step, so that variant forces it on regardless of
        the flag.
        """
        return False

    # ------------------------------------------------------------------
    # Phase 8 — export
    # ------------------------------------------------------------------

    def do_export_bpmn(
        self,
        wg: WorkingGraph,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> BPMN:
        bpmn = ClassicBPMNExporter.apply(wg, parameters)
        return reduction.apply(
            bpmn, {reduction.Parameters.COLLAPSE_GATEWAYS: True}
        )

    # ------------------------------------------------------------------
    # Pipeline driver
    # ------------------------------------------------------------------

    def apply(
        self,
        log: Union[EventLog, EventStream, pd.DataFrame, DFG, str],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> BPMN:
        parameters = parameters or {}

        if isinstance(log, str):
            # A file path was supplied directly — read it via pm4py so
            # both ``classic`` and ``sm2`` variants accept paths.
            from pm4py.objects.log.importer.xes import importer as xes_importer

            log = xes_importer.apply(log)

        if isinstance(log, dict):
            # Pre-computed DFG path — phases 0 and 1 are bypassed.
            dfg = log
            loops = LoopInfo(
                self_loops={a for (a, b) in dfg.keys() if a == b},
            )
            traces: List[Any] = []
        else:
            traces = self.do_extract_traces(log, parameters)
            if not traces:
                raise ValueError(
                    "Cannot run Split Miner: the supplied log is empty"
                )
            dfg, loops = self.do_dfg_discovery(traces, parameters)

        dfg_no_self = strip_self_loops(dfg)
        conc = self.do_concurrency(dfg_no_self, traces, loops, parameters)
        filt = self.do_filter(conc.pdfg, parameters)
        wg = self.do_build_initial_bpmn(filt, conc, loops, parameters)

        self.do_discover_splits(wg, parameters)
        self.do_discover_joins(wg, parameters)

        or_minimise = exec_utils.get_param_value(
            Parameters.OR_MINIMISE, parameters, DEFAULT_OR_MINIMISE
        )
        if or_minimise or self.or_handling_is_mandatory():
            self.do_minimize_or_joins(wg, parameters)

        return self.do_export_bpmn(wg, parameters)
