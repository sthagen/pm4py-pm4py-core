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
from enum import Enum

from pm4py.objects.bpmn.obj import BPMN
from pm4py.util import exec_utils


class Parameters(Enum):
    COLLAPSE_GATEWAYS = "collapse_gateways"


# Gateway classes for which two consecutive same-type gateways can be
# merged without changing the language of the model. XOR and AND are
# associative (``XOR(a, XOR(b, c)) = XOR(a, b, c)`` and likewise for
# AND), so flattening a nested same-type split/join preserves the set of
# accepted traces. Inclusive (OR) gateways are intentionally excluded to
# keep the merge provably language preserving.
_MERGEABLE_GATEWAYS = (BPMN.ExclusiveGateway, BPMN.ParallelGateway)


def _edge_maps(bpmn_graph):
    """Return ``(outgoing, incoming)`` flow maps keyed by node.

    Both maps associate a node with the *set* of sequence flows leaving
    (resp. entering) it. They are rebuilt from scratch whenever the graph
    is mutated so callers never act on stale adjacency.
    """
    outgoing = {}
    incoming = {}
    for flow in bpmn_graph.get_flows():
        source = flow.get_source()
        target = flow.get_target()
        outgoing.setdefault(source, set()).add(flow)
        incoming.setdefault(target, set()).add(flow)
    return outgoing, incoming


def reduce_xor_gateways(bpmn_graph, parameters=None):
    """
    Reduces the number of XOR gateways in the diagram

    Parameters
    ------------
    bpmn_graph
        BPMN graph
    parameters
        Parameters

    Returns
    ------------
    bpmn_graph
        (possibly reduced) BPMN graph
    """
    if parameters is None:
        parameters = {}

    changed = True
    while changed:
        changed = False
        outgoing_edges = None
        incoming_edges = None
        outgoing_edges = {}
        incoming_edges = {}

        for flow in bpmn_graph.get_flows():
            source = flow.get_source()
            target = flow.get_target()

            if source not in outgoing_edges:
                outgoing_edges[source] = set()
            outgoing_edges[source].add(flow)

            if target not in incoming_edges:
                incoming_edges[target] = set()
            incoming_edges[target].add(flow)

        nodes = list(bpmn_graph.get_nodes())
        for node in nodes:
            if isinstance(node, BPMN.ExclusiveGateway):
                if (
                    node in outgoing_edges
                    and node in incoming_edges
                    and len(outgoing_edges[node]) == 1
                    and len(incoming_edges[node]) == 1
                ):
                    changed = True
                    source_node = None
                    target_node = None
                    for flow in incoming_edges[node]:
                        source_node = flow.get_source()
                        if flow in bpmn_graph.get_flows():
                            bpmn_graph.remove_flow(flow)
                    for flow in outgoing_edges[node]:
                        target_node = flow.get_target()
                        if flow in bpmn_graph.get_flows():
                            bpmn_graph.remove_flow(flow)
                    if node in bpmn_graph.get_nodes():
                        bpmn_graph.remove_node(node)
                    bpmn_graph.add_flow(
                        BPMN.SequenceFlow(source_node, target_node)
                    )
                    break

    return bpmn_graph


def remove_trivial_gateways(bpmn_graph, parameters=None):
    """Remove gateways with exactly one incoming and one outgoing flow.

    A gateway with a single input and a single output neither branches
    nor synchronises anything, so it can be spliced out and its
    predecessor connected straight to its successor. This holds for every
    gateway type (XOR, AND and OR alike), hence the reduction is always
    language preserving.
    """
    if parameters is None:
        parameters = {}

    changed = True
    while changed:
        changed = False
        outgoing, incoming = _edge_maps(bpmn_graph)
        for node in list(bpmn_graph.get_nodes()):
            if not isinstance(node, BPMN.Gateway):
                continue
            ins = incoming.get(node, set())
            outs = outgoing.get(node, set())
            if len(ins) != 1 or len(outs) != 1:
                continue
            in_flow = next(iter(ins))
            out_flow = next(iter(outs))
            source = in_flow.get_source()
            target = out_flow.get_target()
            bpmn_graph.remove_flow(in_flow)
            bpmn_graph.remove_flow(out_flow)
            bpmn_graph.remove_node(node)
            # Do not introduce a self-loop if the gateway sat on a
            # one-node cycle; just drop it in that degenerate case.
            if source is not target:
                bpmn_graph.add_flow(BPMN.SequenceFlow(source, target))
            changed = True
            break

    return bpmn_graph


def collapse_split_gateways(bpmn_graph, parameters=None):
    """Merge a split gateway into a same-type successor split gateway.

    When a split gateway ``g`` has an outgoing flow to another split
    gateway ``s`` of the same type and ``s`` has no other predecessor
    than ``g``, the nesting ``g -> s`` is flattened: ``g`` absorbs every
    outgoing branch of ``s`` and ``s`` is removed. This mirrors the
    consecutive-split collapse performed by the reference Split Miner
    implementation and is restricted to XOR/AND gateways so it stays
    language preserving.
    """
    if parameters is None:
        parameters = {}

    changed = True
    while changed:
        changed = False
        outgoing, incoming = _edge_maps(bpmn_graph)
        for g in list(bpmn_graph.get_nodes()):
            if not isinstance(g, _MERGEABLE_GATEWAYS):
                continue
            merged = False
            for out_flow in list(outgoing.get(g, set())):
                succ = out_flow.get_target()
                if type(succ) is not type(g):
                    continue
                succ_in = incoming.get(succ, set())
                # the successor split must be fed exclusively by g
                if any(f.get_source() is not g for f in succ_in):
                    continue
                # g absorbs the successor's outgoing branches
                for sf in list(outgoing.get(succ, set())):
                    tgt = sf.get_target()
                    bpmn_graph.remove_flow(sf)
                    if tgt is not g:
                        bpmn_graph.add_flow(BPMN.SequenceFlow(g, tgt))
                for sf in list(succ_in):
                    bpmn_graph.remove_flow(sf)
                bpmn_graph.remove_node(succ)
                merged = True
                changed = True
                break
            if merged:
                break

    return bpmn_graph


def collapse_join_gateways(bpmn_graph, parameters=None):
    """Merge a join gateway into a same-type predecessor join gateway.

    Dual of :func:`collapse_split_gateways`. When a join gateway ``g`` is
    fed by another join gateway ``p`` of the same type and ``p``'s only
    successor is ``g``, the nesting ``p -> g`` is flattened: ``g`` absorbs
    every incoming flow of ``p`` and ``p`` is removed. Restricted to
    XOR/AND gateways to remain language preserving.
    """
    if parameters is None:
        parameters = {}

    changed = True
    while changed:
        changed = False
        outgoing, incoming = _edge_maps(bpmn_graph)
        for g in list(bpmn_graph.get_nodes()):
            if not isinstance(g, _MERGEABLE_GATEWAYS):
                continue
            merged = False
            for in_flow in list(incoming.get(g, set())):
                pred = in_flow.get_source()
                if type(pred) is not type(g):
                    continue
                pred_out = outgoing.get(pred, set())
                # the predecessor join must feed only g
                if any(f.get_target() is not g for f in pred_out):
                    continue
                # g absorbs the predecessor's incoming flows
                for pf in list(incoming.get(pred, set())):
                    src = pf.get_source()
                    bpmn_graph.remove_flow(pf)
                    if src is not g:
                        bpmn_graph.add_flow(BPMN.SequenceFlow(src, g))
                for pf in list(pred_out):
                    bpmn_graph.remove_flow(pf)
                bpmn_graph.remove_node(pred)
                merged = True
                changed = True
                break
            if merged:
                break

    return bpmn_graph


def collapse_gateways(bpmn_graph, parameters=None):
    """Flatten nested same-type gateways and drop trivial ones.

    Splits and joins are collapsed in alternation (split, join, split,
    join) because collapsing one side can expose new opportunities on the
    other; a final pass removes any single-in/single-out gateway left
    behind. All steps preserve the language of the model.
    """
    if parameters is None:
        parameters = {}

    collapse_split_gateways(bpmn_graph, parameters=parameters)
    collapse_join_gateways(bpmn_graph, parameters=parameters)
    collapse_split_gateways(bpmn_graph, parameters=parameters)
    collapse_join_gateways(bpmn_graph, parameters=parameters)
    remove_trivial_gateways(bpmn_graph, parameters=parameters)
    return bpmn_graph


def apply(bpmn_graph, parameters=None):
    """
    Reduce the complexity of a BPMN graph by removing useless elements

    Parameters
    ------------
    bpmn_graph
        BPMN graph
    parameters
        Parameters of the algorithm, including:
        - Parameters.COLLAPSE_GATEWAYS: when set to ``True``, also flatten
          nested same-type (XOR/AND) split and join gateways. Disabled by
          default so existing callers keep the conservative behaviour.

    Returns
    ------------
    bpmn_graph
        (possibly reduced) BPMN graph
    """
    if parameters is None:
        parameters = {}

    bpmn_graph = reduce_xor_gateways(bpmn_graph, parameters=parameters)

    if exec_utils.get_param_value(
        Parameters.COLLAPSE_GATEWAYS, parameters, False
    ):
        bpmn_graph = collapse_gateways(bpmn_graph, parameters=parameters)

    return bpmn_graph
