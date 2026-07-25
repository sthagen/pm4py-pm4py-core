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
"""Approximate alignments based on tandem-repeat compression.

Implements the reduce-align-expand scheme from Reißner, Armas-Cervantes,
and La Rosa, *Efficient Conformance Checking using Approximate Alignment
Computation with Tandem Repeats* (2022), arXiv:2004.01781.

The generic Petri-net implementation validates the expanded firing sequence.
When a retained repeat copy is a model loop, it is replayed for the removed
copies.  Otherwise, the removed events are restored as log moves, which keeps
the result executable on arbitrary labelled Petri nets.
"""

from dataclasses import dataclass
from enum import Enum
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from pm4py.algo.conformance.alignments.petri_net.utils import approx_utils
from pm4py.objects.log.obj import Trace
from pm4py.objects.petri_net import semantics
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.util import constants, exec_utils, variants_util
from pm4py.util import typing


class Parameters(Enum):
    PARAM_TRACE_COST_FUNCTION = "trace_cost_function"
    PARAM_MODEL_COST_FUNCTION = "model_cost_function"
    PARAM_SYNC_COST_FUNCTION = "sync_cost_function"
    PARAM_MAX_ALIGN_TIME_TRACE = "max_align_time_trace"
    PARAM_ALIGNMENT_RESULT_IS_SYNC_PROD_AWARE = "ret_tuple_as_trans_desc"
    MAX_EXPANSIONS = "max_expansions"
    PARAMETER_VARIANT_DELIMITER = "variant_delimiter"
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY


@dataclass(frozen=True)
class TandemRepeat:
    original_start: int
    reduced_start: int
    period: Tuple[Any, ...]
    repetitions: int

    @property
    def removed_events(self) -> int:
        return (self.repetitions - 2) * len(self.period)


def _is_primitive(block: Sequence[Any]) -> bool:
    size = len(block)
    for period in range(1, size):
        if size % period == 0 and list(block) == list(block[:period]) * (
            size // period
        ):
            return False
    return True


def reduce_tandem_repeats(
    labels: Sequence[Any],
) -> Tuple[List[Any], List[int], List[TandemRepeat]]:
    """Greedily reduce non-overlapping maximal primitive tandem repeats.

    Runs with three or more copies are collapsed to the two copies needed by
    the repeat-aware reconstruction.
    """
    labels = list(labels)
    reduced: List[Any] = []
    kept_indices: List[int] = []
    repeats: List[TandemRepeat] = []
    index = 0

    while index < len(labels):
        best = None
        max_period = (len(labels) - index) // 3
        for period_length in range(1, max_period + 1):
            period = labels[index : index + period_length]
            if not _is_primitive(period):
                continue
            repetitions = 1
            while (
                index + (repetitions + 1) * period_length <= len(labels)
                and labels[
                    index + repetitions * period_length :
                    index + (repetitions + 1) * period_length
                ]
                == period
            ):
                repetitions += 1
            if repetitions < 3:
                continue
            saved = (repetitions - 2) * period_length
            candidate = (saved, repetitions * period_length, -period_length)
            if best is None or candidate > best[0]:
                best = (candidate, period_length, repetitions, tuple(period))

        if best is None:
            reduced.append(labels[index])
            kept_indices.append(index)
            index += 1
            continue

        _, period_length, repetitions, period = best
        repeats.append(
            TandemRepeat(
                original_start=index,
                reduced_start=len(reduced),
                period=period,
                repetitions=repetitions,
            )
        )
        first_and_last = list(range(index, index + period_length)) + list(
            range(
                index + (repetitions - 1) * period_length,
                index + repetitions * period_length,
            )
        )
        for original_index in first_and_last:
            reduced.append(labels[original_index])
            kept_indices.append(original_index)
        index += repetitions * period_length

    return reduced, kept_indices, repeats


def apply(
    trace: Trace,
    net: PetriNet,
    im: Marking,
    fm: Marking,
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> typing.AlignmentResult:
    if parameters is None:
        parameters = {}
    start_time = time.time()

    labels = approx_utils.trace_labels(trace, parameters)
    trace_costs, model_costs, sync_costs = approx_utils.get_cost_functions(
        trace, net, parameters
    )
    reduced_labels, kept_indices, repeats = reduce_tandem_repeats(labels)
    reduced_costs = [trace_costs[index] for index in kept_indices]
    max_time = exec_utils.get_param_value(
        Parameters.PARAM_MAX_ALIGN_TIME_TRACE, parameters, sys.maxsize
    )
    max_expansions = exec_utils.get_param_value(
        Parameters.MAX_EXPANSIONS, parameters, 100000
    )

    search_results = approx_utils.search_alignment(
        reduced_labels,
        net,
        im,
        fm,
        reduced_costs,
        model_costs,
        sync_costs,
        max_time=max_time,
        max_expansions=max_expansions,
    )
    if not search_results:
        return None

    reduced_result = search_results[0]
    steps, loop_expansions = _expand_repeats(
        reduced_result.steps,
        repeats,
        im,
        trace_costs,
        sync_costs,
        prefer_model_loops=True,
    )
    if not approx_utils.validate_steps(labels, net, im, fm, steps):
        steps, loop_expansions = _expand_repeats(
            reduced_result.steps,
            repeats,
            im,
            trace_costs,
            sync_costs,
            prefer_model_loops=False,
        )

    expanded_result = approx_utils.SearchResult(
        steps=steps,
        marking=Marking(fm),
        cost=sum(step.cost for step in steps),
        visited_states=reduced_result.visited_states,
        queued_states=reduced_result.queued_states,
        traversed_arcs=reduced_result.traversed_arcs,
    )
    ret_desc = exec_utils.get_param_value(
        Parameters.PARAM_ALIGNMENT_RESULT_IS_SYNC_PROD_AWARE,
        parameters,
        False,
    )
    result = approx_utils.result_dictionary(
        expanded_result,
        labels,
        net,
        im,
        fm,
        "tandem_repeats",
        ret_tuple_as_trans_desc=ret_desc,
    )
    result.update(
        {
            "reduced_trace_length": len(reduced_labels),
            "original_trace_length": len(labels),
            "tandem_repeats": len(repeats),
            "removed_events": sum(r.removed_events for r in repeats),
            "model_loop_expansions": loop_expansions,
            "upper_bound": result["standard_cost"],
            "runtime": time.time() - start_time,
        }
    )
    return result


def _expand_repeats(
    reduced_steps: Tuple[approx_utils.AlignmentStep, ...],
    repeats: Sequence[TandemRepeat],
    initial_marking: Marking,
    original_trace_costs: Sequence[int],
    sync_costs: Dict[PetriNet.Transition, int],
    prefer_model_loops: bool,
) -> Tuple[Tuple[approx_utils.AlignmentStep, ...], int]:
    steps = list(reduced_steps)
    loop_expansions = 0

    # Right-to-left insertion preserves the reduced trace indexes used to find
    # the boundaries of repeats that have not yet been expanded.
    for repeat in reversed(repeats):
        period_length = len(repeat.period)
        start_position = next(
            index
            for index, step in enumerate(steps)
            if step.log_index == repeat.reduced_start
        )
        first_end = next(
            index + 1
            for index, step in enumerate(steps)
            if step.log_index == repeat.reduced_start + period_length - 1
        )
        insertion_position = first_end
        first_copy = steps[start_position:first_end]

        use_loop = prefer_model_loops and _is_model_loop(
            steps, start_position, first_end, initial_marking
        )
        inserted = []
        for removed_copy in range(repeat.repetitions - 2):
            if use_loop:
                for step in first_copy:
                    if step.log_label is None:
                        inserted.append(step)
                    else:
                        offset = step.log_index - repeat.reduced_start
                        original_index = (
                            repeat.original_start
                            + (removed_copy + 1) * period_length
                            + offset
                        )
                        move_cost = (
                            sync_costs.get(step.transition, 0)
                            if step.transition is not None
                            else original_trace_costs[original_index]
                        )
                        inserted.append(
                            approx_utils.AlignmentStep(
                                step.log_label,
                                step.transition,
                                None,
                                move_cost,
                            )
                        )
                loop_expansions += 1
            else:
                copy_number = removed_copy + 1
                for offset, label in enumerate(repeat.period):
                    original_index = (
                        repeat.original_start
                        + copy_number * period_length
                        + offset
                    )
                    inserted.append(
                        approx_utils.AlignmentStep(
                            label,
                            None,
                            None,
                            original_trace_costs[original_index],
                        )
                    )
        steps[insertion_position:insertion_position] = inserted

    return tuple(steps), loop_expansions


def _is_model_loop(
    steps: Sequence[approx_utils.AlignmentStep],
    start: int,
    end: int,
    initial_marking: Marking,
) -> bool:
    marking = Marking(initial_marking)
    for step in steps[:start]:
        if step.transition is not None:
            marking = semantics.weak_execute(step.transition, marking)
    loop_start = Marking(marking)
    for step in steps[start:end]:
        if step.transition is not None:
            marking = semantics.weak_execute(step.transition, marking)
    return marking == loop_start


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
