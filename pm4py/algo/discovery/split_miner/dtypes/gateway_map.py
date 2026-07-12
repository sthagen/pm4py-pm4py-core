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
"""Inclusive-OR-join replacement (port of the reference ``GatewayMap``).

Split Miner's final step (``replaceIORs`` with the ``replace inclusive
gateways`` option enabled) rewrites every inclusive (OR) join into the
behaviourally equivalent exclusive (XOR) or parallel (AND) join. The
decision is made on a *gateway map* — a graph whose nodes are the
gateways of the BPMN model and whose edges are the task-paths connecting
them.

For every OR-join, processed shallowest-first in a breadth-first depth
order, the algorithm walks backwards towards the join's dominator. If the
incoming branches are mutually exclusive (``check_xor``) the join becomes
an XOR; otherwise it becomes an AND and *token generators* (auxiliary AND
gateways with synthetic flows) are inserted so the parallel join can
always synchronise.
"""
from typing import Dict, List, Optional, Set

import networkx as nx

from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph


# Gateway kinds as used by the WorkingGraph.
_XOR = "xor"
_AND = "and"
_OR = "or"
_GATE_KINDS = {_XOR, _AND, _OR}

# Sentinels for the fake entry/exit gateways of the map.
_FAKE_ENTRY = "__gm_entry__"
_FAKE_EXIT = "__gm_exit__"


class _Flow:
    """A gateway-map edge: a task-path between two gateways.

    ``first`` is the node immediately after ``src`` on the path, ``last``
    the node immediately before ``tgt`` (so the real BPMN edge entering a
    join is ``last -> tgt``). ``loop`` marks edges that close a cycle.
    """

    __slots__ = ("id", "src", "tgt", "first", "last", "loop")

    def __init__(self, fid, src, tgt, first, last):
        self.id = fid
        self.src = src
        self.tgt = tgt
        self.first = first
        self.last = last
        self.loop = False

    def __repr__(self):
        return f"F{self.id}({self.src}->{self.tgt}{'*' if self.loop else ''})"


def _is_gateway(wg: WorkingGraph, node: str) -> bool:
    n = wg.nodes.get(node)
    return n is not None and n.kind in _GATE_KINDS


# ----------------------------------------------------------------------
# WorkingGraph pre-processing
# ----------------------------------------------------------------------


def _remove_join_split(wg: WorkingGraph) -> None:
    """Split every gateway that both joins and splits.

    A gateway with more than one incoming *and* more than one outgoing
    flow is separated into a pure join (keeping the incoming flows, typed
    inclusive) feeding a pure split (keeping the outgoing flows, original
    type). Mirrors ``DiagramHandler.removeJoinSplit``.
    """
    for gid in list(wg.nodes.keys()):
        node = wg.nodes.get(gid)
        if node is None or node.kind not in _GATE_KINDS:
            continue
        ins = list(wg.in_edges.get(gid, []))
        outs = list(wg.out_edges.get(gid, []))
        if len(ins) > 1 and len(outs) > 1:
            split = wg.add_node(node.kind, label=node.kind)
            for t in outs:
                wg.remove_edge(gid, t)
                wg.add_edge(split, t)
            wg.add_edge(gid, split)
            node.kind = _OR
            node.label = _OR


# ----------------------------------------------------------------------
# Gateway map
# ----------------------------------------------------------------------


class GatewayMap:
    def __init__(self, wg: WorkingGraph, apply_hagen: bool = True):
        self.wg = wg
        self.apply_hagen = apply_hagen
        self.fid = 0
        self.gid = 0

        self.gateways: Set[str] = set()
        self.flows: Set[_Flow] = set()
        self.incomings: Dict[str, Set[_Flow]] = {}
        self.outgoings: Dict[str, Set[_Flow]] = {}
        self.successors: Dict[str, Set[str]] = {}
        self.predecessors: Dict[str, Set[str]] = {}

        self.entry: Optional[str] = None
        self.exit: Optional[str] = None

        self.gates_depth: Dict[str, int] = {}
        self.loop_joins: Set[str] = set()
        self.idom: Dict[str, str] = {}
        self.ior_hierarchy: List[str] = []

    # -- map building -------------------------------------------------

    def _add_gateway(self, gid: str) -> None:
        self.gateways.add(gid)
        self.incomings.setdefault(gid, set())
        self.outgoings.setdefault(gid, set())
        self.successors.setdefault(gid, set())
        self.predecessors.setdefault(gid, set())

    def _add_flow(self, src, tgt, first, last) -> _Flow:
        self.fid += 1
        flow = _Flow(self.fid, src, tgt, first, last)
        self.flows.add(flow)
        self.outgoings[src].add(flow)
        self.incomings[tgt].add(flow)
        self.successors[src].add(tgt)
        self.predecessors[tgt].add(src)
        return flow

    def _remove_flow(self, flow: _Flow) -> None:
        self.flows.discard(flow)
        self.outgoings[flow.src].discard(flow)
        self.incomings[flow.tgt].discard(flow)
        # recompute successor/predecessor membership
        if not any(f.tgt == flow.tgt for f in self.outgoings[flow.src]):
            self.successors[flow.src].discard(flow.tgt)
            self.predecessors[flow.tgt].discard(flow.src)

    def _change_flow_tgt(self, flow: _Flow, new_tgt: str) -> _Flow:
        first = new_tgt if flow.first == flow.tgt else flow.first
        nf = self._add_flow(flow.src, new_tgt, first, flow.last)
        if flow.loop:
            nf.loop = True
        self._remove_flow(flow)
        return nf

    def _walk_to_gateway(self, src_gate: str, first: str):
        """Follow a task chain from ``first`` until a gateway or the sink.

        Returns ``(reached, last)`` where ``reached`` is the next gateway
        (or the WorkingGraph sink) and ``last`` the node just before it.
        """
        wg = self.wg
        prev = src_gate
        cur = first
        while (
            not _is_gateway(wg, cur)
            and cur != wg.end_id
            and len(wg.out_edges.get(cur, [])) == 1
        ):
            prev = cur
            cur = wg.out_edges[cur][0]
        return cur, prev

    def build(self) -> bool:
        wg = self.wg
        _remove_join_split(wg)

        for gid, node in wg.nodes.items():
            if node.kind in _GATE_KINDS:
                self._add_gateway(gid)

        if not self.gateways:
            return False

        # First gateway reachable from the source.
        cur = wg.start_id
        while not _is_gateway(wg, cur) and len(wg.out_edges.get(cur, [])) == 1:
            cur = wg.out_edges[cur][0]
        if not _is_gateway(wg, cur):
            return False
        first_gate = cur
        self.entry = first_gate

        exit_gate = None
        to_visit = [first_gate]
        visited = {wg.end_id}
        seen = set()
        while to_visit:
            entry = to_visit.pop(0)
            if entry in seen:
                continue
            seen.add(entry)
            visited.add(entry)
            for child in list(wg.out_edges.get(entry, [])):
                reached, last = self._walk_to_gateway(entry, child)
                if _is_gateway(wg, reached):
                    self._add_flow(entry, reached, child, last)
                if reached == wg.end_id:
                    exit_gate = entry
                if reached not in to_visit and reached not in visited:
                    to_visit.append(reached)

        if exit_gate is None:
            return False
        self.exit = exit_gate

        # Fake entry/exit so the dominator computation has a single root.
        self._add_gateway(_FAKE_ENTRY)
        self._add_gateway(_FAKE_EXIT)
        self._add_flow(_FAKE_ENTRY, first_gate, first_gate, _FAKE_ENTRY)
        self._add_flow(exit_gate, _FAKE_EXIT, _FAKE_EXIT, exit_gate)
        self.entry = _FAKE_ENTRY
        self.exit = _FAKE_EXIT

        self._detect_loops()
        self._normalize_loop_joins()
        self._populate_ior_hierarchy()
        self._generate_dominators()
        return True

    # -- loops --------------------------------------------------------

    def _detect_loops(self) -> None:
        """Mark map flows that close a cycle (loop edges).

        Faithful port of the reference ``detectLoops``/``exploreLoops``: a
        fix-point DFS that classifies each flow as forward or loop. A node
        is only *settled* once all its incoming flows have been traversed;
        otherwise it is re-queued (added back to ``unvisited``) so it is
        re-explored when reached again. The recursion's return value marks
        whether the explored subtree can *only* go backward
        (``loop and not forward``); an edge into such a subtree is itself a
        loop edge. A flow is a true loop only if it was *never* classified
        as a forward edge.
        """
        unvisited: Set[str] = set(self.outgoings.keys())
        visiting: Set[str] = set()
        visited_gates: Dict[str, bool] = {}
        visited_flows: Set[_Flow] = set()
        loop_edges: Set[_Flow] = set()
        forward_edges: Set[_Flow] = set()

        def explore(entry: str) -> bool:
            loop_edge = False
            forward_edge = False
            unvisited.discard(entry)
            visiting.add(entry)
            if entry == self.exit:
                forward_edge = True
            for oflow in sorted(self.outgoings.get(entry, set()),
                                key=lambda f: f.id):
                visited_flows.add(oflow)
                nxt = oflow.tgt
                if nxt in unvisited:
                    if explore(nxt):
                        loop_edge = True
                        loop_edges.add(oflow)
                    else:
                        forward_edge = True
                        forward_edges.add(oflow)
                elif nxt in visiting:
                    loop_edge = True
                    loop_edges.add(oflow)
                elif nxt in visited_gates:
                    if visited_gates[nxt]:
                        loop_edge = True
                        loop_edges.add(oflow)
                    else:
                        forward_edge = True
                        forward_edges.add(oflow)
            visiting.discard(entry)
            fully = all(
                iflow in visited_flows
                for iflow in self.incomings.get(entry, set())
            )
            if fully:
                visited_gates[entry] = loop_edge and not forward_edge
            else:
                unvisited.add(entry)
            return loop_edge and not forward_edge

        import sys
        old = sys.getrecursionlimit()
        sys.setrecursionlimit(max(old, len(self.gateways) * 8 + 100))
        try:
            explore(self.entry)
        finally:
            sys.setrecursionlimit(old)

        for flow in loop_edges:
            if flow not in forward_edges:
                flow.loop = True

    def _normalize_loop_joins(self) -> None:
        """Separate loop merges from forward merges at loop-joins.

        A join receiving at least one loop edge is a loop-join. If it has
        a single forward branch it is recorded as-is and, if inclusive,
        demoted to exclusive. If it has *several* forward branches the
        join is split (as in the reference) into a forward XOR-join that
        feeds a new exclusive loop-join; the loop back-edges and the
        forward result are merged at the loop-join. This keeps the
        gateway map's dominator structure, which is what the
        inclusive-join replacement relies on.
        """
        self.loop_joins = set()
        for join in sorted(self.gateways):
            ins = self.incomings.get(join, set())
            if len(ins) <= 1:
                continue
            ins_ord = sorted(ins, key=lambda f: f.id)
            loops = [f for f in ins_ord if f.loop]
            fwds = [f for f in ins_ord if not f.loop]
            if not loops:
                continue
            if len(fwds) > 1:
                loop_join = self.wg.add_node(_XOR, label=_XOR)
                self._add_gateway(loop_join)
                # loop sources on the WorkingGraph side
                srcs = {f.last for f in loops}
                # map: the join's outgoing flow now leaves the loop-join,
                # and a new flow connects join -> loop-join
                for of in sorted(self.outgoings.get(join, set()),
                                 key=lambda f: f.id):
                    self._change_flow_src(of, loop_join)
                self._add_flow(join, loop_join, loop_join, join)
                # map: loop edges are redirected to the loop-join
                for f in loops:
                    self._change_flow_tgt(f, loop_join)
                # WorkingGraph: move the join's successors onto the
                # loop-join and wire join -> loop-join
                for t in list(self.wg.out_edges.get(join, [])):
                    self.wg.remove_edge(join, t)
                    self.wg.add_edge(loop_join, t)
                self.wg.add_edge(join, loop_join)
                # WorkingGraph: move the loop back-edges onto the loop-join
                for s in list(self.wg.in_edges.get(join, [])):
                    if s in srcs:
                        self.wg.remove_edge(s, join)
                        self.wg.add_edge(s, loop_join)
                self.loop_joins.add(loop_join)
                continue
            self.loop_joins.add(join)
            node = self.wg.nodes.get(join)
            if node is not None and node.kind == _OR:
                node.kind = _XOR
                node.label = _XOR

    # -- hierarchy + dominators --------------------------------------

    def _populate_ior_hierarchy(self) -> None:
        # Longest-path depth from the entry (matching the reference): a
        # node is re-queued whenever a deeper path reaches it; loop joins
        # are never re-deepened nor re-queued once seen, so cycles
        # terminate. This is the correct depth for the inclusive-join
        # replacement.
        depth: Dict[str, int] = {self.entry: 0}
        to_visit = [self.entry]
        visited = {self.entry}
        while to_visit:
            g = to_visit.pop(0)
            sd = depth[g] + 1
            for nxt in sorted(self.successors.get(g, set())):
                bumped = False
                if nxt not in depth:
                    depth[nxt] = sd
                    bumped = True
                elif depth[nxt] < sd and nxt not in self.loop_joins:
                    depth[nxt] = sd
                    bumped = True
                if nxt in visited and nxt in self.loop_joins:
                    continue
                if nxt in visited and not bumped:
                    continue
                to_visit.append(nxt)
                visited.add(nxt)
        self.gates_depth = depth

        # Inclusive joins ordered shallowest-first.
        iors = [
            g
            for g in depth
            if self.wg.nodes.get(g) is not None
            and self.wg.nodes[g].kind == _OR
        ]
        iors.sort(key=lambda g: (depth[g], g))
        self.ior_hierarchy = iors

    def _generate_dominators(self) -> None:
        g = nx.DiGraph()
        g.add_nodes_from(sorted(self.gateways))
        for src in sorted(self.gateways):
            for tgt in sorted(self.successors.get(src, set())):
                g.add_edge(src, tgt)
        # immediate_dominators needs every node reachable from the root.
        reach = nx.descendants(g, self.entry) | {self.entry}
        sub = g.subgraph(reach)
        self.idom = nx.immediate_dominators(sub, self.entry)

    def _dominator(self, ior: str) -> Optional[str]:
        return self.idom.get(ior)

    # -- IOR replacement ---------------------------------------------

    def detect_and_replace_iors(self) -> None:
        # process shallowest-first; recompute hierarchy lazily because
        # depths do not change as we only retype gateways
        pending = list(self.ior_hierarchy)
        for ior in pending:
            node = self.wg.nodes.get(ior)
            if node is None or node.kind != _OR:
                continue
            dominator = self._dominator(ior)
            if dominator is None:
                continue

            to_visit: Dict[str, Set[str]] = {}
            visited_gates: Dict[str, Set[str]] = {}
            visited_flows: Dict[str, Set[_Flow]] = {}
            loop = False

            for igmf in sorted(self.incomings.get(ior, set()),
                               key=lambda f: f.id):
                if igmf.loop:
                    node.kind = _XOR
                    node.label = _XOR
                    loop = True
                    break
                last = igmf.last
                # Mirror the reference: only insert a per-incoming XOR when a
                # real edge last -> ior exists in the diagram. The fake-entry
                # flow (``last`` is the map's entry sentinel, with no diagram
                # edge) is left untouched instead of crashing.
                if last not in self.wg.out_edges or ior not in \
                        self.wg.out_edges.get(last, []):
                    continue
                self.wg.remove_edge(last, ior)
                xor = self.wg.add_node(_XOR, label=_XOR)
                self.wg.add_edge(last, xor)
                self.wg.add_edge(xor, ior)
                self._add_gateway(xor)
                self._add_flow(xor, ior, ior, xor)
                self._change_flow_tgt(igmf, xor)
                to_visit[xor] = {xor}
                visited_gates[xor] = {dominator}
                visited_flows[xor] = set()

            if loop:
                continue

            ands: Set[str] = set()
            ior_type = self._replace_ior(
                dominator,
                self.gates_depth.get(ior, 0),
                to_visit,
                visited_gates,
                visited_flows,
                set(),
                {},
                ands,
            )
            node.kind = ior_type
            node.label = ior_type

        _remove_trivial_gateways(self.wg)

    def _replace_ior(
        self,
        dominator: str,
        ior_depth: int,
        to_visit: Dict[str, Set[str]],
        visited_gates: Dict[str, Set[str]],
        visited_flows: Dict[str, Set[_Flow]],
        dom_frontier: Set[_Flow],
        loop_injections: Dict[str, Set[_Flow]],
        ands: Set[str],
    ) -> str:
        empty = True
        for xor in sorted(to_visit.keys()):
            tmp: Set[str] = set()
            for g in sorted(to_visit[xor]):
                for igmf in sorted(self.incomings.get(g, set()),
                                   key=lambda f: f.id):
                    src = igmf.src
                    if igmf in visited_flows[xor]:
                        continue
                    visited_flows[xor].add(igmf)
                    if src == dominator:
                        dom_frontier.add(igmf)
                    if src in self.loop_joins and src not in loop_injections:
                        loop_injections[src] = set()
                        for injection in sorted(
                            self.incomings.get(src, set()), key=lambda f: f.id
                        ):
                            isrc = injection.src
                            if (
                                isrc in self.gates_depth
                                and self.gates_depth[isrc] <= ior_depth
                            ):
                                continue
                            loop_injections[src].add(injection)
                    if src in visited_gates[xor] or (
                        src in self.gates_depth
                        and self.gates_depth[src] > ior_depth
                    ):
                        continue
                    visited_gates[xor].add(src)
                    snode = self.wg.nodes.get(src)
                    if (
                        snode is not None
                        and snode.kind == _AND
                        and len(self.outgoings.get(src, set())) > 1
                    ):
                        ands.add(src)
                    tmp.add(src)
                    empty = False
            to_visit[xor] = tmp

        if not empty:
            return self._replace_ior(
                dominator,
                ior_depth,
                to_visit,
                visited_gates,
                visited_flows,
                dom_frontier,
                loop_injections,
                ands,
            )

        if self._check_xor(visited_gates, visited_flows, ands):
            return _XOR

        # Build single-token generators for the parallel rewrite.
        changes: Dict[_Flow, _SingleTokenGen] = {}
        for xor in sorted(visited_gates):
            for g in sorted(visited_gates[xor]):
                gnode = self.wg.nodes.get(g)
                if (
                    gnode is not None and gnode.kind == _AND
                ) or len(self.outgoings.get(g, set())) == 1:
                    continue
                for of in sorted(self.outgoings.get(g, set()),
                                 key=lambda f: f.id):
                    if of in visited_flows[xor] or (
                        g == dominator and of not in dom_frontier
                    ):
                        continue
                    if of in changes:
                        changes[of].xors.add(xor)
                    else:
                        changes[of] = _SingleTokenGen(xor, g, of)

        # Loop-injection token generators: for every loop-join reached
        # during the backward exploration whose injecting back-edges sit
        # deeper than the IOR, every XOR that did *not* reach that loop-join
        # must receive a token (reference: loopChanges/MultipleTokenGen).
        loop_changes: List["_MultipleTokenGen"] = []
        for loop_inj in sorted(loop_injections):
            if not loop_injections[loop_inj]:
                continue
            tmp: Set[str] = set()
            for xor in sorted(visited_gates):
                if loop_inj not in visited_gates[xor]:
                    tmp.add(xor)
            if tmp:
                loop_changes.append(
                    _MultipleTokenGen(tmp, loop_injections[loop_inj], loop_inj)
                )

        if not self.apply_hagen:
            return _OR

        for of in sorted(changes.keys(), key=lambda f: f.id):
            self._place_token_generator(changes[of])
        for mtg in loop_changes:
            self._place_multiple_token_generator(mtg)

        return _AND

    def _check_xor(
        self,
        visited_gates: Dict[str, Set[str]],
        visited_flows: Dict[str, Set[_Flow]],
        ands: Set[str],
    ) -> bool:
        visited_ids: Dict[str, Dict[str, Set[int]]] = {}
        unvisited_ids: Dict[str, Dict[str, Set[int]]] = {}
        for and_g in sorted(ands):
            visited_ids[and_g] = {}
            unvisited_ids[and_g] = {}
            for xor in sorted(visited_gates):
                v = visited_flows[xor]
                v1: Set[int] = set()
                u1: Set[int] = set()
                for oe in sorted(self.outgoings.get(and_g, set()),
                                 key=lambda f: f.id):
                    if oe in v:
                        v1.add(oe.id)
                    else:
                        u1.add(oe.id)
                if not v1:
                    continue
                visited_ids[and_g][xor] = v1
                unvisited_ids[and_g][xor] = u1

        for and_g in sorted(ands):
            for xor1 in sorted(visited_ids[and_g]):
                v1 = set(visited_ids[and_g][xor1])
                u1 = set(unvisited_ids[and_g][xor1])
                for xor2 in sorted(visited_ids[and_g]):
                    v2 = set(visited_ids[and_g][xor2])
                    u2 = set(unvisited_ids[and_g][xor2])
                    # retainAll(x) returns True (changed) iff not subset
                    u2_changed = not u2.issubset(u1)
                    v2_inter = v2 & v1
                    v2_changed = v2_inter != v2
                    if (not u2_changed) and (
                        (not v2_changed) or (not v2_inter)
                    ):
                        continue
                    return False
        return True

    def _place_token_generator(self, tg: "_SingleTokenGen") -> None:
        wg = self.wg
        e_gate = tg.escaping_gate
        e_flow = tg.escaping_flow
        first = e_flow.first
        fnode = wg.nodes.get(first)
        if (
            fnode is not None
            and fnode.kind == _AND
            and len(self.outgoings.get(first, set())) > 1
        ):
            and_g = first
        else:
            and_g = wg.add_node(_AND, label=_AND)
            wg.add_edge(e_gate, and_g)
            # ``first`` may be the map-only fake entry/exit sentinel, which
            # has no node in the WorkingGraph; the reference treats such a
            # flow target as null, so the diagram-side edge is a no-op.
            first_real = first in wg.nodes
            if first_real:
                wg.add_edge(and_g, first)
            self._add_gateway(and_g)
            self._add_flow(e_gate, and_g, and_g, e_gate)
            # re-source the escaping flow through the new AND
            ef = self._change_flow_src(e_flow, and_g)
            if first_real and first in wg.out_edges.get(e_gate, []):
                wg.remove_edge(e_gate, first)
            e_flow = ef
        for xor in sorted(tg.xors):
            wg.add_edge(and_g, xor)
            self._add_flow(and_g, xor, xor, and_g)

    def _place_multiple_token_generator(self, mtg: "_MultipleTokenGen") -> None:
        wg = self.wg
        xors = mtg.xors
        injections = mtg.injections
        loop_injection = mtg.loop_injection
        if not xors:
            return
        and_g: Optional[str] = None

        if len(injections) > 1:
            # merge all injecting back-edges through a new XOR join
            xor = wg.add_node(_XOR, label=_XOR)
            self._add_gateway(xor)
            srcs: Set[str] = set()
            for inj_flow in sorted(injections, key=lambda f: f.id):
                srcs.add(inj_flow.last)
                self._change_flow_tgt(inj_flow, xor)
            final_injection = self._add_flow(
                xor, loop_injection, loop_injection, xor
            )
            final_injection.loop = True
            injections = {final_injection}
            for s in list(wg.in_edges.get(loop_injection, [])):
                if s in srcs:
                    wg.remove_edge(s, loop_injection)
                    wg.add_edge(s, xor)
            wg.add_edge(xor, loop_injection)

        # at this point a single injecting back-edge remains
        for inj in sorted(injections, key=lambda f: f.id):
            last = inj.last
            lnode = wg.nodes.get(last)
            if (
                lnode is not None
                and lnode.kind == _AND
                and len(self.outgoings.get(last, set())) > 1
            ):
                and_g = last
            else:
                and_g = wg.add_node(_AND, label=_AND)
                self._add_gateway(and_g)
                self._change_flow_tgt(inj, and_g)
                for s in list(wg.in_edges.get(loop_injection, [])):
                    if s == last:
                        wg.remove_edge(s, loop_injection)
                        wg.add_edge(last, and_g)
                nf = self._add_flow(
                    and_g, loop_injection, loop_injection, and_g
                )
                nf.loop = True
                wg.add_edge(and_g, loop_injection)

        for x in sorted(xors):
            wg.add_edge(and_g, x)
            self._add_flow(and_g, x, x, and_g)

    def _change_flow_src(self, flow: _Flow, new_src: str) -> _Flow:
        last = new_src if flow.last == flow.src else flow.last
        nf = self._add_flow(new_src, flow.tgt, flow.first, last)
        if flow.loop:
            nf.loop = True
        self._remove_flow(flow)
        return nf


class _SingleTokenGen:
    __slots__ = ("xors", "escaping_gate", "escaping_flow")

    def __init__(self, xor, escaping_gate, escaping_flow):
        self.xors = {xor}
        self.escaping_gate = escaping_gate
        self.escaping_flow = escaping_flow


class _MultipleTokenGen:
    __slots__ = ("xors", "injections", "loop_injection")

    def __init__(self, xors, injections, loop_injection):
        self.xors = set(xors)
        self.injections = injections
        self.loop_injection = loop_injection


def _remove_trivial_gateways(wg: WorkingGraph) -> None:
    """Splice out any gateway with a single incoming and outgoing flow."""
    changed = True
    while changed:
        changed = False
        for gid in list(wg.nodes.keys()):
            node = wg.nodes.get(gid)
            if node is None or node.kind not in _GATE_KINDS:
                continue
            ins = list(wg.in_edges.get(gid, []))
            outs = list(wg.out_edges.get(gid, []))
            if len(ins) == 1 and len(outs) == 1:
                src, tgt = ins[0], outs[0]
                wg.remove_edge(src, gid)
                wg.remove_edge(gid, tgt)
                wg.remove_node(gid)
                if src != tgt:
                    wg.add_edge(src, tgt)
                changed = True
                break


def replace_inclusive_joins(
    wg: WorkingGraph, apply_hagen: bool = True
) -> None:
    """Replace every inclusive (OR) join with an XOR or AND join."""
    has_or = any(
        n.kind == _OR and len(wg.in_edges.get(nid, [])) > 1
        for nid, n in wg.nodes.items()
    )
    if not has_or:
        return
    gm = GatewayMap(wg, apply_hagen=apply_hagen)
    if not gm.build():
        return
    gm.detect_and_replace_iors()
