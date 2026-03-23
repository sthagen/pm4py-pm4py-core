'''
    PM4Py – A Process Mining Library for Python
Copyright (C) 2024 Process Intelligence Solutions UG (haftungsbeschränkt)

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
import numpy as np
from pm4py.algo.analysis.woflan.graphs import utility as helper
from pm4py.util import nx_utils


def construct_tree(net, initial_marking):
    """
    Construct a restricted coverability marking.
    For more information, see the thesis "Verification of WF-nets", 4.3.
    :param net:
    :param initial_marking:
    :return:
    """
    initial_marking = helper.convert_marking(net, initial_marking)
    _, req_sparse, deltas, place_list, _ = helper.compute_firing_requirement(
        net
    )
    place_index = {p: i for i, p in enumerate(place_list)}
    look_up_indices = {}
    j = 0
    coverability_graph = nx_utils.DiGraph()
    coverability_graph.add_node(j, marking=initial_marking)
    look_up_indices[helper.marking_to_key(initial_marking)] = j

    j += 1
    new_arc = True
    while new_arc:
        new_arc = False
        nodes = list(coverability_graph.nodes).copy()
        while len(nodes) > 0:
            m = nodes.pop()
            if np.inf not in coverability_graph.nodes[m]["marking"]:
                possible_markings = helper.enabled_markings(
                    req_sparse, deltas, coverability_graph.nodes[m]["marking"]
                )
                m2 = None
                if len(possible_markings) > 0:
                    for marking in possible_markings:
                        # check for m1 + since we want to construct a tree, we
                        # do not want that a marking is already in a graph
                        # since it is going to have an arc
                        if (
                            helper.marking_to_key(marking[0])
                            not in look_up_indices
                        ):
                            if check_if_transition_unique(
                                m, coverability_graph, marking[1]
                            ):
                                m2 = marking
                                new_arc = True
                                break
                if new_arc:
                    break
        if new_arc:
            ancestors = nx_utils.ancestors(coverability_graph, m)
            m3 = np.zeros(len(place_list))
            for place in place_list:
                idx = place_index[place]
                if check_for_smaller_marking(
                    m2[0], coverability_graph, idx, ancestors
                ):
                    m3[idx] = np.inf
                else:
                    m3[idx] = m2[0][idx]
            coverability_graph.add_node(j, marking=m3)
            coverability_graph.add_edge(m, j, transition=m2[1])
            look_up_indices[helper.marking_to_key(m3)] = j
            j += 1
    return coverability_graph


def check_if_transition_unique(marking, graph, transition):
    for edge in graph.out_edges(marking):
        if graph[edge[0]][edge[1]]["transition"] == transition:
            return False
    return True


def check_for_smaller_marking(
    marking, coverability_graph, index, ancestors
):
    for node in ancestors:
        node_marking = coverability_graph.nodes[node]["marking"]
        if all(
            np.less_equal(node_marking, marking)
        ):
            if node_marking[index] < marking[index]:
                return True
    return False
