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
from pm4py.util import nx_utils


def _prepare_place_transition_lists(net):
    place_list = sorted(list(net.places), key=lambda x: x.name)
    transition_list = sorted(list(net.transitions), key=lambda x: x.name)
    place_index = {p: i for i, p in enumerate(place_list)}
    return place_list, transition_list, place_index


def marking_to_key(marking: np.ndarray) -> bytes:
    """
    Convert a marking array into a stable bytes key.
    """
    return np.asarray(marking, dtype=np.float64).tobytes()


def compute_incidence_matrix(net, place_list=None, transition_list=None, place_index=None):
    """
    Given a Petri Net, the incidence matrix is computed. An incidence matrix has n rows (places) and m columns
    (transitions).
    :param net: Petri Net object
    :return: Incidence matrix
    """
    if (
        place_list is None
        or transition_list is None
        or place_index is None
    ):
        place_list, transition_list, place_index = _prepare_place_transition_lists(
            net
        )
    n = len(transition_list)
    m = len(place_list)
    C = np.zeros((m, n), dtype=np.int64)
    for j, t in enumerate(transition_list):
        for in_arc in t.in_arcs:
            C[place_index[in_arc.source], j] -= in_arc.weight
        for out_arc in t.out_arcs:
            C[place_index[out_arc.target], j] += out_arc.weight
    return C


def split_incidence_matrix(matrix, net, transition_list=None):
    """
    We split the incidence matrix columnwise to get the firing information for each transition
    :param matrix: incidence matrix
    :param net: Petri Net
    :return: Dictionary, whereby the key is an np array that contains the firing information and the value is the name
    of the transition
    """
    transition_dict = {}
    if transition_list is None:
        transition_list = sorted(list(net.transitions), key=lambda x: x.name)
    for i, transition in enumerate(transition_list):
        transition_dict[transition] = matrix[:, i]
    return transition_dict


def compute_firing_requirement(net):
    place_list, transition_list, place_index = _prepare_place_transition_lists(net)
    req_dense = {}
    req_sparse = {}
    deltas = {}
    for transition in transition_list:
        dense_req = np.zeros(len(place_list), dtype=np.int64)
        sparse_req = {}
        delta = {}
        for arc in transition.in_arcs:
            idx = place_index[arc.source]
            dense_req[idx] -= arc.weight
            sparse_req[idx] = sparse_req.get(idx, 0) + arc.weight
            delta[idx] = delta.get(idx, 0) - arc.weight
        for arc in transition.out_arcs:
            idx = place_index[arc.target]
            delta[idx] = delta.get(idx, 0) + arc.weight
        req_dense[transition] = dense_req
        req_sparse[transition] = list(sparse_req.items())
        deltas[transition] = list(delta.items())
    return req_dense, req_sparse, deltas, place_list, transition_list


def enabled_markings(req_sparse, deltas, marking):
    new_markings = []
    for transition, requirements in req_sparse.items():
        enabled = True
        for idx, required_weight in requirements:
            if marking[idx] < required_weight:
                enabled = False
                break
        if not enabled:
            continue
        new_marking = marking.copy()
        for idx, change in deltas[transition]:
            new_marking[idx] += change
        new_markings.append((new_marking, transition))
    return new_markings


def convert_marking(net, marking, original_net=None):
    """
    Takes an marking as input and converts it into an Numpy Array
    :param net: PM4Py Petri Net object
    :param marking: Marking that should be converted
    :param original_net: PM4Py Petri Net object without short-circuited transition
    :return: Numpy array representation
    """
    # marking_list=list(el.name for el in marking.keys())
    #
    marking_set = {el.name for el in marking.keys()}
    place_list = sorted(list(el.name for el in net.places))

    mark = np.zeros(len(place_list))
    for index, place in enumerate(place_list):
        if place in marking_set:
            mark[index] = 1
    return mark


def check_for_dead_tasks(net, graph):
    """
    We compute a list of dead tasks. A dead task is a task which does not appear in the Minimal Coverability Graph
    :param net: Petri Net representation of PM4Py
    :param graph: Minimal coverability graph. NetworkX MultiDiGraph object.
    :return: list of dead tasks
    """
    tasks = {
        transition
        for transition in sorted(list(net.transitions), key=lambda x: x.name)
        if transition.label is not None
    }
    for _, _, data in graph.edges(data=True):
        transition = data.get("transition")
        if transition in tasks:
            tasks.discard(transition)
    return sorted(list(tasks), key=lambda x: x.name)


def check_for_improper_conditions(mcg):
    """
    An improper condition is a state in the minimum-coverability graph with an possible infinite amount of tokens
    :param mcg: networkx object (minimal coverability graph)
    :return: True, if there are no improper conditions; false otherwise
    """
    improper_states = []
    for node in mcg.nodes:
        if np.inf in mcg.nodes[node]["marking"]:
            improper_states.append(node)
    return improper_states


def check_for_substates(mcg):
    """
    Checks if a substate exists in a given mcg
    :param mcg: Minimal coverability graph (networkx object)
    :return: True, if there exist no substate; False otherwise
    """
    for node in mcg.nodes:
        reachable_states = nx_utils.descendants(mcg, node)
        for state in reachable_states:
            if all(
                np.less(
                    mcg.nodes[node]["marking"], mcg.nodes[state]["marking"]
                )
            ):
                return False
    return True
