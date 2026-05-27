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
"""Initial BPMN construction from a filtered PDFG.

Sentinel start / end labels in the filtered DFG become the BPMN start
and end events; every other node becomes a task. Concurrency and self-
loop metadata is attached to the working graph for the later phases.
"""
from typing import Any, Dict, Optional, Set

from pm4py.algo.discovery.split_miner.bpmn_init.abc import BPMNInitializer
from pm4py.algo.discovery.split_miner.dtypes.concurrency import (
    ConcurrencyResult,
)
from pm4py.algo.discovery.split_miner.dtypes.filtering import FilterResult
from pm4py.algo.discovery.split_miner.dtypes.log import END_LABEL, START_LABEL
from pm4py.algo.discovery.split_miner.dtypes.loops import LoopInfo
from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph


class ClassicBPMNInitializer(BPMNInitializer):
    """Build a fresh working graph from a filtered PDFG and metadata."""

    @classmethod
    def apply(
        cls,
        filtered: FilterResult,
        concurrency: ConcurrencyResult,
        loops: LoopInfo,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> WorkingGraph:
        wg = WorkingGraph()

        # The filtered edge set is a Python ``set``; iterating it directly
        # would expose ``PYTHONHASHSEED``-dependent ordering and make the
        # whole pipeline non-deterministic across processes. Sort once
        # here so every downstream phase sees a stable order of edges
        # and node-insertion.
        sorted_edges = sorted(filtered.edges, reverse=True)

        nodes: Set[str] = set()
        for a, b in sorted_edges:
            nodes.add(a)
            nodes.add(b)
        nodes.add(filtered.source)
        nodes.add(filtered.sink)

        for label in sorted(nodes, reverse=True):
            if label == START_LABEL:
                wg.add_node("start", label="start", node_id=label)
                wg.start_id = label
            elif label == END_LABEL:
                wg.add_node("end", label="end", node_id=label)
                wg.end_id = label
            else:
                wg.add_node("task", label=label, node_id=label)

        for a, b in sorted_edges:
            wg.add_edge(a, b)

        wg.concurrency = set(concurrency.concurrent_pairs)
        wg.self_loops = set(loops.self_loops)
        return wg
