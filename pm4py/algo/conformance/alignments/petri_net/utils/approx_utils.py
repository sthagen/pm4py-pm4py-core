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
"""Shared primitives for approximate Petri-net alignments.

The routines in this module deliberately search the original model instead of
constructing a synchronous-product net.  Besides using less memory, this makes
it possible to stop after a trace fragment and retain the reached model
marking, which is needed by the sliding-window and fixed-horizon variants.
"""

from dataclasses import dataclass
import heapq
import sys
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from pm4py.objects.petri_net import semantics
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import align_utils
from pm4py.util import constants, exec_utils
from pm4py.util.xes_constants import DEFAULT_NAME_KEY


@dataclass(frozen=True)
class AlignmentStep:
    """One executable alignment step.

    ``transition`` is kept as an object (and not only as a label) so callers
    can validate and safely compose approximate alignment fragments.
    """

    log_label: Optional[Any]
    transition: Optional[PetriNet.Transition]
    log_index: Optional[int]
    cost: int


@dataclass
class SearchResult:
    steps: Tuple[AlignmentStep, ...]
    marking: Marking
    cost: int
    visited_states: int
    queued_states: int
    traversed_arcs: int
    future_lower_bound: int = 0


def get_activity_key(parameters: Optional[Dict[Any, Any]]) -> str:
    return exec_utils.get_param_value(
        constants.PARAMETER_CONSTANT_ACTIVITY_KEY,
        parameters or {},
        exec_utils.get_param_value(
            "activity_key", parameters or {}, DEFAULT_NAME_KEY
        ),
    )


def trace_labels(
    trace: Sequence[Any], parameters: Optional[Dict[Any, Any]] = None
) -> List[Any]:
    activity_key = get_activity_key(parameters)
    return [event[activity_key] for event in trace]


def get_cost_functions(
    trace: Sequence[Any],
    net: PetriNet,
    parameters: Optional[Dict[Any, Any]] = None,
) -> Tuple[List[int], Dict[PetriNet.Transition, int], Dict[PetriNet.Transition, int]]:
    """Return PM4Py-compatible trace, model, and synchronous costs."""
    if parameters is None:
        parameters = {}

    trace_costs = exec_utils.get_param_value(
        "trace_cost_function", parameters, None
    )
    if trace_costs is None:
        trace_costs = [align_utils.STD_MODEL_LOG_MOVE_COST] * len(trace)
        parameters["trace_cost_function"] = trace_costs
    elif isinstance(trace_costs, dict):
        trace_costs = [trace_costs[i] for i in range(len(trace))]
    else:
        trace_costs = list(trace_costs)

    if len(trace_costs) != len(trace):
        raise ValueError("trace_cost_function must contain one cost per event")

    model_costs = exec_utils.get_param_value(
        "model_cost_function", parameters, None
    )
    if model_costs is None:
        model_costs = {
            transition: (
                align_utils.STD_MODEL_LOG_MOVE_COST
                if transition.label is not None
                else align_utils.STD_TAU_COST
            )
            for transition in net.transitions
        }
        parameters["model_cost_function"] = model_costs

    sync_costs = exec_utils.get_param_value(
        "sync_cost_function", parameters, None
    )
    if sync_costs is None:
        sync_costs = {
            transition: align_utils.STD_SYNC_COST
            for transition in net.transitions
            if transition.label is not None
        }
        parameters["sync_cost_function"] = sync_costs

    return trace_costs, model_costs, sync_costs


def search_alignment(
    labels: Sequence[Any],
    net: PetriNet,
    initial_marking: Marking,
    final_marking: Optional[Marking],
    trace_costs: Sequence[int],
    model_costs: Dict[PetriNet.Transition, int],
    sync_costs: Dict[PetriNet.Transition, int],
    max_results: int = 1,
    future_cost: Optional[Callable[[Marking], int]] = None,
    max_time: float = sys.maxsize,
    max_expansions: int = 100000,
    max_post_model_moves: int = 0,
) -> List[SearchResult]:
    """Search alignments from an arbitrary model marking.

    If ``final_marking`` is ``None``, consuming all events is sufficient and
    up to ``max_results`` paths ending in distinct model markings are returned.
    Otherwise, the single conventional final marking is required.
    """
    if max_results < 1:
        raise ValueError("max_results must be at least one")
    if future_cost is None:
        future_cost = lambda _marking: 0

    start_time = time.time()
    counter = 0
    initial = Marking(initial_marking)
    initial_h = future_cost(initial) if final_marking is None else 0
    # priority, negative trace index, path length, counter, g, marking, path,
    # number of model moves made after the fragment was consumed
    open_set = [
        (initial_h, 0, 0, counter, 0, initial, tuple(), 0)
    ]
    best_cost: Dict[Tuple[int, Marking], int] = {(0, initial): 0}
    results: List[SearchResult] = []
    result_markings = set()
    visited = 0
    queued = 1
    traversed = 0

    while open_set and visited < max_expansions:
        if time.time() - start_time > max_time:
            break

        (
            _priority,
            negative_index,
            _path_length,
            _counter,
            cost,
            marking,
            path,
            post_model_moves,
        ) = heapq.heappop(open_set)
        index = -negative_index
        if cost != best_cost.get((index, marking)):
            continue
        visited += 1

        consumed = index == len(labels)
        if consumed and (
            final_marking is None or marking == final_marking
        ):
            if marking not in result_markings:
                lower_bound = future_cost(marking) if final_marking is None else 0
                results.append(
                    SearchResult(
                        path,
                        Marking(marking),
                        cost,
                        visited,
                        queued,
                        traversed,
                        lower_bound,
                    )
                )
                result_markings.add(marking)
                if len(results) >= max_results:
                    break
            if final_marking is not None:
                break

        enabled = sorted(
            semantics.enabled_transitions(net, marking),
            key=lambda transition: (
                str(transition.label),
                str(transition.name),
                id(transition),
            ),
        )

        if not consumed:
            current_label = labels[index]
            for transition in enabled:
                if transition.label == current_label:
                    traversed += 1
                    new_marking = semantics.execute(transition, net, marking)
                    new_cost = cost + sync_costs.get(
                        transition, align_utils.STD_SYNC_COST
                    )
                    step = AlignmentStep(
                        current_label, transition, index, sync_costs.get(
                            transition, align_utils.STD_SYNC_COST
                        )
                    )
                    counter += 1
                    was_queued = _queue_state(
                        open_set,
                        best_cost,
                        counter,
                        index + 1,
                        new_marking,
                        new_cost,
                        path + (step,),
                        0,
                        future_cost if final_marking is None else None,
                    )
                    if was_queued:
                        queued += 1

            traversed += 1
            log_cost = trace_costs[index]
            counter += 1
            was_queued = _queue_state(
                open_set,
                best_cost,
                counter,
                index + 1,
                marking,
                cost + log_cost,
                path + (AlignmentStep(current_label, None, index, log_cost),),
                0,
                future_cost if final_marking is None else None,
            )
            if was_queued:
                queued += 1

        allow_model_moves = (
            not consumed
            or final_marking is not None
            or post_model_moves < max_post_model_moves
        )
        if allow_model_moves:
            for transition in enabled:
                traversed += 1
                new_marking = semantics.execute(transition, net, marking)
                move_cost = model_costs[transition]
                counter += 1
                was_queued = _queue_state(
                    open_set,
                    best_cost,
                    counter,
                    index,
                    new_marking,
                    cost + move_cost,
                    path
                    + (AlignmentStep(None, transition, None, move_cost),),
                    post_model_moves + 1 if consumed else 0,
                    future_cost if final_marking is None else None,
                )
                if was_queued:
                    queued += 1

    for result in results:
        result.visited_states = visited
        result.queued_states = queued
        result.traversed_arcs = traversed
    results.sort(key=lambda result: (result.cost + result.future_lower_bound, result.cost))
    return results


def _queue_state(
    open_set,
    best_cost,
    counter,
    index,
    marking,
    cost,
    path,
    post_model_moves,
    future_cost,
):
    key = (index, marking)
    if cost >= best_cost.get(key, sys.maxsize):
        return False
    best_cost[key] = cost
    heuristic = future_cost(marking) if future_cost is not None else 0
    heapq.heappush(
        open_set,
        (
            cost + heuristic,
            -index,
            len(path),
            counter,
            cost,
            marking,
            path,
            post_model_moves,
        ),
    )
    return True


def structurally_reachable_labels(
    net: PetriNet, marking: Marking
) -> frozenset:
    """Return a safe structural over-approximation of reachable labels."""
    places = set(marking.keys())
    transitions = {
        transition for transition in net.transitions if not transition.in_arcs
    }
    frontier = list(places)
    while frontier:
        place = frontier.pop()
        for arc in place.out_arcs:
            transition = arc.target
            if transition in transitions:
                continue
            transitions.add(transition)
            for out_arc in transition.out_arcs:
                target = out_arc.target
                if target not in places:
                    places.add(target)
                    frontier.append(target)
    return frozenset(
        transition.label
        for transition in transitions
        if transition.label is not None
    )


def validate_steps(
    labels: Sequence[Any],
    net: PetriNet,
    initial_marking: Marking,
    final_marking: Optional[Marking],
    steps: Iterable[AlignmentStep],
) -> bool:
    """Validate both projections and every model firing in an alignment."""
    projected = []
    marking = Marking(initial_marking)
    for step in steps:
        if step.log_label is not None:
            projected.append(step.log_label)
        if step.transition is not None:
            if not semantics.is_enabled(step.transition, net, marking):
                return False
            marking = semantics.execute(step.transition, net, marking)
        if (
            step.log_label is not None
            and step.transition is not None
            and step.log_label != step.transition.label
        ):
            return False
    return projected == list(labels) and (
        final_marking is None or marking == final_marking
    )


def standard_cost(steps: Iterable[AlignmentStep]) -> int:
    cost = 0
    for step in steps:
        if step.log_label is not None and step.transition is None:
            cost += align_utils.STD_MODEL_LOG_MOVE_COST
        elif step.log_label is None and step.transition is not None:
            cost += (
                align_utils.STD_MODEL_LOG_MOVE_COST
                if step.transition.label is not None
                else align_utils.STD_TAU_COST
            )
    return cost


def format_alignment(
    steps: Iterable[AlignmentStep], ret_tuple_as_trans_desc: bool = False
) -> List[Any]:
    alignment = []
    for step in steps:
        log_label = (
            step.log_label if step.log_label is not None else align_utils.SKIP
        )
        if step.transition is None:
            model_name = align_utils.SKIP
            model_label = align_utils.SKIP
        else:
            model_name = step.transition.name
            model_label = step.transition.label
        if ret_tuple_as_trans_desc:
            log_name = log_label
            alignment.append(
                ((log_name, model_name), (log_label, model_label))
            )
        else:
            alignment.append((log_label, model_label))
    return alignment


def result_dictionary(
    result: SearchResult,
    labels: Sequence[Any],
    net: PetriNet,
    initial_marking: Marking,
    final_marking: Marking,
    approximation_method: str,
    ret_tuple_as_trans_desc: bool = False,
) -> Dict[str, Any]:
    steps = result.steps
    return {
        "alignment": format_alignment(steps, ret_tuple_as_trans_desc),
        "cost": result.cost,
        "standard_cost": standard_cost(steps),
        "visited_states": result.visited_states,
        "queued_states": result.queued_states,
        "traversed_arcs": result.traversed_arcs,
        "is_valid": validate_steps(
            labels, net, initial_marking, final_marking, steps
        ),
        "approximation_method": approximation_method,
        "bound_type": "valid_alignment_upper_bound",
    }
