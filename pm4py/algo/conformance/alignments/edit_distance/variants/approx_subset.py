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
"""Subset-selection and edit-distance conformance approximation.

Implements Fani Sani, van Zelst, and van der Aalst, *Conformance Checking
Approximation using Subset Selection and Edit Distance* (CAiSE 2020).  In
addition to the paper's cost/fitness bounds, this variant retains each
representative's complete transition sequence and therefore returns a valid
Petri-net alignment (including silent transitions) for every trace.
"""

from collections import Counter
from dataclasses import dataclass
from enum import Enum
import math
import random
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from pm4py.algo.conformance.alignments.petri_net.utils import approx_utils
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.objects.log.obj import EventLog, Trace
from pm4py.objects.petri_net import semantics
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import align_utils
from pm4py.util import constants, exec_utils
from pm4py.util import typing


class Parameters(Enum):
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY
    SELECTION_METHOD = "selection_method"
    SUBSET_SIZE = "subset_size"
    SUBSET_FRACTION = "subset_fraction"
    RANDOM_SEED = "random_seed"
    K_MEDOIDS_MAX_ITERATIONS = "k_medoids_max_iterations"
    SIMULATION_MAX_TRACE_LENGTH = "simulation_max_trace_length"
    SIMULATION_MAX_ATTEMPTS = "simulation_max_attempts"
    PARAM_MAX_ALIGN_TIME_TRACE = "max_align_time_trace"
    MAX_EXPANSIONS = "max_expansions"
    PARAM_ALIGNMENT_RESULT_IS_SYNC_PROD_AWARE = "ret_tuple_as_trans_desc"


@dataclass
class _Representative:
    visible_trace: Tuple[Any, ...]
    transitions: Tuple[PetriNet.Transition, ...]
    source_variant: Optional[Tuple[Any, ...]]
    exact_steps: Optional[Tuple[approx_utils.AlignmentStep, ...]] = None
    visited_states: int = 0
    queued_states: int = 0
    traversed_arcs: int = 0


def apply(
    log: EventLog,
    net: PetriNet,
    im: Marking,
    fm: Marking,
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> typing.ListAlignments:
    if parameters is None:
        parameters = {}
    event_log = log_converter.apply(
        log,
        variant=log_converter.Variants.TO_EVENT_LOG,
        parameters=parameters,
    )
    activity_key = approx_utils.get_activity_key(parameters)
    variants = [tuple(event[activity_key] for event in trace) for trace in event_log]
    frequencies = Counter(variants)
    unique_variants = list(dict.fromkeys(variants))
    if not unique_variants:
        return []

    subset_size = exec_utils.get_param_value(
        Parameters.SUBSET_SIZE, parameters, None
    )
    if subset_size is None:
        fraction = exec_utils.get_param_value(
            Parameters.SUBSET_FRACTION, parameters, 0.1
        )
        if not 0 < fraction <= 1:
            raise ValueError("subset_fraction must be in (0, 1]")
        subset_size = max(1, math.ceil(len(unique_variants) * fraction))
    subset_size = max(1, min(int(subset_size), len(unique_variants)))
    method = exec_utils.get_param_value(
        Parameters.SELECTION_METHOD, parameters, "frequency"
    ).lower()
    max_time = exec_utils.get_param_value(
        Parameters.PARAM_MAX_ALIGN_TIME_TRACE, parameters, sys.maxsize
    )
    max_expansions = exec_utils.get_param_value(
        Parameters.MAX_EXPANSIONS, parameters, 100000
    )
    start_time = time.time()

    if method == "simulation":
        representatives = _simulate_representatives(
            net, im, fm, subset_size, parameters
        )
    else:
        selected = _select_variants(
            unique_variants, frequencies, subset_size, method, parameters
        )
        representatives = []
        for variant in selected:
            remaining_time = max_time - (time.time() - start_time)
            if remaining_time <= 0:
                break
            result = approx_utils.search_alignment(
                variant,
                net,
                im,
                fm,
                [align_utils.STD_MODEL_LOG_MOVE_COST] * len(variant),
                _standard_model_costs(net),
                _standard_sync_costs(net),
                max_time=remaining_time,
                max_expansions=max_expansions,
            )
            if result:
                representatives.append(
                    _representative_from_search(variant, result[0])
                )

    if not representatives:
        raise ValueError("no complete representative model trace could be constructed")

    shortest = approx_utils.search_alignment(
        [],
        net,
        im,
        fm,
        [],
        _standard_model_costs(net),
        _standard_sync_costs(net),
        max_time=max(0, max_time - (time.time() - start_time)),
        max_expansions=max_expansions,
    )
    shortest_path_exact = bool(shortest)
    shortest_visible_length = (
        sum(
            1
            for step in shortest[0].steps
            if step.transition is not None and step.transition.label is not None
        )
        if shortest
        else min(len(rep.visible_trace) for rep in representatives)
    )

    exact_by_variant = {
        representative.source_variant: representative
        for representative in representatives
        if representative.source_variant is not None
        and representative.exact_steps is not None
    }
    cache = {}
    ret_desc = exec_utils.get_param_value(
        Parameters.PARAM_ALIGNMENT_RESULT_IS_SYNC_PROD_AWARE,
        parameters,
        False,
    )
    aligned = []
    for variant in variants:
        if variant not in cache:
            exact_representative = exact_by_variant.get(variant)
            if exact_representative is not None:
                representative = exact_representative
                steps = representative.exact_steps
                selected_exact = True
            else:
                representative = min(
                    representatives,
                    key=lambda item: _edit_distance(
                        variant, item.visible_trace
                    ),
                )
                operations = _edit_operations(
                    variant, representative.visible_trace
                )
                steps = _materialize_alignment(
                    variant, representative.transitions, operations
                )
                selected_exact = False

            standard_cost = approx_utils.standard_cost(steps)
            denominator = len(variant) + shortest_visible_length
            upper_moves = standard_cost // align_utils.STD_MODEL_LOG_MOVE_COST
            lower_moves = (
                upper_moves
                if selected_exact
                else (
                    max(0, shortest_visible_length - len(variant))
                    if shortest_path_exact
                    else 0
                )
            )
            fitness_lower = (
                max(0.0, 1 - upper_moves / denominator)
                if denominator > 0
                else (1.0 if upper_moves == 0 else 0.0)
            )
            fitness_upper = (
                max(0.0, 1 - lower_moves / denominator)
                if denominator > 0
                else 1.0
            )
            result = {
                "alignment": approx_utils.format_alignment(steps, ret_desc),
                "cost": standard_cost,
                "standard_cost": standard_cost,
                "fitness": fitness_lower,
                "bwc": denominator * align_utils.STD_MODEL_LOG_MOVE_COST,
                "lower_bound_cost": (
                    standard_cost
                    if selected_exact
                    else lower_moves * align_utils.STD_MODEL_LOG_MOVE_COST
                ),
                "upper_bound_cost": standard_cost,
                "fitness_lower_bound": fitness_lower,
                "fitness_upper_bound": fitness_upper,
                "fitness_bounds_guaranteed": shortest_path_exact,
                "approximated_fitness": (
                    fitness_lower + fitness_upper
                )
                / 2,
                "is_valid": approx_utils.validate_steps(
                    variant, net, im, fm, steps
                ),
                "approximation_method": "subset_edit_distance",
                "bound_type": "valid_alignment_upper_bound",
                "selection_method": method,
                "subset_size": len(representatives),
                "selected_exact": selected_exact,
                "representative_variant": representative.visible_trace,
                "deviation_counts": _deviation_counts(steps),
                "visited_states": representative.visited_states
                if selected_exact
                else 0,
                "queued_states": representative.queued_states
                if selected_exact
                else 0,
                "traversed_arcs": representative.traversed_arcs
                if selected_exact
                else 0,
            }
            cache[variant] = result
        aligned.append(dict(cache[variant]))
    runtime = time.time() - start_time
    for result in aligned:
        result["runtime"] = runtime
    return aligned


def apply_with_summary(
    log: EventLog,
    net: PetriNet,
    im: Marking,
    fm: Marking,
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> Dict[str, Any]:
    """Return alignments together with paper-style aggregate bounds."""
    alignments = apply(log, net, im, fm, parameters=parameters)
    if not alignments:
        return {
            "alignments": [],
            "log_fitness": 1.0,
            "fitness_lower_bound": 1.0,
            "fitness_upper_bound": 1.0,
            "deviation_counts": {
                "insertions": {},
                "deletions": {},
                "synchronous": {},
            },
        }
    deviation_counts = {
        "insertions": Counter(),
        "deletions": Counter(),
        "synchronous": Counter(),
    }
    for alignment in alignments:
        for move_type, counts in alignment["deviation_counts"].items():
            deviation_counts[move_type].update(counts)
    return {
        "alignments": alignments,
        "log_fitness": sum(
            alignment["approximated_fitness"] for alignment in alignments
        )
        / len(alignments),
        "fitness_lower_bound": sum(
            alignment["fitness_lower_bound"] for alignment in alignments
        )
        / len(alignments),
        "fitness_upper_bound": sum(
            alignment["fitness_upper_bound"] for alignment in alignments
        )
        / len(alignments),
        "deviation_counts": {
            move_type: dict(counts)
            for move_type, counts in deviation_counts.items()
        },
    }


def _standard_model_costs(net):
    return {
        transition: (
            align_utils.STD_MODEL_LOG_MOVE_COST
            if transition.label is not None
            else align_utils.STD_TAU_COST
        )
        for transition in net.transitions
    }


def _standard_sync_costs(net):
    return {
        transition: align_utils.STD_SYNC_COST
        for transition in net.transitions
        if transition.label is not None
    }


def _representative_from_search(variant, result):
    transitions = tuple(
        step.transition
        for step in result.steps
        if step.transition is not None
    )
    visible = tuple(
        transition.label
        for transition in transitions
        if transition.label is not None
    )
    return _Representative(
        visible,
        transitions,
        tuple(variant),
        result.steps,
        result.visited_states,
        result.queued_states,
        result.traversed_arcs,
    )


def _select_variants(unique, frequencies, size, method, parameters):
    if method == "frequency":
        return sorted(
            unique,
            key=lambda variant: (-frequencies[variant], variant),
        )[:size]
    if method == "random":
        rng = random.Random(
            exec_utils.get_param_value(Parameters.RANDOM_SEED, parameters, 0)
        )
        return rng.sample(unique, size)
    if method in {"k_medoids", "k-medoids", "medoids"}:
        return _k_medoids(unique, frequencies, size, parameters)
    raise ValueError(
        "selection_method must be frequency, random, k_medoids, or simulation"
    )


def _k_medoids(unique, frequencies, size, parameters):
    medoids = sorted(
        unique, key=lambda variant: (-frequencies[variant], variant)
    )[:size]
    distance_cache = {}

    def distance(left, right):
        key = (left, right) if left <= right else (right, left)
        if key not in distance_cache:
            distance_cache[key] = _edit_distance(left, right)
        return distance_cache[key]

    max_iterations = exec_utils.get_param_value(
        Parameters.K_MEDOIDS_MAX_ITERATIONS, parameters, 10
    )
    for _ in range(max_iterations):
        clusters = {medoid: [] for medoid in medoids}
        for variant in unique:
            medoid = min(medoids, key=lambda item: distance(variant, item))
            clusters[medoid].append(variant)
        new_medoids = []
        for medoid, cluster in clusters.items():
            if not cluster:
                new_medoids.append(medoid)
                continue
            new_medoids.append(
                min(
                    cluster,
                    key=lambda candidate: sum(
                        frequencies[variant] * distance(candidate, variant)
                        for variant in cluster
                    ),
                )
            )
        if new_medoids == medoids:
            break
        medoids = new_medoids
    return medoids


def _simulate_representatives(net, im, fm, size, parameters):
    seed = exec_utils.get_param_value(Parameters.RANDOM_SEED, parameters, 0)
    rng = random.Random(seed)
    max_length = exec_utils.get_param_value(
        Parameters.SIMULATION_MAX_TRACE_LENGTH,
        parameters,
        max(100, 4 * len(net.transitions)),
    )
    max_attempts = exec_utils.get_param_value(
        Parameters.SIMULATION_MAX_ATTEMPTS, parameters, max(100, 20 * size)
    )
    representatives = []
    seen = set()
    for _ in range(max_attempts):
        marking = Marking(im)
        transitions = []
        for _step in range(max_length):
            if marking == fm:
                break
            enabled = list(semantics.enabled_transitions(net, marking))
            if not enabled:
                break
            transition = rng.choice(enabled)
            transitions.append(transition)
            marking = semantics.execute(transition, net, marking)
        if marking != fm:
            continue
        visible = tuple(
            transition.label
            for transition in transitions
            if transition.label is not None
        )
        if visible in seen:
            continue
        seen.add(visible)
        representatives.append(
            _Representative(visible, tuple(transitions), None)
        )
        if len(representatives) >= size:
            break
    return representatives


def _edit_distance(left: Sequence[Any], right: Sequence[Any]) -> int:
    previous = list(range(len(right) + 1))
    for i, left_value in enumerate(left, 1):
        current = [i]
        for j, right_value in enumerate(right, 1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1]
                    if left_value == right_value
                    else previous[j - 1] + 2,
                )
            )
        previous = current
    return previous[-1]


def _edit_operations(left: Sequence[Any], right: Sequence[Any]):
    rows = len(left) + 1
    columns = len(right) + 1
    costs = [[0] * columns for _ in range(rows)]
    for i in range(rows):
        costs[i][0] = i
    for j in range(columns):
        costs[0][j] = j
    for i in range(1, rows):
        for j in range(1, columns):
            costs[i][j] = min(
                costs[i - 1][j] + 1,
                costs[i][j - 1] + 1,
                costs[i - 1][j - 1]
                if left[i - 1] == right[j - 1]
                else costs[i - 1][j - 1] + 2,
            )
    operations = []
    i, j = len(left), len(right)
    while i or j:
        if (
            i
            and j
            and left[i - 1] == right[j - 1]
            and costs[i][j] == costs[i - 1][j - 1]
        ):
            operations.append(("sync", i - 1, j - 1))
            i -= 1
            j -= 1
        elif i and costs[i][j] == costs[i - 1][j] + 1:
            operations.append(("log", i - 1, None))
            i -= 1
        else:
            operations.append(("model", None, j - 1))
            j -= 1
    operations.reverse()
    return operations


def _materialize_alignment(log_variant, model_transitions, operations):
    visible_positions = [
        index
        for index, transition in enumerate(model_transitions)
        if transition.label is not None
    ]
    steps = []
    model_cursor = 0
    for operation, log_index, visible_index in operations:
        if visible_index is not None:
            transition_position = visible_positions[visible_index]
            while model_cursor < transition_position:
                transition = model_transitions[model_cursor]
                steps.append(
                    approx_utils.AlignmentStep(
                        None,
                        transition,
                        None,
                        align_utils.STD_TAU_COST,
                    )
                )
                model_cursor += 1
            transition = model_transitions[model_cursor]
            model_cursor += 1
            if operation == "sync":
                steps.append(
                    approx_utils.AlignmentStep(
                        log_variant[log_index], transition, log_index, 0
                    )
                )
            else:
                steps.append(
                    approx_utils.AlignmentStep(
                        None,
                        transition,
                        None,
                        align_utils.STD_MODEL_LOG_MOVE_COST,
                    )
                )
        else:
            steps.append(
                approx_utils.AlignmentStep(
                    log_variant[log_index],
                    None,
                    log_index,
                    align_utils.STD_MODEL_LOG_MOVE_COST,
                )
            )
    while model_cursor < len(model_transitions):
        transition = model_transitions[model_cursor]
        steps.append(
            approx_utils.AlignmentStep(
                None,
                transition,
                None,
                align_utils.STD_TAU_COST
                if transition.label is None
                else align_utils.STD_MODEL_LOG_MOVE_COST,
            )
        )
        model_cursor += 1
    return tuple(steps)


def _deviation_counts(steps: Iterable[approx_utils.AlignmentStep]):
    insertions = Counter()
    deletions = Counter()
    synchronous = Counter()
    for step in steps:
        if step.log_label is not None and step.transition is None:
            deletions[step.log_label] += 1
        elif (
            step.log_label is None
            and step.transition is not None
            and step.transition.label is not None
        ):
            insertions[step.transition.label] += 1
        elif step.log_label is not None and step.transition is not None:
            synchronous[step.log_label] += 1
    return {
        "insertions": dict(insertions),
        "deletions": dict(deletions),
        "synchronous": dict(synchronous),
    }
