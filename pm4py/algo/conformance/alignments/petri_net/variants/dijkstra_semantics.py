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
"""
Semantics-aware Dijkstra alignments for Petri nets.

Unlike the synchronous-product based alignment variants, this implementation
keeps the model marking in the search state and asks the supplied semantics
which transitions are enabled and how they fire.  It can therefore be used
unchanged for classic, inhibitor, reset, and reset/inhibitor Petri nets.
"""

import heapq
import sys
import time
from enum import Enum
from itertools import count
from typing import Any, Dict, Optional, Union

from pm4py.objects.log import obj as log_implementation
from pm4py.objects.log.obj import Trace
from pm4py.objects.petri_net import semantics as petri_semantics
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import align_utils
from pm4py.util import exec_utils, typing, variants_util
from pm4py.util.constants import PARAMETER_CONSTANT_ACTIVITY_KEY
from pm4py.util.xes_constants import DEFAULT_NAME_KEY


class Parameters(Enum):
    PARAM_TRACE_COST_FUNCTION = "trace_cost_function"
    PARAM_MODEL_COST_FUNCTION = "model_cost_function"
    PARAM_SYNC_COST_FUNCTION = "sync_cost_function"
    PARAM_ALIGNMENT_RESULT_IS_SYNC_PROD_AWARE = "ret_tuple_as_trans_desc"
    PARAM_MAX_ALIGN_TIME_TRACE = "max_align_time_trace"
    PARAM_MAX_ALIGN_TIME = "max_align_time"
    PARAMETER_VARIANT_DELIMITER = "variant_delimiter"
    ACTIVITY_KEY = PARAMETER_CONSTANT_ACTIVITY_KEY
    PETRI_SEMANTICS = "petri_semantics"


class _SearchNode:
    __slots__ = ("cost", "index", "marking", "parent", "move", "descriptor")

    def __init__(
        self,
        cost,
        index,
        marking,
        parent=None,
        move=None,
        descriptor=None,
    ):
        self.cost = cost
        self.index = index
        self.marking = marking
        self.parent = parent
        self.move = move
        self.descriptor = descriptor


def get_best_worst_cost(
    petri_net: PetriNet,
    initial_marking: Marking,
    final_marking: Marking,
    parameters: Optional[Dict[Any, Any]] = None,
):
    """Return the cost of aligning an empty trace to the model."""
    parameters = {} if parameters is None else dict(parameters)
    for key in list(parameters):
        if (
            getattr(key, "value", key)
            == Parameters.PARAM_TRACE_COST_FUNCTION.value
        ):
            del parameters[key]
    result = apply(
        log_implementation.Trace(),
        petri_net,
        initial_marking,
        final_marking,
        parameters=parameters,
    )
    return result["cost"] if result is not None else None


def apply(
    trace: Trace,
    petri_net: PetriNet,
    initial_marking: Marking,
    final_marking: Marking,
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> typing.AlignmentResult:
    """
    Align a trace to a Petri net using the supplied Petri-net semantics.

    The search state is ``(trace position, model marking)``. Successors are
    synchronous moves, log moves, and model moves. ``PETRI_SEMANTICS`` defaults
    to :class:`ClassicSemantics`, preserving the behavior expected for normal
    Petri nets.
    """
    if parameters is None:
        parameters = {}

    activity_key = exec_utils.get_param_value(
        Parameters.ACTIVITY_KEY, parameters, DEFAULT_NAME_KEY
    )
    semantics = exec_utils.get_param_value(
        Parameters.PETRI_SEMANTICS,
        parameters,
        petri_semantics.ClassicSemantics(),
    )
    trace_cost_function = exec_utils.get_param_value(
        Parameters.PARAM_TRACE_COST_FUNCTION, parameters, None
    )
    model_cost_function = exec_utils.get_param_value(
        Parameters.PARAM_MODEL_COST_FUNCTION, parameters, None
    )
    sync_cost_function = exec_utils.get_param_value(
        Parameters.PARAM_SYNC_COST_FUNCTION, parameters, None
    )
    max_align_time_trace = exec_utils.get_param_value(
        Parameters.PARAM_MAX_ALIGN_TIME_TRACE, parameters, sys.maxsize
    )
    ret_tuple_as_trans_desc = exec_utils.get_param_value(
        Parameters.PARAM_ALIGNMENT_RESULT_IS_SYNC_PROD_AWARE,
        parameters,
        False,
    )

    activities = [event[activity_key] for event in trace]
    if trace_cost_function is None:
        trace_cost_function = [
            align_utils.STD_MODEL_LOG_MOVE_COST for _ in activities
        ]
        parameters[Parameters.PARAM_TRACE_COST_FUNCTION] = trace_cost_function
    if model_cost_function is None:
        model_cost_function = {
            transition: (
                align_utils.STD_MODEL_LOG_MOVE_COST
                if transition.label is not None
                else align_utils.STD_TAU_COST
            )
            for transition in petri_net.transitions
        }
        parameters[Parameters.PARAM_MODEL_COST_FUNCTION] = model_cost_function
    if sync_cost_function is None:
        sync_cost_function = {
            transition: align_utils.STD_SYNC_COST
            for transition in petri_net.transitions
            if transition.label is not None
        }
        parameters[Parameters.PARAM_SYNC_COST_FUNCTION] = sync_cost_function

    _validate_costs(
        trace_cost_function,
        model_cost_function,
        sync_cost_function,
        len(activities),
        petri_net,
    )

    return _search(
        activities,
        petri_net,
        initial_marking,
        final_marking,
        semantics,
        trace_cost_function,
        model_cost_function,
        sync_cost_function,
        max_align_time_trace,
        ret_tuple_as_trans_desc,
    )


def apply_from_variant(
    variant,
    petri_net,
    initial_marking,
    final_marking,
    parameters=None,
):
    """Align a variant string to a Petri net."""
    trace = variants_util.variant_to_trace(variant, parameters=parameters)
    return apply(
        trace,
        petri_net,
        initial_marking,
        final_marking,
        parameters=parameters,
    )


def apply_from_variants_list(
    var_list,
    petri_net,
    initial_marking,
    final_marking,
    parameters=None,
):
    """Align each variant in a ``(variant, count)`` list."""
    if parameters is None:
        parameters = {}
    return {
        item[0]: apply_from_variant(
            item[0],
            petri_net,
            initial_marking,
            final_marking,
            parameters=dict(parameters),
        )
        for item in var_list
    }


def _cost_at(costs, index):
    return costs[index]


def _validate_costs(
    trace_cost_function,
    model_cost_function,
    sync_cost_function,
    trace_length,
    net,
):
    if len(trace_cost_function) != trace_length:
        raise ValueError("trace_cost_function must contain one cost per event")
    costs = [_cost_at(trace_cost_function, i) for i in range(trace_length)]
    try:
        costs.extend(model_cost_function[t] for t in net.transitions)
        costs.extend(
            sync_cost_function[t]
            for t in net.transitions
            if t.label is not None
        )
    except KeyError as exc:
        raise ValueError(
            "cost functions must define every applicable model transition"
        ) from exc
    if any(cost < 0 for cost in costs):
        raise ValueError("Dijkstra alignment costs must be non-negative")


def _queue_key(node, move_rank, serial):
    # Prefer progress in the trace and synchronous moves when costs are equal.
    return (node.cost, -node.index, move_rank, serial, node)


def _search(
    activities,
    net,
    initial_marking,
    final_marking,
    semantics,
    trace_cost_function,
    model_cost_function,
    sync_cost_function,
    max_align_time_trace,
    ret_tuple_as_trans_desc,
):
    started = time.time()
    serials = count()
    initial = _SearchNode(0, 0, initial_marking.copy())
    open_set = [_queue_key(initial, 0, next(serials))]
    best_cost = {(0, initial.marking): 0}
    closed = set()
    visited = 0
    queued = 0
    traversed = 0

    while open_set:
        if time.time() - started > max_align_time_trace:
            return None

        current = heapq.heappop(open_set)[-1]
        state = (current.index, current.marking)
        if state in closed or current.cost != best_cost.get(state):
            continue

        if (
            current.index == len(activities)
            and current.marking == final_marking
        ):
            return _reconstruct(
                current,
                visited,
                queued,
                traversed,
                ret_tuple_as_trans_desc,
            )

        closed.add(state)
        visited += 1
        enabled = semantics.enabled_transitions(net, current.marking)

        if current.index < len(activities):
            activity = activities[current.index]
            traversed += 1
            log_move = (activity, align_utils.SKIP)
            log_descriptor = (
                (f"trace_{current.index}", align_utils.SKIP),
                log_move,
            )
            log_node = _SearchNode(
                current.cost
                + _cost_at(trace_cost_function, current.index),
                current.index + 1,
                current.marking,
                current,
                log_move,
                log_descriptor,
            )
            queued += _push_if_better(
                open_set, best_cost, closed, log_node, 1, serials
            )

            for transition in enabled:
                if transition.label != activity:
                    continue
                traversed += 1
                new_marking = semantics.execute(
                    transition, net, current.marking
                )
                if new_marking is None:
                    continue
                sync_move = (activity, transition.label)
                sync_descriptor = (
                    (f"trace_{current.index}", transition.name),
                    sync_move,
                )
                sync_node = _SearchNode(
                    current.cost + sync_cost_function[transition],
                    current.index + 1,
                    new_marking,
                    current,
                    sync_move,
                    sync_descriptor,
                )
                queued += _push_if_better(
                    open_set, best_cost, closed, sync_node, 0, serials
                )

        for transition in enabled:
            traversed += 1
            new_marking = semantics.execute(transition, net, current.marking)
            if new_marking is None:
                continue
            model_move = (align_utils.SKIP, transition.label)
            model_descriptor = (
                (align_utils.SKIP, transition.name),
                model_move,
            )
            model_node = _SearchNode(
                current.cost + model_cost_function[transition],
                current.index,
                new_marking,
                current,
                model_move,
                model_descriptor,
            )
            queued += _push_if_better(
                open_set, best_cost, closed, model_node, 2, serials
            )

    return None


def _push_if_better(
    open_set, best_cost, closed, node, move_rank, serials
):
    state = (node.index, node.marking)
    if state in closed or node.cost >= best_cost.get(state, float("inf")):
        return 0
    best_cost[state] = node.cost
    heapq.heappush(
        open_set, _queue_key(node, move_rank, next(serials))
    )
    return 1


def _reconstruct(
    node,
    visited,
    queued,
    traversed,
    ret_tuple_as_trans_desc,
):
    cost = node.cost
    alignment = []
    while node.parent is not None:
        alignment.append(
            node.descriptor if ret_tuple_as_trans_desc else node.move
        )
        node = node.parent
    alignment.reverse()
    return {
        "alignment": alignment,
        "cost": cost,
        "visited_states": visited,
        "queued_states": queued,
        "traversed_arcs": traversed,
        "lp_solved": 0,
    }
