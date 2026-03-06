"""
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
"""

import random
import sys
from pm4py.algo.simulation.playout.ocpn.variants.utils import feasible_traces_to_ocel
from pm4py.objects.ocpn.semantics import OCPetriNetSemantics
from pm4py.objects.ocel.obj import OCEL
from pm4py.objects.ocpn.obj import OCPetriNet, OCMarking
from pm4py.objects.ocel import constants
from pm4py.util import exec_utils
from typing import Optional, Dict, Any, Union, List
from enum import Enum


class Parameters(Enum):
    EVENT_ID = constants.PARAM_EVENT_ID
    EVENT_ACTIVITY = constants.PARAM_EVENT_ACTIVITY
    EVENT_TIMESTAMP = constants.PARAM_EVENT_TIMESTAMP
    OBJECT_ID = constants.PARAM_OBJECT_ID
    OBJECT_TYPE = constants.PARAM_OBJECT_TYPE
    MAX_BINDINGS_PER_ACTIVITY = "maxBindingsPerActivity"
    BRANCHING_FACTOR_TRANSITIONS = "branchingFactorTransitions"
    BRANCHING_FACTOR_BINDINGS = "branchingFactorBindings"
    OBJECTS_UNIQUE_PER_TRACE = "objects_unique_per_trace"
    RETURN_TRACES = "return_traces"
    EXISTS_TRACE = "exists_trace"
    OCPETRINET_SEMANTICS = "ocpetrinet_semantics"
    IS_FINAL_FUNC = "is_final_func"


FINAL_MARKER = "FINAL"


def apply(
    net: OCPetriNet,
    initial_marking: OCMarking,
    final_marking: OCMarking,
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> OCEL:
    """
    Compute playout of an object-centric Petri net generating an OCEL (extensive search;
    any activity may only be executed a limited number of times as specified).
    Uses an optimized Memoized DFS Graph Population algorithm.

    Parameters
    -----------
    net
        Object-centric Petri net to play-out
    initial_marking
        Initial marking of the object-centric Petri net
    final_marking
        Final marking of the object-centric Petri net
    parameters
        Parameters of the algorithm:
            Parameters.MAX_BINDINGS_PER_ACTIVITY -> Maximum bindings per activity (mandatory)
            Parameters.EXISTS_TRACE -> If True, return a boolean indicating if at least one trace exists instead of an OCEL
            Parameters.OBJECTS_UNIQUE_PER_TRACE: If True, objects in the resulting OCEL are make unique per trace (default: False)
            Parameters.RETURN_TRACES -> If True, return traces instead of OCEL
            Parameters.BRANCHING_FACTOR_TRANSITIONS -> Maximum number of transitions to explore from a single
                state (default: sys.maxsize, i.e., no limit). If set to a float, it will be stochastically rounded to an integer for every state.
            Parameters.BRANCHING_FACTOR_BINDINGS -> Maximum number of bindings to explore for a single transition
                (default: sys.maxsize, i.e., no limit). If set to a float, it will be stochastically rounded to an integer for every state.
            Parameters.OCPETRINET_SEMANTICS -> Object-centric Petri net semantics
            Parameters.IS_FINAL_FUNC -> Function that given a marking and the final marking returns whether the final marking is reached.
                (default: marking == final_marking)
    """
    if parameters is None:
        parameters = {}

    return_traces = exec_utils.get_param_value(
        Parameters.RETURN_TRACES, parameters, False
    )
    exists_trace = exec_utils.get_param_value(
        Parameters.EXISTS_TRACE, parameters, False
    )
    if Parameters.MAX_BINDINGS_PER_ACTIVITY not in parameters:
        raise ValueError(
            "Parameter MAX_BINDINGS_PER_ACTIVITY must be specified for the extensive playout. This parameter limits the maximum number of times an activity may be executed."
        )
    max_bindings_per_activity = exec_utils.get_param_value(
        Parameters.MAX_BINDINGS_PER_ACTIVITY, parameters, None
    )
    # How many enabled transitions to explore from a single state
    # deactivated by default
    bf_trans = exec_utils.get_param_value(
        Parameters.BRANCHING_FACTOR_TRANSITIONS, parameters, sys.maxsize
    )
    # How many bindings to explore for a single transition
    # deactivated by default
    bf_binds = exec_utils.get_param_value(
        Parameters.BRANCHING_FACTOR_BINDINGS, parameters, sys.maxsize
    )
    semantics = exec_utils.get_param_value(
        Parameters.OCPETRINET_SEMANTICS,
        parameters,
        OCPetriNetSemantics(),
    )
    is_final = exec_utils.get_param_value(
        Parameters.IS_FINAL_FUNC,
        parameters,
        _is_final
    )

    # Save transitions as ids for memory efficiency; create lookup table for conversion
    all_transitions = sorted(list(net.transitions), key=lambda t: t.name)
    transition_to_idx = {t: i for i, t in enumerate(all_transitions)}

    # State key: (marking, number of firings per transition)
    # Transition firing counts; Position corresponds to transitions_to_idx table
    initial_transition_counts = (0,) * len(all_transitions)

    initial_state_key = (initial_marking, initial_transition_counts)

    # Memoization cache: Dict[state_key, Union[Set[Tuple[binding, next_key]], str]]
    # where the state_key is a tuple of (marking, transition_counts) and the
    # value is either FINAL_MARKER if the state is final,
    # or a set of tuples (binding, next_state_key) with all possible bindings
    # in the given state key and the state key they lead to
    memo = {}

    # == Phase 1: Memoization DFS Graph Population ==
    trace_exists = _populate_memo_graph(
        initial_state_key,
        net,
        final_marking,
        semantics,
        transition_to_idx,
        max_bindings_per_activity,
        bf_trans,
        bf_binds,
        exists_trace,
        is_final,
        memo,
    )
    
    # If we are only interested in whether a trace exists, return immediately
    if exists_trace:
        return trace_exists
    

    # == Phase 2: Reconstruct traces from memo ==
    feasible_traces_iter = _reconstruct_traces(
        initial_state_key, memo, transition_to_idx, all_transitions
    )

    # == Phase 3: Return data in desired format ==
    # We did not save the object types of objects in the events, so we need to reconstruct them from the initial marking
    # Maps object ids to their types
    id_to_obj_type = dict()
    # Every object can be found in the initial marking
    for p, obj_ids in initial_marking.items():
        ot = p.object_type
        for obj_id in obj_ids:
            id_to_obj_type[obj_id] = ot
    
    if return_traces:
        # Inverse the transition_to_idx mapping to get transition labels
        idx_to_transition = {v: k for k, v in transition_to_idx.items()}
        return (list(feasible_traces_iter), idx_to_transition, id_to_obj_type)
    else:
        return feasible_traces_to_ocel(
            feasible_traces_iter, all_transitions, id_to_obj_type, parameters
        )


def _populate_memo_graph(
    state_key: tuple,
    net: OCPetriNet,
    final_marking: OCMarking,
    semantics,
    t_to_idx: dict,
    max_bindings: int,
    bf_trans: float,
    bf_binds: float,
    exists_trace: bool,
    is_final,
    memo: dict,
) -> bool:
    """
    Recursively explores the state space to build a compact, memoized graph of all valid traces.

    This function performs a depth-first search from a given state_key. It populates a memoization
    cache (`memo`). For each state (defined by the state_key), it stores the set of "next steps" (as tuples of
    (transition_index, binding, next_state_key)) that lie on a path to the final marking,
    where binding is a set of object IDs that were bound to the transition.

    This approach avoids duplicate computation of two different traces leading to the same state key.

    Parameters
    -----------
    state_key
        A tuple `(OCMarking, tuple)` representing the current state of the search.
    net
        The object-centric Petri net being explored.
    final_marking
        The target OCMarking that signifies the end of a successful trace.
    semantics
        The OCPN semantics object used for enabling and firing transitions.
    t_to_idx
        A lookup dictionary mapping transition objects to their integer indices.
    max_bindings
        The maximum number of times any single transition is allowed to fire.
    bf_trans
        The max branching factor for transitions, limiting how many enabled transitions to explore.
        If set to a float, it will be stochastically rounded to an integer.
    bf_binds
        The max branching factor for bindings, limiting how many bindings to explore for each transition.
        If set to a float, it will be stochastically rounded to an integer.
    exists_trace
        If `True`, the function will return a boolean indicating if at least one trace exists that
        leads to the final marking, rather than populating the memo with all valid traces.
    is_final
        A function to determine if a marking is the final marking.
    memo
        The memoization cache, a dictionary that is modified in place by the function.
        It maps state_keys to the set of valid next steps or a special marker.

    Returns
    -----------
    bool
        Returns `True` if the final_marking is reachable from the given state_key,
        otherwise returns `False`.
    """
    if state_key in memo:
        # a deadlock is indicated by an empty set in the memo.
        # an entry that is not empty indicates that the final marking is reachable
        return bool(memo[state_key])

    # state_key has not been explored yet, so we explore it
    marking, transition_counts = state_key
    if is_final(marking, final_marking):
        # signal that the final marking is reached
        memo[state_key] = FINAL_MARKER
        return True

    next_steps = set()
    enabled_transitions = semantics.enabled_transitions(net, marking)
    # Stochastically round bf_trans to an integer
    rounded_bf_trans = int(bf_trans) + (1 if random.random() < (bf_trans % 1) else 0)
    # select a random subset if branching factor is limited
    transitions_to_explore = random.sample(
        list(enabled_transitions), k=min(rounded_bf_trans, len(enabled_transitions))
    )

    # explore all successor states by firing enabled transitions
    for t in transitions_to_explore:
        transition_idx = t_to_idx[t]
        if transition_counts[transition_idx] >= max_bindings:
            continue

        # Create new transition counts
        new_transition_counts = list(transition_counts)
        new_transition_counts[transition_idx] += 1
        new_counts_tuple = tuple(new_transition_counts)

        # Get all possible bindings for the transition
        bindings = list(semantics.get_possible_bindings(net, t, marking))

        # Stochastically round bf_binds to an integer
        rounded_bf_binds = int(bf_binds) + (
            1 if random.random() < (bf_binds % 1) else 0
        )
        # select a random subset of bindings if branching factor is limited
        bindings_to_explore = random.sample(
            bindings, k=min(rounded_bf_binds, len(bindings))
        )

        for binding in bindings_to_explore:
            new_marking = semantics.fire(net, t, marking, binding)
            new_state_key = (new_marking, new_counts_tuple)
            object_ids = [oi for objs in binding.values() for oi in objs]

            # Recursively explore the next state. Only add to memo it if it leads to the final state
            if _populate_memo_graph(
                new_state_key,
                net,
                final_marking,
                semantics,
                t_to_idx,
                max_bindings,
                bf_trans,
                bf_binds,
                exists_trace,
                is_final,
                memo,
            ):
                next_steps.add((transition_idx, frozenset(object_ids), new_state_key))
                if exists_trace:
                    # If we are only interested in whether a trace exists, we can return early
                    return True

    # Add all next steps to the memoization cache
    # If state_key is a deadlock, it will be an empty set
    memo[state_key] = next_steps
    return bool(next_steps)


def _reconstruct_traces(
    state_key: tuple, memo: dict, t_to_idx: dict, all_transitions: List
) -> iter:
    """
    Recursively reconstructs all valid traces by traversing the pre-computed graph in the memo cache.

    This function is a generator that operates on the populated `memo` dictionary created by
    `_populate_memo_graph`. It starts from a given state_key and recursively follows all valid
    "next steps" stored in the cache. When it reaches a path's end (marked by the FINAL_MARKER),
    it yields a complete trace.

    Parameters
    -----------
    state_key
        The tuple `(OCMarking, tuple)` representing the current state from which to reconstruct paths.
    memo
        The pre-populated memoization cache containing the valid path graph from the
        `_populate_memo_graph` function.
    t_to_idx
        A lookup dictionary mapping transition objects to their integer indices.
    all_transitions
        A ordered list of all transition objects in the Petri net.

    Yields
    -----------
    tuple
        A single, complete trace. Each yielded trace is a tuple of event tuples, where each
        event is `(transition_idx, frozenset(object_ids))`.
    """
    next_steps = memo.get(state_key)

    if next_steps == FINAL_MARKER:
        # If we reached the final marking, yield an empty trace
        yield ()
        return

    if not next_steps:
        # This should not happen unless the initial marking is a deadlock
        return

    for t_idx, object_ids, next_state_key in next_steps:
        current_event = (t_idx, object_ids)

        # Recursively yield all traces from the next state
        for tail in _reconstruct_traces(
            next_state_key, memo, t_to_idx, all_transitions
        ):
            # Prepend the current event
            yield (current_event,) + tail


def _is_final(marking, final_marking):
    return marking == final_marking