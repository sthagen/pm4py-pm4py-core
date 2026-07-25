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
"""Sliding-window top-k approximate Petri-net alignments.

Implements the method of Bogdanov, Cohen, and Gal, *A Scalable and
Near-Optimal Conformance Checking Approach for Long Traces* (2024),
arXiv:2406.05439.  Intermediate windows may end in any model marking.  The
best paths with distinct endpoint markings are retained and ranked using the
paper's unreachable-future-activity lower bound.
"""

from dataclasses import dataclass
from enum import Enum
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from pm4py.algo.conformance.alignments.petri_net.utils import approx_utils
from pm4py.objects.log.obj import Trace
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import align_utils
from pm4py.util import constants, exec_utils, variants_util
from pm4py.util import typing


class Parameters(Enum):
    PARAM_TRACE_COST_FUNCTION = "trace_cost_function"
    PARAM_MODEL_COST_FUNCTION = "model_cost_function"
    PARAM_SYNC_COST_FUNCTION = "sync_cost_function"
    PARAM_MAX_ALIGN_TIME_TRACE = "max_align_time_trace"
    PARAM_ALIGNMENT_RESULT_IS_SYNC_PROD_AWARE = "ret_tuple_as_trans_desc"
    WINDOW_SIZE = "window_size"
    MAX_CANDIDATES = "max_candidates"
    MAX_EXPANSIONS = "max_expansions"
    MAX_POST_MODEL_MOVES = "max_post_model_moves"
    PARAMETER_VARIANT_DELIMITER = "variant_delimiter"
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY


@dataclass
class _Candidate:
    marking: Marking
    steps: Tuple[approx_utils.AlignmentStep, ...]
    cost: int
    score: int


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
    window_size = exec_utils.get_param_value(
        Parameters.WINDOW_SIZE, parameters, 20
    )
    max_candidates = exec_utils.get_param_value(
        Parameters.MAX_CANDIDATES, parameters, 5
    )
    max_expansions = exec_utils.get_param_value(
        Parameters.MAX_EXPANSIONS, parameters, 100000
    )
    max_post_model_moves = exec_utils.get_param_value(
        Parameters.MAX_POST_MODEL_MOVES,
        parameters,
        max(1, len(net.transitions)),
    )
    max_time = exec_utils.get_param_value(
        Parameters.PARAM_MAX_ALIGN_TIME_TRACE, parameters, sys.maxsize
    )
    if window_size < 1:
        raise ValueError("window_size must be at least one")
    if max_candidates < 1:
        raise ValueError("max_candidates must be at least one")

    start_time = time.time()
    candidates = [_Candidate(Marking(im), tuple(), 0, 0)]
    retained_counts: List[int] = []
    visited = 0
    queued = 0
    traversed = 0
    fallback_used = False
    windows = [
        (start, min(start + window_size, len(labels)))
        for start in range(0, len(labels), window_size)
    ]
    if not windows:
        windows = [(0, 0)]

    for window_number, (window_start, window_end) in enumerate(windows):
        is_last = window_number == len(windows) - 1
        extensions: List[_Candidate] = []
        remaining_labels = labels[window_end:]
        remaining_costs = trace_costs[window_end:]
        reachability_cache = {}

        def future_cost(marking):
            if marking not in reachability_cache:
                reachability_cache[marking] = (
                    approx_utils.structurally_reachable_labels(net, marking)
                )
            reachable = reachability_cache[marking]
            return sum(
                cost
                for label, cost in zip(remaining_labels, remaining_costs)
                if label not in reachable
            )

        for candidate in candidates:
            time_left = max_time - (time.time() - start_time)
            if time_left <= 0:
                break
            results = approx_utils.search_alignment(
                labels[window_start:window_end],
                net,
                candidate.marking,
                fm if is_last else None,
                trace_costs[window_start:window_end],
                model_costs,
                sync_costs,
                max_results=1 if is_last else max_candidates,
                future_cost=None if is_last else future_cost,
                max_time=time_left,
                max_expansions=max_expansions,
                max_post_model_moves=(0 if is_last else max_post_model_moves),
            )
            if results:
                visited += results[0].visited_states
                queued += results[0].queued_states
                traversed += results[0].traversed_arcs
            for result in results:
                extensions.append(
                    _Candidate(
                        result.marking,
                        candidate.steps + result.steps,
                        candidate.cost + result.cost,
                        candidate.cost
                        + result.cost
                        + result.future_lower_bound,
                    )
                )

        if not extensions:
            candidates = []
            break

        if is_last:
            candidates = sorted(
                extensions, key=lambda candidate: candidate.cost
            )[:1]
        else:
            by_marking = {}
            for extension in sorted(
                extensions,
                key=lambda candidate: (candidate.score, candidate.cost),
            ):
                if extension.marking not in by_marking:
                    by_marking[extension.marking] = extension
            candidates = list(by_marking.values())[:max_candidates]
        retained_counts.append(len(candidates))

    if not candidates:
        # A resource limit or a locally retained dead end must not turn an
        # approximation into an invalid alignment.  Try the ordinary direct
        # state-space search with the remaining budget.
        fallback_used = True
        time_left = max_time - (time.time() - start_time)
        results = approx_utils.search_alignment(
            labels,
            net,
            im,
            fm,
            trace_costs,
            model_costs,
            sync_costs,
            max_time=max(0, time_left),
            max_expansions=max_expansions,
        )
        if not results:
            return None
        result = results[0]
        candidates = [
            _Candidate(result.marking, result.steps, result.cost, result.cost)
        ]
        visited += result.visited_states
        queued += result.queued_states
        traversed += result.traversed_arcs

    chosen = min(candidates, key=lambda candidate: candidate.cost)
    search_result = approx_utils.SearchResult(
        chosen.steps,
        chosen.marking,
        chosen.cost,
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
        "sliding_window",
        ret_tuple_as_trans_desc=ret_desc,
    )
    result.update(
        {
            "window_size": window_size,
            "window_count": len(windows),
            "max_candidates": max_candidates,
            "retained_candidates": retained_counts,
            "fallback_used": fallback_used,
            "upper_bound": result["standard_cost"],
            "runtime": time.time() - start_time,
        }
    )
    return result


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
