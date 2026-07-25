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
"""Sequential fixed-horizon approximate alignments.

This is a PM4Py implementation of the ``(k, x)`` sequential alignment from
van Dongen, Carmona, Chatain, and Taymouri, *Aligning Modeled and Observed
Behavior: A Compromise Between Computation Complexity and Quality* (CAiSE
2017).  It enumerates the exact executable prefix of at most ``x`` product-net
moves and solves the paper's integer marking-equation tail for every candidate.
This is equivalent to the prefix/tail ILP formulation while avoiding binary
variables for prefixes that are not executable.
"""

from dataclasses import dataclass
from enum import Enum
import math
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from pm4py.algo.analysis.marking_equation.variants import classic as me_classic
from pm4py.algo.conformance.alignments.petri_net.utils import approx_utils
from pm4py.objects.log.obj import Trace
from pm4py.objects.petri_net import semantics
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import align_utils
from pm4py.objects.petri_net.utils.petri_utils import (
    construct_trace_net_cost_aware,
)
from pm4py.objects.petri_net.utils.synchronous_product import (
    construct_cost_aware,
)
from pm4py.util import constants, exec_utils, variants_util
from pm4py.util import typing
from pm4py.util.lp import solver as lp_solver


class Parameters(Enum):
    PARAM_TRACE_COST_FUNCTION = "trace_cost_function"
    PARAM_MODEL_COST_FUNCTION = "model_cost_function"
    PARAM_SYNC_COST_FUNCTION = "sync_cost_function"
    PARAM_MAX_ALIGN_TIME_TRACE = "max_align_time_trace"
    PARAM_ALIGNMENT_RESULT_IS_SYNC_PROD_AWARE = "ret_tuple_as_trans_desc"
    HORIZON = "horizon"
    MIN_PROGRESS = "min_progress"
    MAX_HORIZON = "max_horizon"
    MAX_PREFIX_STATES = "max_prefix_states"
    MAX_ITERATIONS = "max_iterations"
    MAX_EXPANSIONS = "max_expansions"
    PARAMETER_VARIANT_DELIMITER = "variant_delimiter"
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY


@dataclass
class _PrefixSolution:
    marking: Marking
    path: Tuple[PetriNet.Transition, ...]
    prefix_cost: int
    tail_cost: int
    progress: int
    visited: int
    queued: int
    traversed: int
    lp_solved: int

    @property
    def objective(self):
        return self.prefix_cost + self.tail_cost


def apply(
    trace: Trace,
    net: PetriNet,
    im: Marking,
    fm: Marking,
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> typing.AlignmentResult:
    if parameters is None:
        parameters = {}

    labels = approx_utils.trace_labels(trace, parameters)
    trace_costs, model_costs, sync_costs = approx_utils.get_cost_functions(
        trace, net, parameters
    )
    horizon = exec_utils.get_param_value(Parameters.HORIZON, parameters, 4)
    min_progress = exec_utils.get_param_value(
        Parameters.MIN_PROGRESS, parameters, 1
    )
    max_horizon = exec_utils.get_param_value(
        Parameters.MAX_HORIZON, parameters, max(20, horizon)
    )
    max_prefix_states = exec_utils.get_param_value(
        Parameters.MAX_PREFIX_STATES, parameters, 20000
    )
    max_iterations = exec_utils.get_param_value(
        Parameters.MAX_ITERATIONS,
        parameters,
        max(20, 2 * (len(trace) + len(net.transitions))),
    )
    max_time = exec_utils.get_param_value(
        Parameters.PARAM_MAX_ALIGN_TIME_TRACE, parameters, sys.maxsize
    )
    if horizon < 1 or min_progress < 0 or min_progress > horizon:
        raise ValueError("require 1 <= horizon and 0 <= min_progress <= horizon")
    if max_horizon < horizon:
        raise ValueError("max_horizon must not be smaller than horizon")

    trace_net, trace_im, trace_fm, trace_net_costs = (
        construct_trace_net_cost_aware(
            trace,
            trace_costs,
            activity_key=approx_utils.get_activity_key(parameters),
        )
    )
    revised_sync = {}
    for trace_transition in trace_net.transitions:
        for model_transition in net.transitions:
            if trace_transition.label == model_transition.label:
                revised_sync[(trace_transition, model_transition)] = (
                    sync_costs[model_transition]
                )
    sync_net, sync_im, sync_fm, product_costs = construct_cost_aware(
        trace_net,
        trace_im,
        trace_fm,
        net,
        im,
        fm,
        align_utils.SKIP,
        trace_net_costs,
        model_costs,
        revised_sync,
    )

    start_time = time.time()
    current = Marking(sync_im)
    product_path: Tuple[PetriNet.Transition, ...] = tuple()
    remaining_events = len(trace)
    previous_estimate = math.inf
    current_horizon = horizon
    current_progress = min(min_progress, remaining_events)
    committed_horizons: List[int] = []
    visited = 0
    queued = 0
    traversed = 0
    lp_solved = 0
    fallback_reason = None

    if lp_solver.DEFAULT_LP_SOLVER_VARIANT is None:
        fallback_reason = "no_lp_solver"
    else:
        for _iteration in range(max_iterations):
            if current == sync_fm:
                break
            time_left = max_time - (time.time() - start_time)
            if time_left <= 0:
                fallback_reason = "timeout"
                break

            solution = _solve_prefix(
                sync_net,
                current,
                sync_fm,
                product_costs,
                current_horizon,
                current_progress,
                max_prefix_states,
                time_left,
            )
            if solution is None:
                if current_horizon < max_horizon:
                    current_horizon += 1
                    current_progress = min(
                        current_progress + 1, remaining_events
                    )
                    continue
                fallback_reason = "no_prefix_solution"
                break

            visited += solution.visited
            queued += solution.queued
            traversed += solution.traversed
            lp_solved += solution.lp_solved

            if (
                solution.marking != sync_fm
                and previous_estimate < math.inf
                and solution.objective >= 2 * previous_estimate
                and current_horizon < max_horizon
            ):
                current_horizon += 1
                current_progress = min(
                    current_progress + 1, remaining_events
                )
                continue

            if not solution.path:
                fallback_reason = "prefix_made_no_progress"
                break
            product_path += solution.path
            current = Marking(solution.marking)
            remaining_events = max(0, remaining_events - solution.progress)
            previous_estimate = solution.tail_cost
            committed_horizons.append(current_horizon)
            current_progress = min(min_progress, remaining_events)
        else:
            fallback_reason = "maximum_iterations"

        if current != sync_fm and fallback_reason is None:
            fallback_reason = "incomplete_product_path"

    if fallback_reason is not None:
        # The approximation is allowed to be suboptimal, never invalid.
        time_left = max_time - (time.time() - start_time)
        fallback = approx_utils.search_alignment(
            labels,
            net,
            im,
            fm,
            trace_costs,
            model_costs,
            sync_costs,
            max_time=max(0, time_left),
            max_expansions=exec_utils.get_param_value(
                Parameters.MAX_EXPANSIONS, parameters, 100000
            ),
        )
        if not fallback:
            return None
        direct = fallback[0]
        visited += direct.visited_states
        queued += direct.queued_states
        traversed += direct.traversed_arcs
        steps = direct.steps
        custom_cost = direct.cost
    else:
        steps = _translate_product_path(product_path, net, im, product_costs)
        custom_cost = sum(product_costs[transition] for transition in product_path)

    search_result = approx_utils.SearchResult(
        steps,
        Marking(fm),
        custom_cost,
        visited,
        queued,
        traversed,
    )
    ret_desc = exec_utils.get_param_value(
        Parameters.PARAM_ALIGNMENT_RESULT_IS_SYNC_PROD_AWARE,
        parameters,
        False,
    )
    result = approx_utils.result_dictionary(
        search_result,
        labels,
        net,
        im,
        fm,
        "fixed_horizon",
        ret_tuple_as_trans_desc=ret_desc,
    )
    result.update(
        {
            "horizon": horizon,
            "min_progress": min_progress,
            "committed_horizons": committed_horizons,
            "lp_solved": lp_solved,
            "fallback_used": fallback_reason is not None,
            "fallback_reason": fallback_reason,
            "upper_bound": result["standard_cost"],
            "runtime": time.time() - start_time,
        }
    )
    return result


def _solve_prefix(
    sync_net: PetriNet,
    initial_marking: Marking,
    final_marking: Marking,
    costs: Dict[PetriNet.Transition, int],
    horizon: int,
    min_progress: int,
    max_states: int,
    max_time: float,
) -> Optional[_PrefixSolution]:
    start_time = time.time()
    counter = 0
    # cost, negative progress, depth, counter, marking, path, progress
    queue = [(0, 0, 0, counter, Marking(initial_marking), tuple(), 0)]
    best = {(Marking(initial_marking), 0): 0}
    tail_cache = {}
    chosen = None
    visited = 0
    queued = 1
    traversed = 0
    lp_solved = 0

    while queue and visited < max_states and time.time() - start_time <= max_time:
        import heapq

        cost, negative_progress, depth, _, marking, path, progress = heapq.heappop(
            queue
        )
        if cost != best.get((marking, depth)):
            continue
        visited += 1

        is_final = marking == final_marking
        if is_final or (path and progress >= min_progress):
            if is_final:
                tail_cost = 0
            else:
                if marking not in tail_cache:
                    tail_cache[marking] = _integer_tail_cost(
                        sync_net, marking, final_marking, costs
                    )
                    lp_solved += 1
                tail_cost = tail_cache[marking]
            if tail_cost is not None:
                candidate = _PrefixSolution(
                    Marking(marking),
                    path,
                    cost,
                    tail_cost,
                    progress,
                    visited,
                    queued,
                    traversed,
                    lp_solved,
                )
                if chosen is None or (
                    candidate.objective,
                    -candidate.progress,
                    len(candidate.path),
                ) < (
                    chosen.objective,
                    -chosen.progress,
                    len(chosen.path),
                ):
                    chosen = candidate

        if depth >= horizon or is_final:
            continue
        for transition in sorted(
            semantics.enabled_transitions(sync_net, marking),
            key=lambda transition: (
                costs[transition],
                str(transition.name),
                id(transition),
            ),
        ):
            traversed += 1
            new_marking = semantics.execute(transition, sync_net, marking)
            new_cost = cost + costs[transition]
            new_progress = progress + (
                1 if transition.label[0] != align_utils.SKIP else 0
            )
            key = (new_marking, depth + 1)
            if new_cost >= best.get(key, sys.maxsize):
                continue
            best[key] = new_cost
            counter += 1
            heapq.heappush(
                queue,
                (
                    new_cost,
                    -new_progress,
                    depth + 1,
                    counter,
                    new_marking,
                    path + (transition,),
                    new_progress,
                ),
            )
            queued += 1

    if chosen is not None:
        chosen.visited = visited
        chosen.queued = queued
        chosen.traversed = traversed
        chosen.lp_solved = lp_solved
    return chosen


def _integer_tail_cost(
    net: PetriNet,
    im: Marking,
    fm: Marking,
    costs: Dict[PetriNet.Transition, int],
) -> Optional[int]:
    marking_solver = me_classic.MarkingEquationSolver(
        net, im, fm, parameters={"costs": costs}
    )
    c, aub, bub, aeq, beq = marking_solver.get_components()
    variable_count = len(c)
    parameters = {
        "require_ilp": True,
        "integrality": [1] * variable_count,
        "bounds": [(0, None)] * variable_count,
        "method": "highs",
    }
    solution = lp_solver.apply(
        c,
        aub,
        bub,
        aeq,
        beq,
        parameters=parameters,
        variant=lp_solver.DEFAULT_LP_SOLVER_VARIANT,
    )
    points = lp_solver.get_points_from_sol(
        solution,
        parameters=parameters,
        variant=lp_solver.DEFAULT_LP_SOLVER_VARIANT,
    )
    if points is None:
        return None
    return int(round(sum(value * coefficient for value, coefficient in zip(points, c))))


def _translate_product_path(
    path: Sequence[PetriNet.Transition],
    model: PetriNet,
    initial_marking: Marking,
    costs: Dict[PetriNet.Transition, int],
) -> Tuple[approx_utils.AlignmentStep, ...]:
    marking = Marking(initial_marking)
    steps = []
    log_index = 0
    for product_transition in path:
        log_label, model_label = product_transition.label
        transition = None
        if model_label != align_utils.SKIP:
            model_name = product_transition.name[1]
            candidates = [
                candidate
                for candidate in model.transitions
                if candidate.name == model_name
                and candidate.label == model_label
                and semantics.is_enabled(candidate, model, marking)
            ]
            if not candidates:
                candidates = [
                    candidate
                    for candidate in model.transitions
                    if candidate.label == model_label
                    and semantics.is_enabled(candidate, model, marking)
                ]
            if not candidates:
                raise ValueError("product alignment cannot be replayed on the model")
            transition = sorted(candidates, key=lambda item: str(item.name))[0]
            marking = semantics.execute(transition, model, marking)
        actual_log_label = (
            None if log_label == align_utils.SKIP else log_label
        )
        steps.append(
            approx_utils.AlignmentStep(
                actual_log_label,
                transition,
                log_index if actual_log_label is not None else None,
                costs[product_transition],
            )
        )
        if actual_log_label is not None:
            log_index += 1
    return tuple(steps)


def get_best_worst_cost(
    net: PetriNet,
    im: Marking,
    fm: Marking,
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
):
    bwc_parameters = {
        key: value
        for key, value in (parameters or {}).items()
        if exec_utils.unroll(key) != "trace_cost_function"
    }
    result = apply(Trace(), net, im, fm, parameters=bwc_parameters)
    return result["cost"] if result is not None else None


def apply_from_variant(
    variant,
    net: PetriNet,
    im: Marking,
    fm: Marking,
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
):
    trace = variants_util.variant_to_trace(variant, parameters=parameters)
    return apply(trace, net, im, fm, parameters=parameters)
