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

from collections import Counter, namedtuple
import random
from typing import Any, Dict, Optional

import pandas as pd
from pm4py.objects.oc_causal_net.obj import OCCausalNet
from pm4py.objects.oc_causal_net.semantics import OCCausalNetState, OCCausalNetSemantics
from pm4py.objects.ocel import constants
from pm4py.objects.ocel.obj import OCEL
from pm4py.util import exec_utils
from enum import Enum


class Parameters(Enum):
    EVENT_ID = constants.PARAM_EVENT_ID
    EVENT_ACTIVITY = constants.PARAM_EVENT_ACTIVITY
    EVENT_TIMESTAMP = constants.PARAM_EVENT_TIMESTAMP
    OBJECT_ID = constants.PARAM_OBJECT_ID
    OBJECT_TYPE = constants.PARAM_OBJECT_TYPE
    OBJECTS_UNIQUE_PER_SEQUENCE = "objects_unique_per_sequence"
    RETURN_SEQUENCES = "return_sequences"
    MAX_BINDINGS_PER_ACTIVITY = "maxBindingsPerActivity"
    OCCN_SEMANTICS = "occn_semantics"
    BRANCHING_FACTOR_ACTIVITIES = "branching_factor_activities"
    BRANCHING_FACTOR_BINDINGS = "branching_factor_bindings"


FINAL_MARKER = "FINAL"


# Define memory-efficient data type for binding
# a binding is a tuple of activity id, consumed objects, and produced objects
#    consumed / produces are tuples of (predecessor/successor activity id, objects_per_ot)
#      where objects_per_ot is a tuples of entries (object_type, objects)
#         where objects is a tuple (obj_id_1, obj_id_2, ...)
Binding = namedtuple("Binding", ["activity_id", "consumed", "produced"])


def apply(
    occn: OCCausalNet, objects: dict, parameters: Optional[Dict[Any, Any]] = None
) -> OCEL:
    """
    Compute playout of an object-centric causal net generating an OCEL.
    Extensive search, retrieves all valid binding sequences.
    Starts by binding start activities with the objects specified and ends in the empty state.
    The empty sequence is considered a valid sequence no other sequences are found.

    Parameters
    -----------
    occn
        Object-centric causal net to play-out
    objects
        Dictionary mapping object types to sets of object ids. These objects will be introduced by the start activities of the occn at the beginning of every binding sequence.
    parameters
        Parameters of the algorithm, including:
            Parameters.MAX_BINDINGS_PER_ACTIVITY: Maximum number of bindings per activity (mandatory)
            Parameters.RETURN_SEQUENCES: If True, return an iterator to all possible sequences of bindings instead of an OCEL
            Parameters.OBJECTS_UNIQUE_PER_SEQUENCE: If True, objects in the resulting OCEL are make unique per sequence (default: False)
            Parameters.OCCN_SEMANTICS: The semantics to be used for the causal net (default: OCCausalNetSemantics())
            Parameters.BRANCHING_FACTOR_ACTIVITIES: Maximum branching factor for exploring enabled activities (default: inf). Note that the play-out will generate a subset of all sequences if this is set.
            Parameters.BRANCHING_FACTOR_BINDINGS: Maximum branching factor for exploring enabled bindings (default: inf). Note that the play-out will generate a subset of all sequences if this is set.
    """
    if parameters is None:
        parameters = {}

    return_sequences = exec_utils.get_param_value(
        Parameters.RETURN_SEQUENCES, parameters, False
    )
    if Parameters.MAX_BINDINGS_PER_ACTIVITY not in parameters:
        raise ValueError(
            "Parameter MAX_BINDINGS_PER_ACTIVITY must be specified for the extensive playout. This parameter limits the maximum number of times an activity may be executed."
        )
    max_bindings_per_activity = exec_utils.get_param_value(
        Parameters.MAX_BINDINGS_PER_ACTIVITY, parameters, None
    )
    semantics = exec_utils.get_param_value(
        Parameters.OCCN_SEMANTICS,
        parameters,
        OCCausalNetSemantics(),
    )
    bf_act = exec_utils.get_param_value(
        Parameters.BRANCHING_FACTOR_ACTIVITIES, parameters, float("inf")
    )
    bf_bind = exec_utils.get_param_value(
        Parameters.BRANCHING_FACTOR_BINDINGS, parameters, float("inf")
    )

    # create int id for every activity for memory efficiency
    activity_to_id = {activity: i for i, activity in enumerate(occn.activities)}
    id_to_activity = {i: activity for activity, i in activity_to_id.items()}
    start_activities = set(
        i for activity, i in activity_to_id.items() if activity.startswith("START_")
    )
    # same for object types
    object_type_to_id = {
        object_type: i for i, object_type in enumerate(occn.object_types)
    }
    id_to_object_type = {i: object_type for object_type, i in object_type_to_id.items()}

    # Set up initial state with starting objects
    # In the state, we denote activities by their id, not by their name
    initial_state = OCCausalNetState()

    # Create fake obligations to start activities for all starting objects
    for object_type, object_ids in objects.items():
        ot_id = object_type_to_id[object_type]
        start_activity_id = activity_to_id[f"START_{object_type}"]
        initial_state += OCCausalNetState(
            {start_activity_id: Counter([(-1, obj_id, ot_id) for obj_id in object_ids])}
        )

    # Activity counts
    # index is from `activity_to_id`
    initial_activity_counts = (0,) * len(occn.activities)

    # State key used for memoization, see below
    initial_state_key = (initial_state, initial_activity_counts)

    # Memoization cache: Dict[state_key, Union[Set[Tuple[Binding, next_key]], str]]
    # where state_key is a tuple of (state, activity_counts) and the value is either
    # FINAL_MARKER if the state is the empty state,
    # or a set of tuples of bindings and next state keys that correspond to all successor
    # states that can be reached from the current state using the respective bindings.
    memo = {}

    # == Phase 1: Memoization DFS Graph Population ==
    _populate_memo_graph(
        initial_state_key,
        occn,
        semantics,
        max_bindings_per_activity,
        start_activities,
        activity_to_id,
        id_to_activity,
        object_type_to_id,
        bf_act,
        bf_bind,
        memo,
    )

    # == Phase 2: Reconstruct traces from memo ==
    valid_sequences_iter = _reconstruct_sequences(initial_state_key, memo)

    # == Phase 3: Return data in the desired format ==
    if return_sequences:
        # return valid_sequences along with a mapping from indices to activities and object types
        return (
            valid_sequences_iter,
            id_to_activity,
            id_to_object_type,
        )
    else:
        return _valid_sequences_to_ocel(valid_sequences_iter, id_to_activity, id_to_object_type, parameters)


def _populate_memo_graph(
    state_key: tuple,
    occn: OCCausalNet,
    semantics,
    max_bindings: int,
    start_activities,
    act_to_idx: dict,
    idx_to_act: dict,
    ot_to_idx: dict,
    bf_act: float,
    bf_bind: float,
    memo: dict,
) -> bool:
    """
    Recursively explores the state space to build a compact, memoized graph of all valid binding sequences.

    This function performs a depth-first search from a given state_key. It populates a memoization
    cache (`memo`). For each state (defined by the state_key), it stores the set of "next steps" (as tuples of
    (binding, next_state_key)) that lie on a path to the empty state,
    where binding is of type Binding.

    This approach avoids duplicate computation of two different sequences leading to the same state key.

    Parameters
    -----------
    state_key : tuple
        A tuple representing the current state in the form (state, activity_counts).
    occn : OCCausalNet
        The object-centric causal net being used.
    semantics
        The semantics to be used for the causal net.
    max_bindings : int
        Maximum number of bindings per activity.
    start_activities
        Collection of indices for start activities.
    act_to_idx : dict
        Dictionary mapping activities to their id.
    idx_to_act : dict
        Dictionary mapping activity ids to their names.
    ot_to_idx : dict
        Dictionary mapping object types to their id.
    bf_act : float
        Traversal will only explore this many enabled activities per step. If set, the play-out will generate a subset
        of all sequences. Will be stochastically rounded if not an integer.
    bf_bind : float
        Traversal will only explore this many enabled bindings per activity. If set, the play-out will generate a subset
        of all sequences. Will be stochastically rounded if not an integer.
    memo : dict
        The memoization cache where the state_key is mapped to a set of next steps or FINAL_MARKER if the state is the empty state.

    Returns
    -------
    bool
        Returns True if the state_key is reachable (i.e., not a deadlock), False otherwise.
        If the state_key is a deadlock, it will be represented by an empty set in the memo.
    """
    if state_key in memo:
        # a deadlock is indicated by an empty set in the memo.
        # an entry that is not empty indicates that the empty state is reachable
        return bool(memo[state_key])

    # state_key has not been explored yet, so we explore it
    state, activity_counts = state_key
    if not state.activities:
        # empty state
        memo[state_key] = FINAL_MARKER
        return True

    next_steps = set()
    enabled_activities = _get_enabled_activities(
        occn, semantics, state, start_activities, act_to_idx, idx_to_act, ot_to_idx
    )

    # Limit the number of enabled activities to bf_act
    if bf_act < float("inf"):
        # Stochastically round bf_act to an integer
        bf_act_rounded = int(bf_act) + (1 if random.random() < (bf_act % 1) else 0)
        # Select random subset of enabled activities
        enabled_activities = set(random.sample(list(enabled_activities), min(bf_act_rounded, len(enabled_activities))))

    # explore all sucessor states by binding all enabled activities
    for act in enabled_activities:
        act_id = act_to_idx[act]

        if activity_counts[act_id] >= max_bindings:
            continue

        new_activiy_counts = list(activity_counts)
        new_activiy_counts[act_id] += 1
        new_activity_counts_tuple = tuple(new_activiy_counts)

        # Get all enabled bindings for this activity
        if act_id in start_activities:
            enabled_bindings = _get_bindings_start_activity(
                occn, act, state, act_to_idx, ot_to_idx
            )
        else:
            enabled_bindings = semantics.enabled_bindings(occn, act, state, act_to_idx, ot_to_idx)

        # Limit the number of enabled bindings to bf_bind
        if bf_bind < float("inf"):
            # Stochastically round bf_bind to an integer
            bf_bind_rounded = int(bf_bind) + (1 if random.random() < (bf_bind % 1) else 0)
            # Select random subset of enabled bindings
            enabled_bindings = set(random.sample(list(enabled_bindings), min(bf_bind_rounded, len(enabled_bindings))))

        # explore all bindings
        for binding in enabled_bindings:
            new_state = semantics.bind_activity(
                occn,
                act=binding[0],
                cons=_convert_binding_tuple_to_dict(binding[1]),
                prod=_convert_binding_tuple_to_dict(binding[2]),
                state=state,
            )
            # clean up fake obligations for start activities
            if act_id in start_activities:
                new_state = _clean_fake_obligations(
                    occn, new_state, act, binding[2], act_to_idx, ot_to_idx
                )
            new_state_key = (new_state, new_activity_counts_tuple)

            if _populate_memo_graph(
                new_state_key,
                occn,
                semantics,
                max_bindings,
                start_activities,
                act_to_idx,
                idx_to_act,
                ot_to_idx,
                bf_act,
                bf_bind,
                memo
            ):
                next_steps.add((binding, new_state_key))

    # Add all next steps to memo
    # If state_key is a deadlock, this will be an empty set
    memo[state_key] = next_steps
    return bool(next_steps)


def _convert_binding_tuple_to_dict(binding_tuple):
    """
    Converts a tuple from a binding (conumed or produced) into a nested dictionary.
    None is converted to None.

    The inner values (object lists) are converted to sets.
    """
    if not binding_tuple:
        return None
    return {
        related_act: {
            object_type: set(objects) for object_type, objects in objects_per_type
        }
        for related_act, objects_per_type in binding_tuple
    }


def _get_enabled_activities(
    occn: OCCausalNet,
    semantics,
    state: OCCausalNetState,
    start_activities,
    act_to_idx: dict,
    idx_to_act: dict,
    ot_to_idx: dict,
) -> set:
    """
    Returns the enabled activities in the given state, including start activities
    if they have "fake obligations".

    Parameters
    -----------
    occn : OCCausalNet
        The causal net being used.
    semantics
        The semantics to be used for the causal net.
    state : OCCausalNetState
        The current state of the causal net.
    start_activities
        Collection of indices for start activities
    act_to_idx
        Dictionary mapping activities to their id.
    idx_to_act
        Dictionary mapping activity ids to their names.
    ot_to_idx
        Dictionary mapping object types to their id.

    Returns
    --------
    set
        A set of ids for enabled activities in the given state.
    """
    enabled_activities = set()

    # get start activities with outstanding fake obligations
    start_activities_with_obligations = state.activities.intersection(start_activities)
    # add names, not ids
    enabled_activities.update(idx_to_act[act_id] for act_id in start_activities_with_obligations)

    # get all other enabled activities
    enabled_activities.update(
        semantics.enabled_activities(
            occn,
            state,
            include_start_activities=False,
            act_to_idx=act_to_idx,
            ot_to_idx=ot_to_idx,
        )
    )

    return enabled_activities


def _get_bindings_start_activity(
    occn: OCCausalNet,
    act: str,
    state: OCCausalNetState,
    act_to_idx: dict,
    ot_to_idx: dict,
):
    """
    Computes all enabled bindings for a start activity with the given fake obligations
    in the state.

    Parameters
    -----------
    occn : OCCausalNet
        The object-centric causal net
    act : str
        The start activity to bind
    state : OCCausalNetState
        The current state of the causal net, which contains the fake obligations for the start activity.
    act_to_idx : dict
        Dictionary mapping activities to their id.
    ot_to_idx : dict
        Dictionary mapping object types to their id.

    Returns
    -----------
    tuple
        A tuple of enabled bindings for the start activity.
        Each binding is a tuple of (activity_id, consumed, produced).
        The consumed and produced are tuples of (predecessor/successor activity id, objects_per_ot),
        where objects_per_ot is a tuple of entries (object_type_id, objects).
    """
    # get the outstanding fake obligations for the start activity
    act_id = act_to_idx[act]
    obligations = state[act_id]
    if not obligations:
        return ()
    outstanding_objects = set()
    for (_, obj_id, _), _ in obligations.items():
        outstanding_objects.add(obj_id)

    # Extract object type
    object_type = act.split("_", 1)[1]

    # Compute enabled bindings
    bindings = OCCausalNetSemantics.enabled_bindings_start_activity(
        occn, act, object_type, outstanding_objects, act_to_idx, ot_to_idx
    )

    return bindings

def _clean_fake_obligations(
    occn: OCCausalNet,
    state: OCCausalNetState,
    act: str,
    produced: tuple,
    act_to_idx: dict,
    ot_to_idx: dict,
) -> OCCausalNetState:
    """
    Cleans up fake obligations for start activities in the state after binding the start activity.
    Since a firing of a start activity consumes no obligations,
    we need to manually remove the fake obligations that were created for the start activity
    for all objects that were bound to it.

    Parameters
    -----------
    occn : OCCausalNet
        The object-centric causal net.
    state : OCCausalNetState
        The current state of the causal net.
    act : str
        The activity that was bound.
    produced : tuple
        The produced tuple from the binding.
    act_to_idx : dict
        Dictionary mapping activities to their id.
    ot_to_idx : dict
        Dictionary mapping object types to their id.

    Returns
    -----------
    OCCausalNetState
        The updated state with cleaned fake obligations.
    """
    # get the set of all objects involved
    objects = set()
    object_types = set()
    for _, ot_to_obj in produced:
        for ot, obj_ids in ot_to_obj:
            objects.update(obj_ids)
            object_types.add(ot)

    assert len(object_types) == 1, "Only one object type should be involved in a start activity binding"
    ot_id = next(iter(object_types))

    act_id = act_to_idx[act]
    # remove all obligations for the start activity that are related to the objects
    state -= OCCausalNetState(
        {act_id: Counter([(-1, obj_id, ot_id) for obj_id in objects])}
    )

    return state


def _reconstruct_sequences(state_key: tuple, memo: dict):
    """
    Reconstructs valid binding sequences from the memoization cache.

    This function iterates over the memoization cache and reconstructs all valid binding sequences
    that lead to the empty state. It yields each sequence tuple of Binding objects.

    Parameters
    ----------
    state_key : tuple
        The key representing the current state in the memoization cache.
    memo : dict
        The memoization cache containing state keys and their corresponding next steps.

    Returns
    -------
    Iterator[tuple[Binding]]
        An iterator yielding tuples of bindings representing valid sequences.
    """
    next_steps = memo.get(state_key)

    if next_steps == FINAL_MARKER:
        # If we reached the empty state, yield an empty sequence
        yield ()
        return

    if not next_steps:
        # Deadlock state; this should only happen when there are 0 valid sequences
        # Do not yield anything
        return

    for binding, next_state_key in next_steps:
        # Recursively reconstruct sequences from the next state
        for sub_sequence in _reconstruct_sequences(next_state_key, memo):
            # Yield the current binding followed by the sub-sequence
            yield (binding,) + sub_sequence


def _valid_sequences_to_ocel(valid_sequences_iter, idx_to_act, idx_to_ot, parameters):
    """
    Converts the valid sequences of bindings into an OCEL object.

    Parameters
    ----------
    valid_sequences_iter : iter
        An iterator over valid sequences of bindings, where each sequence is a tuple of Binding objects
    idx_to_act : dict
        Mapping from indices to activity names
    idx_to_ot : dict
        Mapping from indices to object types
    parameters : dict
        Additional parameters for the conversion, including:
            Parameters.EVENT_ID: The column name for event IDs
            Parameters.OBJECT_ID: The column name for object IDs
            Parameters.OBJECT_TYPE: The column name for object types
            Parameters.EVENT_TIMESTAMP: The column name for event timestamps
            Parameters.EVENT_ACTIVITY: The column name for event activities

    Returns
    -------
    OCEL
        The resulting OCEL object.
    """
    event_id_column = exec_utils.get_param_value(
        Parameters.EVENT_ID, parameters, constants.DEFAULT_EVENT_ID
    )
    object_id_column = exec_utils.get_param_value(
        Parameters.OBJECT_ID, parameters, constants.DEFAULT_OBJECT_ID
    )
    object_type_column = exec_utils.get_param_value(
        Parameters.OBJECT_TYPE, parameters, constants.DEFAULT_OBJECT_TYPE
    )

    event_activity = exec_utils.get_param_value(
        Parameters.EVENT_ACTIVITY, parameters, constants.DEFAULT_EVENT_ACTIVITY
    )
    event_timestamp = exec_utils.get_param_value(
        Parameters.EVENT_TIMESTAMP, parameters, constants.DEFAULT_EVENT_TIMESTAMP
    )
    objects_unique_per_sequence = exec_utils.get_param_value(
        Parameters.OBJECTS_UNIQUE_PER_SEQUENCE, parameters, False
    )
    # Convert all found traces to OCEL format

    # Create the OCEL object
    events_list = []
    objects_list = []
    relations_list = []

    all_objects_seen = set()
    event_id_counter = 0
    # assigns to each event an increased timestamp from 1970
    curr_timestamp = 10000000

    if objects_unique_per_sequence:
        object_id_counter = 0

    for sequence in valid_sequences_iter:
        # For each sequence, create events and objects
        for binding in sequence:
            activity_id = binding[0]
            consumed = binding[1]
            produced = binding[2]

            act = idx_to_act[activity_id]

            # do not add START / END activities
            if act.startswith("START_") or act.startswith("END_"):
                continue

            # Create event
            event_id = f"event_{event_id_counter}"
            event_id_counter += 1
            curr_timestamp += 1

            events_list.append(
                {
                    event_id_column: event_id,
                    event_activity: act,
                    event_timestamp: pd.to_datetime(curr_timestamp, unit="s"),
                }
            )

            # Create objects and relations
            # consumed and produced contain the same objects; we only need to create them once
            for _, ot_to_obj in consumed:
                for ot_id, objects in ot_to_obj:
                    obj_type = idx_to_ot[ot_id]
                    for obj_id in objects:
                        if objects_unique_per_sequence:
                            obj_id = f"{obj_id}_{object_id_counter}"

                        # Add object
                        if obj_id not in all_objects_seen:
                            all_objects_seen.add(obj_id)
                            objects_list.append(
                                {object_id_column: obj_id, object_type_column: obj_type}
                            )

                        # Add relation
                        relations_list.append(
                            {
                                event_id_column: event_id,
                                event_activity: act,
                                event_timestamp: pd.to_datetime(
                                    curr_timestamp, unit="s"
                                ),
                                object_id_column: obj_id,
                                object_type_column: obj_type,
                            }
                        )
        if objects_unique_per_sequence:
            object_id_counter += 1

    # Convert to dataframes
    events_df = pd.DataFrame(events_list)
    objects_df = pd.DataFrame(objects_list)
    relations_df = pd.DataFrame(relations_list)

    # Create the OCEL object
    ocel = OCEL(
        events=events_df,
        objects=objects_df,
        relations=relations_df,
        parameters=parameters,
    )

    return ocel
