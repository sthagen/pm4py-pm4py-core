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
"""Convert :class:`WorkingGraph` into a pm4py :class:`BPMN`.

Self-loops detected during the loops phase are reattached here by
wrapping the looped task with an XOR-join (predecessor side) and an
XOR-split (successor side) that connects back to the join.
"""
from typing import Any, Dict, Optional

from pm4py.algo.discovery.split_miner.bpmn_export.abc import BPMNExporter
from pm4py.algo.discovery.split_miner.dtypes.log import END_LABEL, START_LABEL
from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.objects.bpmn.obj import BPMN


def _make_node(kind: str, label: str, node_id: str) -> BPMN.BPMNNode:
    if kind == "start":
        return BPMN.StartEvent(id=node_id, name="")
    if kind == "end":
        return BPMN.EndEvent(id=node_id, name="")
    if kind == "task":
        return BPMN.Task(id=node_id, name=label)
    if kind == "xor":
        return BPMN.ExclusiveGateway(id=node_id, name="")
    if kind == "and":
        return BPMN.ParallelGateway(id=node_id, name="")
    if kind == "or":
        return BPMN.InclusiveGateway(id=node_id, name="")
    raise ValueError(f"Unknown node kind: {kind}")


class ClassicBPMNExporter(BPMNExporter):
    """Materialise the pm4py :class:`BPMN` from the working graph."""

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
            bpmn.add_flow(
                BPMN.SequenceFlow(node_map[src], node_map[tgt])
            )

        # Sort to keep self-loop attachment order independent of
        # hash randomization; semantically the model is the same, but
        # node/flow ids and rendering order are then reproducible.
        for task_id in sorted(wg.self_loops, reverse=True):
            if task_id not in node_map:
                continue
            if task_id in {START_LABEL, END_LABEL}:
                continue
            cls._attach_self_loop(bpmn, node_map, task_id)
        return bpmn

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _attach_self_loop(
        bpmn: BPMN,
        node_map: Dict[str, BPMN.BPMNNode],
        task_id: str,
    ) -> None:
        task_node = node_map[task_id]
        in_flows = [
            f for f in bpmn.get_flows() if f.get_target() is task_node
        ]
        out_flows = [
            f for f in bpmn.get_flows() if f.get_source() is task_node
        ]

        loop_join = BPMN.ExclusiveGateway(id=f"{task_id}__loop_join", name="")
        loop_split = BPMN.ExclusiveGateway(id=f"{task_id}__loop_split", name="")
        bpmn.add_node(loop_join)
        bpmn.add_node(loop_split)

        for f in in_flows:
            src = f.get_source()
            bpmn.remove_flow(f)
            bpmn.add_flow(BPMN.SequenceFlow(src, loop_join))
        for f in out_flows:
            tgt = f.get_target()
            bpmn.remove_flow(f)
            bpmn.add_flow(BPMN.SequenceFlow(loop_split, tgt))

        bpmn.add_flow(BPMN.SequenceFlow(loop_join, task_node))
        bpmn.add_flow(BPMN.SequenceFlow(task_node, loop_split))
        bpmn.add_flow(BPMN.SequenceFlow(loop_split, loop_join))
