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
"""IWS trie-based online approximate alignments with decay time.

Implements the event-by-event approach from Raun and Awad, *I Will Survive:
An Online Conformance Checking Algorithm Using Decay Time* (2022),
arXiv:2211.16702.  A finite proxy of model behavior is stored in a trie;
look-ahead generates alternative states and fixed/discounted decay bounds the
per-case state buffer.
"""

from dataclasses import dataclass, field
from enum import Enum
import random
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from pm4py.algo.conformance.alignments.petri_net.utils import approx_utils
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net import semantics
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import align_utils
from pm4py.streaming.algo.interface import StreamingAlgorithm
from pm4py.util import constants, exec_utils, xes_constants


class Parameters(Enum):
    CASE_ID_KEY = constants.PARAMETER_CONSTANT_CASEID_KEY
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY
    PROXY_LOG = "proxy_log"
    PROXY_TRACES = "proxy_traces"
    MAX_TRACE_LENGTH = "max_trace_length"
    MAX_SIMULATION_ATTEMPTS = "max_simulation_attempts"
    RANDOM_SEED = "random_seed"
    LOOK_AHEAD = "look_ahead"
    DECAY_TIME = "decay_time"
    DISCOUNT_FACTOR = "discount_factor"
    MAX_STATES = "max_states"
    COMPLETE_CASE_ATTRIBUTE = "complete_case_attribute"
    PARAM_MAX_ALIGN_TIME_TRACE = "max_align_time_trace"
    MAX_EXPANSIONS = "max_expansions"
    PARAM_ALIGNMENT_RESULT_IS_SYNC_PROD_AWARE = "ret_tuple_as_trans_desc"


@dataclass(eq=False)
class _TrieNode:
    identifier: int
    label: Optional[Any] = None
    parent: Optional["_TrieNode"] = None
    segment: Tuple[PetriNet.Transition, ...] = tuple()
    children: Dict[Any, "_TrieNode"] = field(default_factory=dict)
    final: bool = False
    trailing_options: List[Tuple[PetriNet.Transition, ...]] = field(
        default_factory=list
    )

    def __hash__(self):
        return self.identifier


@dataclass
class _State:
    node: _TrieNode
    steps: Tuple[approx_utils.AlignmentStep, ...]
    cost: int
    decay: float


class IWSStreamingAlignments(StreamingAlgorithm):
    def __init__(self, net, im, fm, parameters=None):
        if parameters is None:
            parameters = {}
        self.net = net
        self.im = Marking(im)
        self.fm = Marking(fm)
        self.case_id_key = exec_utils.get_param_value(
            Parameters.CASE_ID_KEY, parameters, constants.CASE_CONCEPT_NAME
        )
        self.activity_key = exec_utils.get_param_value(
            Parameters.ACTIVITY_KEY, parameters, xes_constants.DEFAULT_NAME_KEY
        )
        self.look_ahead = exec_utils.get_param_value(
            Parameters.LOOK_AHEAD, parameters, 3
        )
        self.decay_time = exec_utils.get_param_value(
            Parameters.DECAY_TIME, parameters, 10
        )
        self.discount_factor = exec_utils.get_param_value(
            Parameters.DISCOUNT_FACTOR, parameters, 0.9
        )
        self.max_states = exec_utils.get_param_value(
            Parameters.MAX_STATES, parameters, 20
        )
        self.complete_case_attribute = exec_utils.get_param_value(
            Parameters.COMPLETE_CASE_ATTRIBUTE, parameters, "@@complete"
        )
        self.ret_desc = exec_utils.get_param_value(
            Parameters.PARAM_ALIGNMENT_RESULT_IS_SYNC_PROD_AWARE,
            parameters,
            False,
        )
        if self.look_ahead < 1 or self.decay_time <= 0 or self.max_states < 1:
            raise ValueError(
                "look_ahead, decay_time, and max_states must be positive"
            )
        if not 0 < self.discount_factor <= 1:
            raise ValueError("discount_factor must be in (0, 1]")

        self.root = _TrieNode(0)
        self._next_identifier = 1
        transition_sequences = _proxy_transition_sequences(
            net, im, fm, parameters
        )
        if not transition_sequences:
            raise ValueError("the proxy behavior contains no complete model trace")
        for sequence in transition_sequences:
            self._insert_proxy(sequence)
        self._cases: Dict[str, List[_State]] = {}
        self._completed: Dict[str, Dict[str, Any]] = {}
        self._last_event_runtime = 0.0
        self._total_runtime = 0.0
        self._processed_events = 0
        StreamingAlgorithm.__init__(self)

    def _insert_proxy(self, transitions):
        node = self.root
        invisible_prefix = []
        for transition in transitions:
            if transition.label is None:
                invisible_prefix.append(transition)
                continue
            segment = tuple(invisible_prefix + [transition])
            invisible_prefix = []
            edge_key = (transition.label, segment)
            if edge_key not in node.children:
                child = _TrieNode(
                    self._next_identifier,
                    transition.label,
                    node,
                    segment,
                )
                self._next_identifier += 1
                node.children[edge_key] = child
            node = node.children[edge_key]
        node.final = True
        trailing = tuple(invisible_prefix)
        if trailing not in node.trailing_options:
            node.trailing_options.append(trailing)

    def _process(self, event):
        start_time = time.perf_counter()
        case = event.get(self.case_id_key)
        activity = event.get(self.activity_key)
        if case is None or activity is None:
            raise ValueError("stream events require case and activity attributes")
        case = str(case)
        states = self._cases.get(
            case, [_State(self.root, tuple(), 0, float(self.decay_time))]
        )
        generated = []
        for state in states:
            remaining_decay = state.decay - 1
            # A log move always keeps at least one explanation alive.
            log_step = approx_utils.AlignmentStep(
                activity,
                None,
                None,
                align_utils.STD_MODEL_LOG_MOVE_COST,
            )
            generated.append(
                _State(
                    state.node,
                    state.steps + (log_step,),
                    state.cost + align_utils.STD_MODEL_LOG_MOVE_COST,
                    self._discounted_decay(
                        remaining_decay,
                        state.cost + align_utils.STD_MODEL_LOG_MOVE_COST,
                    ),
                )
            )
            for edge_path in _matching_paths(
                state.node, activity, self.look_ahead
            ):
                extension, extra_cost = _path_extension(edge_path, activity)
                generated.append(
                    _State(
                        edge_path[-1],
                        state.steps + extension,
                        state.cost + extra_cost,
                        float(self.decay_time)
                        if len(edge_path) == 1
                        else self._discounted_decay(
                            remaining_decay, state.cost + extra_cost
                        ),
                    )
                )

        by_node = {}
        for state in sorted(generated, key=lambda item: (item.cost, -item.decay)):
            if state.node not in by_node and state.decay > 0:
                by_node[state.node] = state
        survivors = list(by_node.values())[: self.max_states]
        if not survivors:
            survivors = [min(generated, key=lambda item: item.cost)]
            survivors[0].decay = 1.0
        self._cases[case] = survivors
        self._last_event_runtime = time.perf_counter() - start_time
        self._total_runtime += self._last_event_runtime
        self._processed_events += 1
        if event.get(self.complete_case_attribute, False):
            self._completed[case] = self._finish(case)

    def _discounted_decay(self, remaining_decay, accumulated_cost):
        deviations = accumulated_cost // align_utils.STD_MODEL_LOG_MOVE_COST
        discounted = self.decay_time * (self.discount_factor ** deviations)
        return max(0.0, min(float(remaining_decay), discounted))

    def _current_result(self):
        result = {
            case: self._prefix_result(states)
            for case, states in self._cases.items()
        }
        for case, completed in self._completed.items():
            result[case] = completed
        return result

    def _prefix_result(self, states):
        state = min(states, key=lambda item: item.cost)
        labels = [
            step.log_label for step in state.steps if step.log_label is not None
        ]
        return {
            "alignment": approx_utils.format_alignment(
                state.steps, self.ret_desc
            ),
            "cost": state.cost,
            "standard_cost": approx_utils.standard_cost(state.steps),
            "is_valid": approx_utils.validate_steps(
                labels, self.net, self.im, None, state.steps
            ),
            "is_complete": False,
            "approximation_method": "iws",
            "bound_type": "proxy_alignment_upper_bound",
            "active_states": len(states),
            "trie_node": state.node.identifier,
            "decay": state.decay,
            "upper_bound": approx_utils.standard_cost(state.steps),
            "last_event_runtime": self._last_event_runtime,
            "total_runtime": self._total_runtime,
            "processed_events": self._processed_events,
        }

    def _finish(self, case):
        start_time = time.perf_counter()
        states = self._cases.get(case)
        if not states:
            raise KeyError("unknown case: %s" % case)
        complete_states = []
        for state in states:
            suffix = _shortest_terminal_suffix(state.node)
            if suffix is None:
                continue
            transitions, suffix_cost = suffix
            steps = state.steps + tuple(
                approx_utils.AlignmentStep(
                    None,
                    transition,
                    None,
                    align_utils.STD_MODEL_LOG_MOVE_COST
                    if transition.label is not None
                    else align_utils.STD_TAU_COST,
                )
                for transition in transitions
            )
            complete_states.append(
                _State(
                    state.node,
                    steps,
                    state.cost + suffix_cost,
                    state.decay,
                )
            )
        if not complete_states:
            raise ValueError("no retained state can reach a proxy final node")
        chosen = min(complete_states, key=lambda item: item.cost)
        labels = [
            step.log_label for step in chosen.steps if step.log_label is not None
        ]
        result = {
            "alignment": approx_utils.format_alignment(
                chosen.steps, self.ret_desc
            ),
            "cost": chosen.cost,
            "standard_cost": approx_utils.standard_cost(chosen.steps),
            "is_valid": approx_utils.validate_steps(
                labels, self.net, self.im, self.fm, chosen.steps
            ),
            "is_complete": True,
            "approximation_method": "iws",
            "bound_type": "proxy_alignment_upper_bound",
            "active_states": len(states),
            "upper_bound": approx_utils.standard_cost(chosen.steps),
        }
        result["runtime"] = time.perf_counter() - start_time
        return result

    def finish(self, case_id):
        """Finish a case and return a complete proxy-trie alignment."""
        case = str(case_id)
        self._lock.acquire()
        try:
            result = self._finish(case)
            self._completed[case] = result
            return result
        finally:
            self._lock.release()


def _matching_paths(node, activity, look_ahead):
    matches = []
    stack = [(node, tuple())]
    while stack:
        current, path = stack.pop()
        if len(path) >= look_ahead:
            continue
        for child in current.children.values():
            new_path = path + (child,)
            if child.label == activity:
                matches.append(new_path)
            stack.append((child, new_path))
    return matches


def _path_extension(edge_path, activity):
    steps = []
    cost = 0
    for child in edge_path[:-1]:
        for transition in child.segment:
            move_cost = (
                align_utils.STD_MODEL_LOG_MOVE_COST
                if transition.label is not None
                else align_utils.STD_TAU_COST
            )
            steps.append(
                approx_utils.AlignmentStep(None, transition, None, move_cost)
            )
            cost += move_cost
    matched = edge_path[-1]
    for transition in matched.segment[:-1]:
        steps.append(
            approx_utils.AlignmentStep(
                None, transition, None, align_utils.STD_TAU_COST
            )
        )
        cost += align_utils.STD_TAU_COST
    steps.append(
        approx_utils.AlignmentStep(activity, matched.segment[-1], None, 0)
    )
    return tuple(steps), cost


def _shortest_terminal_suffix(node):
    memo = {}

    def visit(current):
        if current in memo:
            return memo[current]
        candidates = []
        if current.final:
            for trailing in current.trailing_options:
                trailing_cost = sum(
                    align_utils.STD_MODEL_LOG_MOVE_COST
                    if transition.label is not None
                    else align_utils.STD_TAU_COST
                    for transition in trailing
                )
                candidates.append((tuple(trailing), trailing_cost))
        for child in current.children.values():
            suffix = visit(child)
            if suffix is None:
                continue
            edge_cost = sum(
                align_utils.STD_MODEL_LOG_MOVE_COST
                if transition.label is not None
                else align_utils.STD_TAU_COST
                for transition in child.segment
            )
            candidates.append(
                (tuple(child.segment) + suffix[0], edge_cost + suffix[1])
            )
        memo[current] = min(candidates, key=lambda item: item[1]) if candidates else None
        return memo[current]

    return visit(node)


def _proxy_transition_sequences(net, im, fm, parameters):
    proxy_log = exec_utils.get_param_value(Parameters.PROXY_LOG, parameters, None)
    requested = exec_utils.get_param_value(
        Parameters.PROXY_TRACES, parameters, 100
    )
    max_expansions = exec_utils.get_param_value(
        Parameters.MAX_EXPANSIONS, parameters, 100000
    )
    if proxy_log is not None:
        event_log = log_converter.apply(
            proxy_log,
            variant=log_converter.Variants.TO_EVENT_LOG,
            parameters=parameters,
        )
        sequences = []
        seen = set()
        for trace in event_log:
            labels = approx_utils.trace_labels(trace, parameters)
            result = approx_utils.search_alignment(
                labels,
                net,
                im,
                fm,
                [align_utils.STD_MODEL_LOG_MOVE_COST] * len(labels),
                {
                    transition: (
                        align_utils.STD_MODEL_LOG_MOVE_COST
                        if transition.label is not None
                        else align_utils.STD_TAU_COST
                    )
                    for transition in net.transitions
                },
                {
                    transition: 0
                    for transition in net.transitions
                    if transition.label is not None
                },
                max_time=exec_utils.get_param_value(
                    Parameters.PARAM_MAX_ALIGN_TIME_TRACE,
                    parameters,
                    sys.maxsize,
                ),
                max_expansions=max_expansions,
            )
            if result:
                sequence = tuple(
                    step.transition
                    for step in result[0].steps
                    if step.transition is not None
                )
                visible = tuple(
                    transition.label
                    for transition in sequence
                    if transition.label is not None
                )
                if visible not in seen:
                    seen.add(visible)
                    sequences.append(sequence)
        return sequences

    rng = random.Random(
        exec_utils.get_param_value(Parameters.RANDOM_SEED, parameters, 0)
    )
    max_length = exec_utils.get_param_value(
        Parameters.MAX_TRACE_LENGTH,
        parameters,
        max(100, 4 * len(net.transitions)),
    )
    max_attempts = exec_utils.get_param_value(
        Parameters.MAX_SIMULATION_ATTEMPTS,
        parameters,
        max(1000, requested * 20),
    )
    sequences = []
    seen = set()
    for _ in range(max_attempts):
        marking = Marking(im)
        sequence = []
        for _step in range(max_length):
            if marking == fm:
                break
            enabled = list(semantics.enabled_transitions(net, marking))
            if not enabled:
                break
            transition = rng.choice(enabled)
            sequence.append(transition)
            marking = semantics.execute(transition, net, marking)
        if marking != fm:
            continue
        visible = tuple(
            transition.label
            for transition in sequence
            if transition.label is not None
        )
        if visible in seen:
            continue
        seen.add(visible)
        sequences.append(tuple(sequence))
        if len(sequences) >= requested:
            break
    return sequences


def apply(
    net: PetriNet,
    im: Marking,
    fm: Marking,
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> IWSStreamingAlignments:
    return IWSStreamingAlignments(net, im, fm, parameters=parameters)
