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
"""BPMN export for Split Miner 2.0.

Differs from the classic exporter in how level-1 (self) loops are
rendered. Classic Split Miner expands every self-looping task into an
explicit XOR-join / XOR-split pair with a back edge; Split Miner 2.0
keeps the task compact and marks it as a looping activity (the Java side
attaches ``standardLoopCharacteristics``), adding no extra gateways.
"""
from typing import Any, Dict, Optional

from pm4py.algo.discovery.split_miner.bpmn_export.abc import BPMNExporter
from pm4py.algo.discovery.split_miner.bpmn_export.classic import _make_node
from pm4py.algo.discovery.split_miner.dtypes.log import END_LABEL, START_LABEL
from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.objects.bpmn.obj import BPMN


class LifecycleBPMNExporter(BPMNExporter):
    """Materialize the BPMN, keeping self-loops as marked activities."""

    @classmethod
    def apply(
        cls,
        wg: WorkingGraph,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> BPMN:
        bpmn = BPMN()
        node_map: Dict[str, BPMN.BPMNNode] = {}
        for nid, n in wg.nodes.items():
            bnode = _make_node(n.kind, n.label, nid)
            bpmn.add_node(bnode)
            node_map[nid] = bnode

        for src, tgt in wg.edges():
            bpmn.add_flow(BPMN.SequenceFlow(node_map[src], node_map[tgt]))

        # Mark self-looping tasks (no XOR expansion). The Java side
        # serializes this as ``standardLoopCharacteristics``; pm4py's
        # BPMN exporter has no equivalent, so the attribute is purely
        # informational for downstream consumers of the BPMN object.
        for task_id in wg.self_loops:
            if task_id in {START_LABEL, END_LABEL}:
                continue
            node = node_map.get(task_id)
            if node is not None:
                setattr(node, "_sm_looped", True)
        return bpmn
