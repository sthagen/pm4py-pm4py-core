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
"""Split-gateway discovery

A breadth-first walk over the initial BPMN visits each
task; for a task with more than one successor we build one ``OracleItem``
per successor (``past = {successor}``, ``future = concurrent successors``)
and reduce them to a single nested item by repeatedly:

1. exhaustively merging XOR-brothers (equal future),
2. merging one group of AND-brothers (equal past∪future),
3. otherwise force-merging the two closest items (minimum AND-distance)
   into an AND — the reference never produces OR-splits here.

The resulting item tree is rendered into XOR/AND gateways. A persistent
``candidate_joins`` map keyed by each item's ``past|future`` signature lets
identical sub-structures across *different* split-tasks share a single
gateway, which is how Split Miner already materialises some joins during
split discovery ("JOINs generated due to shared future").

This is a faithful port of the reference Oracle split discovery,
validated to be byte-identical to ``splitminer.jar`` on the
SM-Experiment logs (see ``..algorithm``). Because it matches the *tool*
and not the idealised paper figures, it can yield more gateways than a
hand drawing — e.g. two AND-splits on the Augusto et al. (2019) running
example rather than the single one in Fig. 3c.
"""
from typing import Any, Dict, List, Optional, Set, Tuple

from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.algo.discovery.split_miner.splits.abc import SplitsDiscoverer


class _OracleItem:
    """One node of the split hierarchy (port of ``OracleItem``)."""

    __slots__ = ("past", "future", "xor_brothers", "and_brothers",
                 "_fsig", "_osig")

    def __init__(self) -> None:
        self.past: Set[str] = set()
        self.future: Set[str] = set()
        self.xor_brothers: List["_OracleItem"] = []
        self.and_brothers: List["_OracleItem"] = []
        self._fsig: Tuple[str, ...] = ()
        self._osig: Tuple[str, ...] = ()

    def engrave(self) -> None:
        self._fsig = tuple(sorted(self.future))
        self._osig = tuple(sorted(self.past | self.future))

    def signature(self) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
        return (tuple(sorted(self.past)), self._fsig)

    def is_xor(self, other: "_OracleItem") -> bool:
        return other._fsig == self._fsig

    def is_and(self, other: "_OracleItem") -> bool:
        return other._osig == self._osig

    def gate_type(self) -> Optional[str]:
        if self.xor_brothers:
            return "xor"
        if self.and_brothers:
            return "and"
        return None

    def node_code(self) -> Optional[str]:
        if len(self.past) == 1:
            return next(iter(self.past))
        return None

    def and_distance(self, other: "_OracleItem") -> int:
        return len((self.past | self.future) ^ (other.past | other.future))


def _merge_xors(brothers: List[_OracleItem]) -> _OracleItem:
    u = _OracleItem()
    u.xor_brothers = list(brothers)
    if brothers:
        u.future |= brothers[0].future  # all brothers share the same future
    for b in brothers:
        u.past |= b.past
    u.engrave()
    return u


def _merge_ands(brothers: List[_OracleItem]) -> _OracleItem:
    u = _OracleItem()
    u.and_brothers = list(brothers)
    if brothers:
        inter = set(brothers[0].future)
        for b in brothers[1:]:
            inter &= b.future
        u.future = inter
    for b in brothers:
        u.past |= b.past
    u.engrave()
    return u


def _forced_merge_ands(brothers: List[_OracleItem]) -> _OracleItem:
    u = _OracleItem()
    u.and_brothers = list(brothers)
    for b in brothers:
        u.future |= b.future
    for b in brothers:
        u.past |= b.past
    u.future -= u.past
    u.engrave()
    return u


def _sig_key(item: _OracleItem):
    return item.signature()


def _get_final_oracle_item(items: List[_OracleItem]) -> _OracleItem:
    """Reduce the per-successor items to a single nested item."""
    items = list(items)
    while len(items) != 1:
        merged = False

        # 1. exhaustively merge XOR-brothers (equal future)
        while True:
            to_merge: Optional[List[_OracleItem]] = None
            for oi in sorted(items, key=_sig_key):
                grp = [oii for oii in items if oii is not oi and oi.is_xor(oii)]
                if grp:
                    grp.append(oi)
                    to_merge = grp
                    break
            if not to_merge:
                break
            merged = True
            mat = _merge_xors(to_merge)
            for x in to_merge:
                items.remove(x)
            items.append(mat)

        # 2. merge one group of AND-brothers (equal past∪future)
        to_merge = None
        for oi in sorted(items, key=_sig_key):
            grp = [oii for oii in items if oii is not oi and oi.is_and(oii)]
            if grp:
                grp.append(oi)
                to_merge = grp
                break
        if to_merge:
            merged = True
            mat = _merge_ands(to_merge)
            for x in to_merge:
                items.remove(x)
            items.append(mat)

        if merged:
            continue

        # 3. nothing merged: force-merge the two closest items as AND
        sitems = sorted(items, key=_sig_key)
        best: Optional[Tuple[_OracleItem, _OracleItem]] = None
        best_d: Optional[int] = None
        for i, a in enumerate(sitems):
            for b in sitems[i + 1:]:
                d = a.and_distance(b)
                if best_d is None or d < best_d:
                    best_d = d
                    best = (a, b)
        assert best is not None
        a, b = best
        mat = _forced_merge_ands([a, b])
        items.remove(a)
        items.remove(b)
        items.append(mat)

    return items[0]


def _render(
    wg: WorkingGraph,
    entry: str,
    item: _OracleItem,
    candidate_joins: Dict,
) -> None:
    """Render an item tree into gateways, sharing via ``candidate_joins``."""
    sig = item.signature()
    shared = candidate_joins.get(sig)
    if shared is not None:
        wg.add_edge(entry, shared)
        return
    gtype = item.gate_type()
    if gtype is None:
        code = item.node_code()
        if code is not None:
            wg.add_edge(entry, code)
        return
    gate = wg.add_node(gtype, label=gtype)
    wg.add_edge(entry, gate)
    for nxt in sorted(item.xor_brothers, key=_sig_key):
        _render(wg, gate, nxt, candidate_joins)
    for nxt in sorted(item.and_brothers, key=_sig_key):
        _render(wg, gate, nxt, candidate_joins)
    candidate_joins[sig] = gate


class ClassicSplitsDiscoverer(SplitsDiscoverer):
    """Build XOR/AND split hierarchies via a faithful Oracle port."""

    @classmethod
    def apply(
        cls,
        wg: WorkingGraph,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        start = wg.start_id
        if start is None:
            return
        candidate_joins: Dict = {}
        to_visit: List[str] = [start]
        queued: Set[str] = {start}
        visited: Set[str] = set()

        while to_visit:
            entry = to_visit.pop(0)
            visited.add(entry)
            if entry == wg.end_id:
                continue
            succs = wg.successors(entry)
            if len(succs) > 1:
                items: List[_OracleItem] = []
                for s in sorted(succs):
                    oi = _OracleItem()
                    oi.past.add(s)
                    for b in succs:
                        if b != s and wg.is_concurrent(s, b):
                            oi.future.add(b)
                    oi.engrave()
                    items.append(oi)
                for s in list(succs):
                    wg.remove_edge(entry, s)
                final = _get_final_oracle_item(items)
                _render(wg, entry, final, candidate_joins)
                for s in succs:
                    if s not in visited and s not in queued:
                        to_visit.append(s)
                        queued.add(s)
            else:
                for s in succs:
                    if s not in visited and s not in queued:
                        to_visit.append(s)
                        queued.add(s)
