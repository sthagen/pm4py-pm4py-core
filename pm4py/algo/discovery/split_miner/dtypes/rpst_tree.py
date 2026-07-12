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
"""Refined Process Structure Tree (RPST) via triconnected components.

The graph is decomposed into triconnected components with the Hopcroft-Tarjan /
Gutwenger-Mutzel split-component algorithm (``ModelDecomposer`` +
``SplitCompDFS``), the components are organised into the triconnected
component tree (``TCTree``) and finally refined into the RPST.

Fragment types (``TCType``):
  * ``T`` trivial   – a single edge,
  * ``P`` polygon   – series composition (all skeleton vertices deg 2),
  * ``B`` bond      – parallel composition (two skeleton vertices),
  * ``R`` rigid     – triconnected, anything else.
"""
import uuid
from typing import Dict, List, Optional, Set, Tuple


# ----------------------------------------------------------------------
# Multigraph with orientable edges (mirrors jbpt TCTreeSkeleton)
# ----------------------------------------------------------------------


class Edge:
    __slots__ = ("v1", "v2", "virtual", "hidden", "id")

    def __init__(self, v1, v2, virtual=False):
        self.v1 = v1
        self.v2 = v2
        self.virtual = virtual
        self.hidden = False
        self.id = ""

    def other(self, w):
        return self.v1 if self.v2 == w else self.v2

    def set_vertices(self, v, w):
        self.v1 = v
        self.v2 = w

    def is_self_loop(self):
        return self.v1 == self.v2

    def __repr__(self):
        return f"{self.v1}-{self.v2}{'v' if self.virtual else ''}"


class Skeleton:
    """Undirected multigraph; adjacency lists preserve insertion order."""

    def __init__(self):
        self.vertices: List = []
        self._vset: Set = set()
        self.edges: List[Edge] = []
        self.inc: Dict[object, List[Edge]] = {}

    def add_vertex(self, v):
        if v not in self._vset:
            self._vset.add(v)
            self.vertices.append(v)
            self.inc[v] = []

    def add_edge(self, v1, v2, virtual=False):
        self.add_vertex(v1)
        self.add_vertex(v2)
        e = Edge(v1, v2, virtual)
        self.edges.append(e)
        self.inc[v1].append(e)
        self.inc[v2].append(e)
        return e

    def add_virtual_edge(self, v1, v2):
        return self.add_edge(v1, v2, virtual=True)

    def remove_edge(self, e: Edge):
        self.edges.remove(e)
        if e in self.inc.get(e.v1, []):
            self.inc[e.v1].remove(e)
        if e in self.inc.get(e.v2, []):
            self.inc[e.v2].remove(e)

    def get_edges(self, v) -> List[Edge]:
        return self.inc.get(v, [])

    def get_edge(self, v1, v2) -> Optional[Edge]:
        for e in self.inc.get(v1, []):
            if (e.v1 == v1 and e.v2 == v2) or (e.v1 == v2 and e.v2 == v1):
                return e
        return None

    def count_vertices(self) -> int:
        # vertices that still carry at least one edge
        return len({v for e in self.edges for v in (e.v1, e.v2)})

    def vertices_with_edges(self) -> Set:
        return {v for e in self.edges for v in (e.v1, e.v2)}


# ----------------------------------------------------------------------
# DFS passes (mirror AbstractDFS / ParentAndPathDFS / LowAndDescDFS /
# NumberDFS). They operate on a shared ``meta`` dict.
# ----------------------------------------------------------------------


class _DFS:
    """Recursive DFS framework with the four jbpt passes folded in via a
    ``mode`` flag (``low`` for LowAndDescDFS, ``number`` for NumberDFS)."""

    def __init__(self, skeleton: Skeleton, meta: dict, adj: dict, mode: str):
        self.g = skeleton
        self.meta = meta
        self.adj = adj
        self.mode = mode
        self.dfs_num = 0
        self.compl_num = 0
        # shared state
        self.num = meta.setdefault("num", {})
        self.compl = meta.setdefault("compl", {})
        self.state = meta.setdefault("state", {})
        self.etype = meta.setdefault("etype", {})
        for v in self.g.vertices:
            self.state[v] = 0
            self.num[v] = -1
            self.compl[v] = -1
        for e in self.g.edges:
            self.etype[e] = 0
        # ParentAndPath
        self.parent = meta.setdefault("parent", {})
        self.tree_arc = meta.setdefault("tree_arc", {})
        self.starts_path = meta.setdefault("starts_path", {})
        self.path_num = meta.setdefault("path_num", {})
        self._is_new_path = True
        self._path_number = 1
        for v in self.g.vertices:
            self.parent.setdefault(v, None)
            self.tree_arc.setdefault(v, None)
        for e in self.g.edges:
            self.path_num[e] = -1
            self.starts_path[e] = False
        if mode == "low":
            self.lp1n = meta["lp1n"] = {}
            self.lp2n = meta["lp2n"] = {}
            self.lp1v = meta["lp1v"] = {}
            self.lp2v = meta["lp2v"] = {}
            self.numdesc = meta["numdesc"] = {}
            for v in self.g.vertices:
                self.lp1n[v] = -1
                self.lp2n[v] = -1
                self.lp1v[v] = None
                self.lp2v[v] = None
                self.numdesc[v] = -1
        elif mode == "number":
            self.highpt = meta["highpt"] = {}
            self.numv = meta["numv"] = {}
            self.numtree = meta["numtree"] = {}
            self.lp1num = meta["lp1num"] = {}
            self.lp2num = meta["lp2num"] = {}
            for v in self.g.vertices:
                self.highpt[v] = []
                self.numv[v] = -1
                self.numtree[v] = -1
            self._m = len(self.g.vertices)

    def start(self, root):
        self.dfs_num = 0
        self.compl_num = 0
        self._dfs(root)

    def _dfs(self, v):
        self.dfs_num += 1
        self.num[v] = self.dfs_num
        self.state[v] = 1
        self._pre_visit(v, self.num[v])
        for e in list(self.adj[v]):
            if self.etype.get(e, 0) != 0:
                continue
            w = e.other(v)
            e.set_vertices(v, w)
            if self.state.get(w, 0) == 0:
                self.etype[e] = 1
                self._pre_traverse(e, w, True)
                self._dfs(w)
                self._post_traverse(e, w)
            else:
                self.etype[e] = 2
                self._pre_traverse(e, w, False)
        self.state[v] = 2
        self.compl_num += 1
        self.compl[v] = self.compl_num
        self._post_visit(v, self.num[v], self.compl[v])

    # -- hooks --------------------------------------------------------

    def _pre_visit(self, v, dfsnum):
        if self.mode == "low":
            self.lp1n[v] = dfsnum
            self.lp2n[v] = dfsnum
            self.lp1v[v] = v
            self.lp2v[v] = v
            self.numdesc[v] = 1
        elif self.mode == "number":
            self.numv[v] = self._m - self.meta["numdesc"][v] + 1
            self.numtree[v] = 0

    def _pre_traverse(self, e, w, tree_edge):
        # ParentAndPath
        v = e.other(w)
        if tree_edge:
            self.parent[w] = v
            self.tree_arc[w] = e
            self.path_num[e] = self._path_number
            if self._is_new_path:
                self.starts_path[e] = True
                self._is_new_path = False
        else:
            self.path_num[e] = self._path_number
            if self._is_new_path:
                self.starts_path[e] = True
            self._path_number += 1
            self._is_new_path = True
        if self.mode == "low" and not tree_edge:
            if self.num[w] < self.lp1n[v]:
                self.lp2n[v] = self.lp1n[v]
                self.lp2v[v] = self.lp1v[v]
                self.lp1n[v] = self.num[w]
                self.lp1v[v] = w
            elif self.num[w] > self.lp1n[v] and self.num[w] < self.lp2n[v]:
                self.lp2n[v] = self.num[w]
                self.lp2v[v] = w
        if self.mode == "number" and not tree_edge:
            self.highpt[w].append(e.other(w))

    def _post_traverse(self, e, w):
        v = e.other(w)
        if self.mode == "low":
            if self.lp1n[w] < self.lp1n[v]:
                mn = min(self.lp1n[v], self.lp2n[w])
                self.lp2n[v] = mn
                if mn == self.lp1n[v]:
                    self.lp2v[v] = self.lp1v[v]
                else:
                    self.lp2v[v] = self.lp2v[w]
                self.lp1n[v] = self.lp1n[w]
                self.lp1v[v] = self.lp1v[w]
            elif self.lp1n[w] == self.lp1n[v]:
                if self.lp2n[w] < self.lp2n[v]:
                    self.lp2n[v] = self.lp2n[w]
                    self.lp2v[v] = self.lp2v[w]
            elif self.lp1n[w] < self.lp2n[v]:
                self.lp2n[v] = self.lp1n[w]
                self.lp2v[v] = self.lp1v[w]
            self.numdesc[v] = self.numdesc[v] + self.numdesc[w]
        elif self.mode == "number":
            self._m -= 1
            self.numtree[v] = self.numtree[v] + 1

    def _post_visit(self, v, dfsnum, complnum):
        if self.mode == "number":
            self.lp1num[v] = self.numv[self.meta["lp1v"][v]]
            self.lp2num[v] = self.numv[self.meta["lp2v"][v]]


# ----------------------------------------------------------------------
# Split-component DFS (mirrors SplitCompDFS)
# ----------------------------------------------------------------------


class _TSItem:
    __slots__ = ("a", "b", "numH", "numA")

    def __init__(self, numH=-1, a=None, b=None, get_num=None):
        self.a = a
        self.b = b
        self.numH = numH
        self.numA = get_num(a) if (a is not None and get_num) else -1


class _SplitCompDFS:
    def __init__(self, g, meta, adj, comp, parent, tree_arc, highpt,
                 etype, virt, assigned_virt, is_hidden):
        self.g = g
        self.meta = meta
        self.adj = adj
        self.comp = comp
        self.parent = parent
        self.tree_arc = tree_arc
        self.highpt = highpt
        self.etype = etype
        self.virt = virt
        self.assigned_virt = assigned_virt
        self.is_hidden = is_hidden
        self.EOS = _TSItem()
        self.dfs_root = None
        self.e_stack: List[Edge] = []
        self.t_stack: List[_TSItem] = []
        self.num_not_visited_tree_edges = {}
        self.starts_path = meta["starts_path"]
        for v in g.vertices:
            self.num_not_visited_tree_edges[v] = meta["numtree"].get(v, 0)
        # restrict adjacency to the current (ordered) adj lists
        self.state = {}

    # -- helpers ------------------------------------------------------

    def get_num(self, v):
        return self.meta["numv"][v]

    def get_l1num(self, v):
        return self.meta["lp1num"][v]

    def get_l2num(self, v):
        return self.meta["lp2num"][v]

    def get_numdesc(self, v):
        return self.meta["numdesc"][v]

    def get_hnum(self, v):
        hp = self.highpt.get(v, [])
        if hp:
            return self.get_num(hp[0])
        return 0

    @staticmethod
    def is_same_edge(e, v, w):
        return (e.v1 == v and e.v2 == w) or (e.v1 == w and e.v2 == v)

    def _ts(self, numH, a, b):
        return _TSItem(numH, a, b, self.get_num)

    # -- driver -------------------------------------------------------

    def start(self, root):
        self.dfs_root = root
        self.t_stack.append(self.EOS)
        self._dfs(root)
        if self.e_stack:
            self.new_component(list(self.e_stack))
            self.e_stack.clear()

    def _dfs(self, v):
        # mirrors AbstractDFS.dfs but driven by ordered adj lists, with
        # pre/post traverse hooks specialised below.
        self.state[v] = 1
        for e in list(self.meta["ordered_adj"][v]):
            if self.etype.get(e, 0) not in (1, 2):
                # determine tree vs back using node state
                w = e.other(v)
                e.set_vertices(v, w)
                if self.state.get(w, 0) == 0:
                    self.etype[e] = 1
                    self.pre_traverse(e, w, True)
                    self._dfs(w)
                    self.post_traverse(e, w)
                else:
                    self.etype[e] = 2
                    self.pre_traverse(e, w, False)
            else:
                w = e.other(v)
                e.set_vertices(v, w)
                if self.state.get(w, 0) == 0:
                    self.pre_traverse(e, w, True)
                    self._dfs(w)
                    self.post_traverse(e, w)
                else:
                    self.pre_traverse(e, w, False)
        self.state[v] = 2

    # -- hooks --------------------------------------------------------

    def pre_traverse(self, e, w, tree_edge):
        v = e.other(w)
        self.num_not_visited_tree_edges[v] = (
            self.num_not_visited_tree_edges.get(v, 0) - 1
        )
        if self.starts_path.get(e, False):
            self.update_t_stack(v, w, tree_edge)
        if not tree_edge:
            if w == self.parent.get(v):
                el = [e, self.tree_arc.get(v)]
                C = self.new_component(el)
                virt_e = self.new_virtual_edge(C, w, v)
                for edge in C:
                    self.assigned_virt[edge] = virt_e
                self.make_tree_edge(virt_e, w, v)
            else:
                self.e_stack.append(e)

    def post_traverse(self, e, w):
        v = e.other(w)
        if self.is_hidden.get(e, False):
            e_to_push = self.assigned_virt.get(e)
            while self.is_hidden.get(e_to_push, False):
                e_to_push = self.assigned_virt.get(e_to_push)
            self.e_stack.append(e_to_push)
        else:
            self.e_stack.append(e)
        self.check_type2(e, v, w)
        self.check_type1(e, v, w)
        if self.starts_path.get(e, False):
            while self.t_stack and self.t_stack[-1] is not self.EOS:
                self.t_stack.pop()
            if self.t_stack:
                self.t_stack.pop()  # remove EOS
        if self.t_stack:
            i = self.t_stack[-1]
            high_v = self.get_hnum(v)
            while (i is not self.EOS and i.a != v and i.b != v
                   and high_v > i.numH):
                self.t_stack.pop()
                i = self.t_stack[-1] if self.t_stack else self.EOS

    # -- updateTStack (reconstructed) --------------------------------

    def update_t_stack(self, v, w, is_tree_edge):
        last_removed = None
        y = -1
        if is_tree_edge:
            while (self.t_stack and self.t_stack[-1] is not self.EOS
                   and self.t_stack[-1].numA > self.get_l1num(w)):
                last_removed = self.t_stack.pop()
                if last_removed.numH > y:
                    y = last_removed.numH
            h = self.get_num(w) + self.get_numdesc(w) - 1
            if last_removed is None:
                item = self._ts(h, self.meta["lp1v"][w], v)
            else:
                item = self._ts(max(y, h), self.meta["lp1v"][w], last_removed.b)
            self.t_stack.append(item)
            self.t_stack.append(self.EOS)
        else:
            while (self.t_stack and self.t_stack[-1] is not self.EOS
                   and self.t_stack[-1].numA > self.get_num(w)):
                last_removed = self.t_stack.pop()
                if last_removed.numH > y:
                    y = last_removed.numH
            if last_removed is None:
                item = self._ts(self.get_num(v), w, v)
            else:
                item = self._ts(y, w, last_removed.b)
            self.t_stack.append(item)

    # -- checkType1 ---------------------------------------------------

    def check_type1(self, e_backtrack, v, w):
        if (self.get_l2num(w) >= self.get_num(v)
                and self.get_l1num(w) < self.get_num(v)
                and (self.parent.get(v) != self.dfs_root
                     or self.num_not_visited_tree_edges.get(v, 0) > 0)):
            lowpt1_w = self.meta["lp1v"][w]
            C = self.new_component([])
            num_w = self.get_num(w)
            h = num_w + self.get_numdesc(w) - 1
            e = self.e_stack[-1] if self.e_stack else None
            while self.e_stack and (
                (num_w <= self.get_num(e.v1) <= h)
                or (num_w <= self.get_num(e.v2) <= h)
            ):
                e = self.e_stack.pop()
                C = self.add_to_component([e], C)
                e = self.e_stack[-1] if self.e_stack else None
            virtual_edge = self.new_virtual_edge(C, v, lowpt1_w)
            for edge in C:
                self.assigned_virt[edge] = virtual_edge
            if self.e_stack and self.is_same_edge(self.e_stack[-1], v, lowpt1_w):
                e = self.e_stack.pop()
                el = [e, virtual_edge]
                C = self.new_component(el)
                virtual_edge = self.new_virtual_edge(C, v, lowpt1_w)
                for edge in C:
                    self.assigned_virt[edge] = virtual_edge
            if lowpt1_w != self.parent.get(v):
                self.e_stack.append(virtual_edge)
            else:
                tree_arc_v = self.tree_arc.get(v)
                el = [tree_arc_v, virtual_edge]
                C = self.new_component(el)
                virtual_edge = self.new_virtual_edge(C, lowpt1_w, v)
                for edge in C:
                    self.assigned_virt[edge] = virtual_edge
                self.tree_arc[v] = virtual_edge
            self.meta["ordered_adj"][v].append(virtual_edge)
            self.make_tree_edge(virtual_edge, lowpt1_w, v)

    # -- checkType2 ---------------------------------------------------

    def check_type2(self, e_backtrack, v, w):
        top = self.t_stack[-1] if self.t_stack else None
        adj_w = self.meta["ordered_adj"][w]
        first_child = adj_w[0].other(w) if adj_w else None
        edge_count_w = self.meta["edge_count"][w]
        while v != self.dfs_root and (
            (top is not None and top is not self.EOS and top.a == v)
            or (edge_count_w == 2 and first_child is not None
                and self.get_num(first_child) > self.get_num(w))
        ):
            e_ab: List[Edge] = []
            virt_edge = None
            C = None
            if (top is not None and top is not self.EOS and top.a == v
                    and self.parent.get(top.b) == top.a):
                self.t_stack.pop()
                top = self.t_stack[-1] if self.t_stack else None
                continue
            C = self.new_component([])
            if (edge_count_w == 2 and first_child is not None
                    and self.get_num(first_child) > self.get_num(w)):
                # simple type-2 case
                e1 = self.e_stack.pop()
                el = [e1]
                e2 = self.e_stack.pop()
                el.append(e2)
                self.add_to_component(el, C)
                virt_edge = self.new_virtual_edge(C, v, first_child)
                for edge in C:
                    self.assigned_virt[edge] = virt_edge
                if self.e_stack:
                    e = self.e_stack[-1]
                    if (self.is_same_edge(e, v, top.b if top else None)
                            or self.is_same_edge(e, v, first_child)):
                        e_ab.append(self.e_stack.pop())
            else:
                top = self.t_stack.pop()
                e = self.e_stack[-1] if self.e_stack else None
                while (e is not None
                       and top.numA <= self.get_num(e.v1)
                       and top.numA <= self.get_num(e.v2)
                       and self.get_num(e.v1) <= top.numH
                       and self.get_num(e.v2) <= top.numH):
                    e = self.e_stack.pop()
                    if self.is_same_edge(e, top.a, top.b):
                        e_ab.append(e)
                    else:
                        C = self.add_to_component([e], C)
                    e = self.e_stack[-1] if self.e_stack else None
                virt_edge = self.new_virtual_edge(C, top.a, top.b)
                for edge in C:
                    self.assigned_virt[edge] = virt_edge
            if e_ab:
                e_ab.append(virt_edge)
                C = self.new_component(e_ab)
                if (top is None or top.b is None
                        or (first_child is not None
                            and self.is_same_edge(e_ab[0], v, first_child))):
                    b = first_child
                else:
                    b = top.b
                virt_edge = self.new_virtual_edge(C, v, b)
                for edge in C:
                    self.assigned_virt[edge] = virt_edge
            self.e_stack.append(virt_edge)
            self.make_tree_edge(virt_edge, v, virt_edge.other(v))
            w = virt_edge.other(v)
            self.parent[w] = v
            top = self.t_stack[-1] if self.t_stack else None
            adj_w = self.meta["ordered_adj"][w]
            first_child = adj_w[0].other(w) if adj_w else None
            edge_count_w = self.meta["edge_count"][w]

    # -- component helpers -------------------------------------------

    def new_component(self, comp_edges):
        self.remove_edges(comp_edges)
        self.comp.append(comp_edges)
        return comp_edges

    def add_to_component(self, comp_edges, component):
        self.remove_edges(comp_edges)
        component.extend(comp_edges)
        return component

    def remove_edges(self, edges):
        for e in edges:
            adj = self.meta["ordered_adj"].get(e.v1, [])
            if adj and e in adj:
                adj.remove(e)
            if e in self.g.edges:
                self.g.remove_edge(e)
                self.update_edge_count(e.v1, -1)
                self.update_edge_count(e.v2, -1)
            self.is_hidden[e] = True

    def new_virtual_edge(self, component, v, w):
        ve = self.g.add_virtual_edge(v, w)
        self.update_edge_count(v, 1)
        self.update_edge_count(w, 1)
        ve.id = str(uuid.uuid4())
        self.virt[ve] = True
        component.insert(0, ve)
        self.meta["ordered_adj"][v].append(ve)
        return ve

    def make_tree_edge(self, e, v, w):
        e.set_vertices(v, w)
        self.etype[e] = 1

    def update_edge_count(self, node, i):
        self.meta["edge_count"][node] = self.meta["edge_count"].get(node, 0) + i


# ----------------------------------------------------------------------
# Triconnected component tree node + decomposer
# ----------------------------------------------------------------------


class TCNode:
    def __init__(self, name=""):
        self.name = name
        self.ttype = ""  # B / P / R / T
        self.skeleton = Skeleton()
        self.boundary: List = []
        self.children: List["TCNode"] = []

    def __repr__(self):
        return f"{self.ttype or '?'}{self.name}"


def _order_adj_lists(g: Skeleton, meta: dict) -> Dict[object, List[Edge]]:
    n = len(g.vertices)
    bucket_size = 3 * n + 2
    bucket = [[] for _ in range(bucket_size)]
    num = meta["num"]
    lp1 = meta["lp1n"]
    lp2 = meta["lp2n"]
    etype = meta["etype"]
    for e in g.edges:
        if etype.get(e, 0) == 1:  # tree edge
            if lp2[e.v2] < num[e.v1]:
                phi = 3 * lp1[e.v2]
            else:
                phi = 3 * lp1[e.v2] + 2
        else:  # back edge
            phi = 3 * num[e.v2] + 1
        bucket[phi - 1].append(e)
    ordered: Dict[object, List[Edge]] = {v: [] for v in g.vertices}
    for el in bucket:
        for e in el:
            ordered[e.v1].append(e)
    meta["ordered_adj"] = ordered
    return ordered


def _sort_consecutive_multiple_edges(g: Skeleton) -> List[Edge]:
    indices = {v: i for i, v in enumerate(g.vertices)}
    bucket = [[] for _ in range(len(g.vertices))]
    for e in g.edges:
        i = min(indices[e.v1], indices[e.v2])
        bucket[i].append(e)
    sorted_edges: List[Edge] = []
    for el in bucket:
        groups: Dict[int, List[Edge]] = {}
        for e in el:
            key = indices[e.v1] + indices[e.v2]
            groups.setdefault(key, []).append(e)
        for g_edges in groups.values():
            sorted_edges.extend(g_edges)
    return sorted_edges


def _split_off_initial_multiple_edges(g, components, virt, assigned, hidden):
    edges = _sort_consecutive_multiple_edges(g)
    temp = []
    last = None
    size = 0
    for cur in edges:
        if last is not None:
            same = ((cur.v1 == last.v1 and cur.v2 == last.v2)
                    or (cur.v1 == last.v2 and cur.v2 == last.v1))
            if same:
                temp.append(last)
                size += 1
            elif size > 0:
                temp.append(last)
                _md_new_component(g, components, temp, virt, assigned,
                                  hidden, last.v1, last.v2)
                temp = []
                size = 0
        last = cur
    if size > 0:
        temp.append(last)
        _md_new_component(g, components, temp, virt, assigned, hidden,
                          last.v1, last.v2)


def _md_new_component(g, components, temp, virt, assigned, hidden, v1, v2):
    for e in temp:
        if e in g.edges:
            g.remove_edge(e)
        hidden[e] = True
    ve = g.add_virtual_edge(v1, v2)
    virt[ve] = True
    temp.insert(0, ve)
    for e in temp:
        assigned[e] = ve
    components.append(temp)


def _find_split_components(g, components, virt, assigned, hidden, meta, root):
    adj = {v: list(g.get_edges(v)) for v in g.vertices}
    meta["adj"] = adj
    dfs1 = _DFS(g, meta, adj, "low")
    dfs1.start(root)
    ordered = _order_adj_lists(g, meta)
    copied = {v: list(lst) for v, lst in ordered.items()}
    # reset edge types for the renumber DFS (preserve nothing across)
    dfs2 = _DFS(g, meta, copied, "number")
    # NumberDFS reuses parent/treearc/highpt maps – clear etype first
    for e in g.edges:
        meta["etype"][e] = 0
    for v in g.vertices:
        meta["state"][v] = 0
    dfs2.start(root)
    meta["ordered_adj"] = {v: list(lst) for v, lst in copied.items()}
    meta["edge_count"] = {v: len(g.get_edges(v)) for v in g.vertices}
    # reset etype/state for the split DFS
    for e in g.edges:
        meta["etype"][e] = 0
    for v in g.vertices:
        meta["state"][v] = 0
    dfs3 = _SplitCompDFS(
        g, meta, meta["ordered_adj"], components,
        meta["parent"], meta["tree_arc"], meta["highpt"],
        meta["etype"], virt, assigned, hidden,
    )
    dfs3.start(root)


def get_triconnected_components(g: Skeleton, back_edge: Edge):
    components: List[List[Edge]] = []
    virt: Dict[Edge, bool] = {e: False for e in g.edges}
    virt[back_edge] = True
    assigned: Dict[Edge, Edge] = {}
    hidden: Dict[Edge, bool] = {e: False for e in g.edges}
    meta: dict = {}
    for e in g.edges:
        if e.is_self_loop():
            return None
    _split_off_initial_multiple_edges(g, components, virt, assigned, hidden)
    _find_split_components(g, components, virt, assigned, hidden, meta,
                           back_edge.v1)

    # build TCNodes
    nodes: List[TCNode] = []
    for i, el in enumerate(components):
        node = TCNode(str(i))
        sk = Skeleton()
        for edge in el:
            if virt.get(edge, False):
                ve = sk.add_virtual_edge(edge.v1, edge.v2)
                ve.id = edge.id
            else:
                sk.add_edge(edge.v1, edge.v2)
        node.skeleton = sk
        nodes.append(node)
    _classify(nodes)

    # merge components sharing a virtual edge (same type, same id)
    result: List[TCNode] = []
    queue = list(nodes)
    while queue:
        node = queue.pop(0)
        if node.ttype == "R":
            result.append(node)
            continue
        delete = False
        remove = None
        replace = None
        for other in queue:
            if node.ttype != other.ttype:
                continue
            for edge in [e for e in node.skeleton.edges if e.virtual]:
                # Match the shared virtual edge by id, not by endpoints:
                # a bond may carry several parallel virtual edges between
                # the same poles, so get_edge(v1, v2) would return an
                # arbitrary one and miss the actual shared split edge.
                e = next(
                    (x for x in other.skeleton.edges
                     if x.virtual and x.id == edge.id),
                    None,
                )
                if e is None:
                    continue
                remove = other
                replace = TCNode(other.name)
                replace.ttype = other.ttype
                rs = Skeleton()
                for e2 in node.skeleton.edges:
                    if e2 is edge:
                        continue
                    ne = (rs.add_virtual_edge(e2.v1, e2.v2) if e2.virtual
                          else rs.add_edge(e2.v1, e2.v2))
                    ne.id = e2.id
                for e2 in other.skeleton.edges:
                    if e2 is e:
                        continue
                    ne = (rs.add_virtual_edge(e2.v1, e2.v2) if e2.virtual
                          else rs.add_edge(e2.v1, e2.v2))
                    ne.id = e2.id
                replace.skeleton = rs
                delete = True
                break
            if delete:
                break
        if not delete:
            result.append(node)
            continue
        queue.remove(remove)
        queue.append(replace)
    return result


def _classify(nodes: List[TCNode]):
    rc = bc = pc = 0
    for n in nodes:
        if n.skeleton.count_vertices() == 2:
            n.ttype = "B"
            n.name = f"B{bc}"
            bc += 1
            continue
        is_s = True
        for v in n.skeleton.vertices_with_edges():
            if len(n.skeleton.get_edges(v)) != 2:
                is_s = False
                break
        if is_s:
            n.ttype = "P"
            n.name = f"P{pc}"
            pc += 1
        else:
            n.ttype = "R"
            n.name = f"R{rc}"
            rc += 1


# ----------------------------------------------------------------------
# RPST public entry
# ----------------------------------------------------------------------


class RPSTFragment:
    def __init__(self):
        self.ttype = ""
        self.name = ""
        self.entry = None
        self.exit = None
        self.boundary: List = []
        # directed edges (u, v) of the fragment (back-edge / v* mapped out)
        self.edges: Set[Tuple[object, object]] = set()
        self.children: List["RPSTFragment"] = []
        self.is_loop = False


def _build_tctree(nodes: List[TCNode], back_edge: Edge) -> Optional[TCNode]:
    """Nest the triconnected components into a tree via shared virtual
    edges, then attach trivial (T) children for every real edge."""
    # adjacency: virtual-edge id -> the (<=2) components carrying it
    by_vid: Dict[str, List[TCNode]] = {}
    for n in nodes:
        for e in n.skeleton.edges:
            if e.virtual and e.id:
                by_vid.setdefault(e.id, []).append(n)

    # root = component containing the back edge
    root = None
    for n in nodes:
        if n.skeleton.get_edge(back_edge.v1, back_edge.v2) is not None:
            root = n
            break
    if root is None:
        return None
    root.boundary = [back_edge.v1, back_edge.v2]

    visited = {id(root)}
    queue = [root]
    while queue:
        cur = queue.pop(0)
        for e in cur.skeleton.edges:
            if not (e.virtual and e.id):
                continue
            for nb in by_vid.get(e.id, []):
                if id(nb) in visited:
                    continue
                visited.add(id(nb))
                nb.boundary = [e.v1, e.v2]
                cur.children.append(nb)
                queue.append(nb)

    # trivial children for every real (non-virtual) edge
    tc = 0
    all_nodes = []
    stack = [root]
    while stack:
        n = stack.pop()
        all_nodes.append(n)
        stack.extend(n.children)
    for n in list(all_nodes):
        for e in n.skeleton.edges:
            if e.virtual:
                continue
            t = TCNode(f"T{tc}")
            tc += 1
            t.ttype = "T"
            t.boundary = [e.v1, e.v2]
            t.skeleton = Skeleton()
            t.skeleton.add_edge(e.v1, e.v2)
            n.children.append(t)
    return root


def compute_rpst(directed_edges: List[Tuple[object, object]]):
    """Compute the RPST of a single-source/single-sink directed graph.

    Returns ``(root_fragment, src, sink)`` or ``None`` when the graph is
    not biconnected (the reference returns a null root in that case).
    """
    # First-seen node order keeps the whole decomposition deterministic
    # (set iteration order must never leak into the triconnected split).
    nodes: List[object] = []
    seen: Set[object] = set()
    indeg: Dict[object, int] = {}
    outdeg: Dict[object, int] = {}
    for (u, v) in directed_edges:
        for x in (u, v):
            if x not in seen:
                seen.add(x)
                nodes.append(x)
        outdeg[u] = outdeg.get(u, 0) + 1
        indeg[v] = indeg.get(v, 0) + 1
    sources = [n for n in nodes if indeg.get(n, 0) == 0]
    sinks = [n for n in nodes if outdeg.get(n, 0) == 0]
    if len(sources) != 1 or len(sinks) != 1:
        return None
    src, snk = sources[0], sinks[0]

    # split vertices with >1 in and >1 out (v -> v*)
    star: Dict[object, object] = {}
    for n in nodes:
        if indeg.get(n, 0) > 1 and outdeg.get(n, 0) > 1:
            star[n] = (n, "*")  # unique sentinel

    sk = Skeleton()
    dir_edges: List[Tuple[object, object]] = []
    for (u, v) in directed_edges:
        su = star[u] if u in star else u
        sk.add_edge(su, v)
        dir_edges.append((su, v))
    for n, ns in star.items():
        sk.add_edge(n, ns)
        dir_edges.append((n, ns))
    back_edge = sk.add_edge(snk, src)

    comps = get_triconnected_components(sk, back_edge)
    if comps is None:
        return None
    root_tc = _build_tctree(comps, back_edge)
    if root_tc is None:
        return None

    # ------------------------------------------------------------------
    # RPST refinement on the triconnected-component tree
    # ------------------------------------------------------------------
    extra_boundaries = {frozenset((n, ns)) for n, ns in star.items()}

    # (1) remove quasi trivial nodes: T children that are a v->v* edge
    def _remove_quasi(n: TCNode):
        n.children = [
            c for c in n.children
            if not (c.ttype == "T" and frozenset(c.boundary) in extra_boundaries)
        ]
        for c in n.children:
            _remove_quasi(c)

    _remove_quasi(root_tc)

    # (2) contract nodes with exactly one child (replace node by child)
    def _parents(n, pmap):
        for c in n.children:
            pmap[id(c)] = n
            _parents(c, pmap)

    changed = True
    while changed:
        changed = False
        pmap: Dict[int, TCNode] = {}
        _parents(root_tc, pmap)
        stack = [root_tc]
        while stack:
            n = stack.pop()
            if len(n.children) == 1:
                child = n.children[0]
                if n is root_tc:
                    root_tc = child
                else:
                    p = pmap[id(n)]
                    p.children[p.children.index(n)] = child
                changed = True
                break
            stack.extend(n.children)

    # ------------------------------------------------------------------
    # directed maps in real (un-split) space, from the original edges
    # ------------------------------------------------------------------
    out_adj: Dict[object, Set[object]] = {}
    in_adj: Dict[object, Set[object]] = {}
    for (u, v) in directed_edges:
        out_adj.setdefault(u, set()).add(v)
        in_adj.setdefault(v, set()).add(u)

    unstar = {ns: n for n, ns in star.items()}

    def _real(x):
        return unstar.get(x, x)

    def _convert(tc: TCNode) -> Optional[RPSTFragment]:
        if tc.ttype == "T" and src in tc.boundary and snk in tc.boundary:
            return None
        f = RPSTFragment()
        f.ttype = tc.ttype
        f.name = tc.name
        f.boundary = [_real(b) for b in tc.boundary]
        for c in tc.children:
            cf = _convert(c)
            if cf is not None:
                f.children.append(cf)
        return f

    root = _convert(root_tc)
    if root is None:
        return None

    def _fill_edges(f: RPSTFragment):
        for c in f.children:
            _fill_edges(c)
            f.edges |= c.edges
        if f.ttype == "T" and len(f.boundary) == 2:
            a, b = f.boundary
            if a != b:
                if b in out_adj.get(a, set()):
                    f.edges.add((a, b))
                if a in out_adj.get(b, set()):
                    f.edges.add((b, a))

    _fill_edges(root)

    # orient entry/exit: entry is the boundary node that sources the
    # fragment (no incoming edge from within it); fall back to the
    # reference rule when both / neither qualify.
    def _orient(f: RPSTFragment, is_root: bool):
        if is_root:
            f.entry, f.exit = src, snk
        elif len(f.boundary) == 2:
            b0, b1 = f.boundary
            cin0 = any(v == b0 for (_u, v) in f.edges)
            cin1 = any(v == b1 for (_u, v) in f.edges)
            if snk in (b0, b1):
                # the global sink can only be a fragment exit
                f.exit = snk
                f.entry = b0 if b1 == snk else b1
            elif src in (b0, b1):
                # the global source can only be a fragment entry
                f.entry = src
                f.exit = b0 if b1 == src else b1
            elif not cin0 and cin1:
                f.entry, f.exit = b0, b1
            elif not cin1 and cin0:
                f.entry, f.exit = b1, b0
            else:
                entry, exit_ = b0, b1
                coutf = sum(1 for (u, _v) in f.edges if u == entry)
                coutg = len(out_adj.get(entry, set()))
                if not ((not cin0) or coutf == coutg):
                    entry, exit_ = exit_, entry
                f.entry, f.exit = entry, exit_
        for c in f.children:
            _orient(c, False)

    _orient(root, True)
    return root, src, snk
