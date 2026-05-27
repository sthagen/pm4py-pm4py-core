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
"""Split-gateway discovery.

For every task with more than one outgoing edge we build a hierarchy of
XOR / AND gateways that captures the exclusion and concurrency relations
between its direct successors. Cover and future sets are tracked per
successor and per newly inserted gateway; the iteration stops once only
one root remains. A fallback OR-split is inserted when no further XOR or
AND grouping can be discovered.
"""
from typing import Any, Dict, List, Optional, Set

from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.algo.discovery.split_miner.splits.abc import SplitsDiscoverer


def _initial_cover_future(
    wg: WorkingGraph, d_successors: List[str]
):
    cover: Dict[str, Set[str]] = {}
    future: Dict[str, Set[str]] = {}
    for s in d_successors:
        cover[s] = {s}
        future[s] = {
            other
            for other in d_successors
            if other != s and wg.is_concurrent(s, other)
        }
    return cover, future


def _discover_xor_split(
    wg: WorkingGraph,
    s_set: List[str],
    cover: Dict[str, Set[str]],
    future: Dict[str, Set[str]],
) -> Optional[str]:
    for s1 in s_set:
        group: Set[str] = set()
        c_union: Set[str] = set(cover[s1])
        for s2 in s_set:
            if s2 == s1:
                continue
            if future[s1] == future[s2]:
                group.add(s2)
                c_union |= cover[s2]
        if group:
            group.add(s1)
            g = wg.add_node("xor", label="xor")
            for s in group:
                wg.add_edge(g, s)
                s_set.remove(s)
            s_set.append(g)
            cover[g] = c_union
            future[g] = set(future[s1])
            return g
    return None


def _discover_and_split(
    wg: WorkingGraph,
    s_set: List[str],
    cover: Dict[str, Set[str]],
    future: Dict[str, Set[str]],
) -> Optional[str]:
    for s1 in s_set:
        group: Set[str] = set()
        c_union: Set[str] = set(cover[s1])
        f_inter: Set[str] = set(future[s1])
        cf_s1 = cover[s1] | future[s1]
        for s2 in s_set:
            if s2 == s1:
                continue
            cf_s2 = cover[s2] | future[s2]
            if cf_s1 == cf_s2:
                group.add(s2)
                c_union |= cover[s2]
                f_inter &= future[s2]
        if group:
            group.add(s1)
            g = wg.add_node("and", label="and")
            for s in group:
                wg.add_edge(g, s)
                s_set.remove(s)
            s_set.append(g)
            cover[g] = c_union
            future[g] = f_inter
            return g
    return None


def _fallback_or_split(
    wg: WorkingGraph,
    s_set: List[str],
    cover: Dict[str, Set[str]],
    future: Dict[str, Set[str]],
) -> str:
    g = wg.add_node("or", label="or")
    c_union: Set[str] = set()
    for s in list(s_set):
        wg.add_edge(g, s)
        c_union |= cover[s]
    s_set.clear()
    s_set.append(g)
    cover[g] = c_union
    future[g] = set()
    return g


def _split_one(wg: WorkingGraph, t: str) -> None:
    d_succs = wg.successors(t)
    cover, future = _initial_cover_future(wg, d_succs)
    s_set: List[str] = list(d_succs)

    for s in list(d_succs):
        wg.remove_edge(t, s)

    safety = 0
    max_iter = 4 * len(d_succs) + 8
    while len(s_set) > 1:
        progress = False
        if _discover_xor_split(wg, s_set, cover, future) is not None:
            progress = True
        elif _discover_and_split(wg, s_set, cover, future) is not None:
            progress = True
        if not progress:
            _fallback_or_split(wg, s_set, cover, future)
            break
        safety += 1
        if safety > max_iter:
            _fallback_or_split(wg, s_set, cover, future)
            break

    if s_set:
        wg.add_edge(t, s_set[0])


class ClassicSplitsDiscoverer(SplitsDiscoverer):
    """Build a hierarchy of XOR/AND gateways at every split-task."""

    @classmethod
    def apply(
        cls,
        wg: WorkingGraph,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        split_tasks = [
            nid
            for nid, n in list(wg.nodes.items())
            if n.kind in {"task", "start"}
        ]
        for t in split_tasks:
            if len(wg.successors(t)) <= 1:
                continue
            _split_one(wg, t)
