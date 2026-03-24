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
from collections import deque
from pm4py.util import nx_utils


def create_network_graph(net):
    """
    Transform a given Petri Net in a network graph. Each place and transition is node and gets duplicated.
    The even numbers handle the inputs of a node, the odds the output.
    :param net: PM4Py Petri Net representation
    :return: networkx.DiGraph(), bookkeeping dictionary
    """
    graph = nx_utils.DiGraph()
    places = sorted(list(net.places), key=lambda x: x.name)
    transitions = sorted(list(net.transitions), key=lambda x: x.name)
    nodes = set(places) | set(transitions)
    bookkeeping = {}
    for index, el in enumerate(nodes):
        bookkeeping[el] = index * 2
    for node in nodes:
        graph.add_node(bookkeeping[node])
        graph.add_node(bookkeeping[node] + 1)
        graph.add_edge(bookkeeping[node], bookkeeping[node] + 1, capacity=1)
    # add edges for outgoing arcs in former Petri Net
    for element in nodes:
        for arc in element.out_arcs:
            graph.add_edge(
                bookkeeping[element] + 1, bookkeeping[arc.target], capacity=1
            )
    # add edges for ingoing arcs in former Petri Net
    for element in nodes:
        for arc in element.in_arcs:
            graph.add_edge(
                bookkeeping[arc.source] + 1, bookkeeping[element], capacity=1
            )
    return graph, bookkeeping


def apply(net):
    """
    Using the max-flow min-cut theorem, we compute a list of nett well handled TP and PT pairs
    (T=transition, P=place)
    :param net: Petri Net
    :return: List
    """
    graph, booking = create_network_graph(net)
    adjacency = {node: {} for node in graph.nodes}
    for u, v, data in graph.edges(data=True):
        adjacency[u][v] = data.get("capacity", 1)

    places = sorted(list(net.places), key=lambda x: x.name)
    transitions = sorted(list(net.transitions), key=lambda x: x.name)
    sources = [booking[p] + 1 for p in places] + [
        booking[t] + 1 for t in transitions
    ]
    reachability = _compute_reachability(adjacency, sources)

    pairs = []
    for place in places:
        p_source = booking[place] + 1
        p_target = booking[place]
        reachable_from_place = reachability[p_source]
        for transition in transitions:
            t_source = booking[transition] + 1
            t_target = booking[transition]
            if t_target in reachable_from_place:
                if _has_flow_value_at_least_two(adjacency, p_source, t_target):
                    pairs.append((p_source, t_target))
            if p_target in reachability[t_source]:
                if _has_flow_value_at_least_two(adjacency, t_source, p_target):
                    pairs.append((t_source, p_target))
    return pairs


def _compute_reachability(adjacency, sources):
    reachability = {}
    for source in sources:
        seen = set()
        queue = deque([source])
        while queue:
            node = queue.popleft()
            for neighbor in adjacency.get(node, {}):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        reachability[source] = seen
    return reachability


def _has_flow_value_at_least_two(adjacency, source, target, cutoff=2):
    """
    Lightweight unit-capacity max flow that stops once the cutoff is reached.
    """
    if source == target:
        return False
    residual = {u: neighbors.copy() for u, neighbors in adjacency.items()}
    for u, neighbors in adjacency.items():
        for v in neighbors:
            residual.setdefault(v, {})
            residual[v].setdefault(u, 0)
    flow = 0
    while flow < cutoff:
        parent = {source: None}
        queue = deque([source])
        while queue and target not in parent:
            node = queue.popleft()
            for neighbor, capacity in residual.get(node, {}).items():
                if capacity > 0 and neighbor not in parent:
                    parent[neighbor] = node
                    if neighbor == target:
                        break
                    queue.append(neighbor)
        if target not in parent:
            break
        v = target
        while v != source:
            u = parent[v]
            residual[u][v] -= 1
            residual[v][u] = residual[v].get(u, 0) + 1
            v = u
        flow += 1
    return flow >= cutoff
