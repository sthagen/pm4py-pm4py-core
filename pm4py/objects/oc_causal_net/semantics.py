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

from collections import Counter, defaultdict
import itertools
from typing import Any, Generic, Set, TypeVar, Union
from copy import deepcopy
from pm4py.objects.oc_causal_net.obj import OCCausalNet


N = TypeVar("N", bound=OCCausalNet)
M = TypeVar("M", bound=OCCausalNet.Marker)
MG = TypeVar("MG", bound=OCCausalNet.MarkerGroup)


class OCCausalNetState(Generic[N], defaultdict):
    """
    The state of an object-centric causal net is a mapping from activities act to
    multisets of outstanding obligations (act2, object_id, object_type) from act2 to act.

    ```
    state = OCCausalNetState({act: Counter([(act2, object_id, object_type)])})
    ```
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the OCCausalNetState, querying unspecified activities defaults to an empty multiset."""
        super().__init__(Counter)
        data_args = args
        if args and args[0] is Counter:
            data_args = args[1:]
        initial_data = dict(*data_args, **kwargs)
        for act, obligations in initial_data.items():
            self[act] = Counter(obligations)

    def __hash__(self):
        return frozenset(
            (act, frozenset(counter.items()))
            for act, counter in self.items()
            if counter
        ).__hash__()

    def __eq__(self, other):
        if not isinstance(other, OCCausalNetState):
            return False
        return all(
            self.get(a, Counter()) == other.get(a, Counter())
            for a in set(self.keys()) | set(other.keys())
        )

    def __le__(self, other):
        for a, self_counter in self.items():
            other_counter = other.get(a, Counter())
            # Every obligation count in self must be less than or equal to the count in other.
            if not all(
                other_counter.get(pred, 0) >= count
                for pred, count in self_counter.items()
            ):
                return False
        return True

    def __add__(self, other):
        result = OCCausalNetState()
        for a, self_counter in self.items():
            result[a] += self_counter
        for a, other_counter in other.items():
            result[a] += other_counter
        return result

    def __sub__(self, other):
        result = OCCausalNetState()
        for a, self_counter in self.items():
            diff = self_counter - other.get(a, Counter())
            if diff != Counter():
                result[a] = diff
        return result

    def __repr__(self):
        # e.g.  [(a, o1[order], a'), ...]
        sorted_entries = sorted(self.items(), key=lambda item: item[0])
        obligations = [
            f"({pred}, {obj_id}[{ot}], {act}):{count}"
            for (act, obl) in sorted_entries
            for ((pred, obj_id, ot), count) in obl.items()
        ]
        return f'[{", ".join(obligations) if obligations else ""}]'

    def __str__(self):
        return self.__repr__()

    def __deepcopy__(self, memodict={}):
        new_state = OCCausalNetState()
        memodict[id(self)] = new_state
        for act, obligations in self.items():
            act_copy = (
                memodict[id(act)] if id(act) in memodict else deepcopy(act, memodict)
            )
            counter_copy = (
                memodict[id(obligations)]
                if id(obligations) in memodict
                else deepcopy(obligations, memodict)
            )
            new_state[act_copy] = counter_copy
        return new_state

    @property
    def activities(self) -> Set:
        """
        Set of activities with outstanding obligations.
        """
        return set(act for act in self.keys() if self[act])


class OCCausalNetSemantics(Generic[N]):
    """
    Class for the semantics of object-centric causal nets
    """

    @classmethod
    def enabled_activities(
        cls,
        occn: N,
        state: OCCausalNetState,
        include_start_activities=False,
        act_to_idx: dict = None,
        ot_to_idx: dict = None,
    ) -> Set:
        """
        Returns the enabled activities in the given state.

        Parameters
        ----------
        occn
            Object-centric causal net
        state
            State of the OCCN
        include_start_activities
            True if start activities should be included in the set.
            Start activities are always enabled.
        act_to_idx
            If activities are denoted in the state by an id instead of their name,
            a dictionary mapping activities to their index has to be provided here.
        ot_to_idx
            If object types are denoted in the state by an id instead of their name,
            a dictionary mapping object types to their index has to be provided here.

        Returns
        -------
        set
            Set of all activities enabled.
        """
        return set(
            act
            for act in occn.activities
            if (include_start_activities or not act.startswith("START_"))
            and cls.is_enabled(occn, act, state, act_to_idx, ot_to_idx)
        )

    @classmethod
    def is_enabled(
        cls,
        occn: N,
        act: str,
        state: OCCausalNetState,
        act_to_idx: dict = None,
        ot_to_idx: dict = None,
    ) -> bool:
        """
        Checks whether a given activity is enabled in a given object-centric
        casal net and state.
        An activity is enabled if there exists an input marker group that can be
        bound. Start activities are always enabled.

        Parameters
        ----------
        occn
            Object-centric causal net
        act
            Activity to check
        state
            State of the OCCN
        act_to_idx
            If activities are denoted in the state by an id instead of their name,
            a dictionary mapping activities to their index has to be provided here.
        ot_to_idx
            If object types are denoted in the state by an id instead of their name,
            a dictionary mapping object types to their index has to be provided here.

        Returns
        -------
        bool
            true if enabled, false otherwise
        """
        # Start activities are always enabled
        if act.startswith("START_"):
            return True

        if act_to_idx:
            act_id = act_to_idx[act]
        else:
            act_id = act


        # preprocess Counter for this activity to a lookup table where values 
        # are sets of objects with outstanding obligations to this act
        objects = defaultdict(set)
        for rel_act, obj_id, ot_id in state[act_id].keys():
            objects[(rel_act, ot_id)].add(obj_id)



        imgs = occn.input_marker_groups[act]

        # if there are not outstanding obligations, the activity cannot be enabled
        if not state[act_id]:
            return False

        # check each img
        for img in imgs:
            # markers that allow for consumption of 0 obligations do not need to be enabled
            # at least one marker of the img needs to be enabled
            one_marker_enabled = False
            for marker in img.markers:
                min_count = marker.min_count
                rel_act_id = (
                    marker.related_activity
                    if not act_to_idx
                    else act_to_idx[marker.related_activity]
                )
                ot_id = (
                    marker.object_type
                    if not ot_to_idx
                    else ot_to_idx[marker.object_type]
                )

                num_objects = len(objects[(rel_act_id, ot_id)])
                if num_objects >= max(min_count, 1):
                    one_marker_enabled = True
                elif min_count != 0:
                    # marker is not enabled, move on to next img
                    one_marker_enabled = False
                    break
            if one_marker_enabled:
                return True
        return False

    @classmethod
    def _find_matching_marker_group(
        cls, obligations: dict, marker_groups: list
    ) -> Union[MG, None]:
        """
        Finda a matching marker group that is able to consume/produce the given obligations.

        Parameters
        ----------
        obligations : dict
            Obligations to consume, mapping related activities to a dict mapping
            object types to a set of object ids
        marker_groups : list
            List of marker groups to check

        Returns
        -------
        Union[MG, None]
            A matching marker group if found, None otherwise.
        """
        if not obligations:
            return None
        # Calculate object counts from the obligations
        obj_counts = {
            related_act: {
                ot: len(obligations[related_act][ot]) for ot in obligations[related_act]
            }
            for related_act in obligations
        }

        # check each group
        for mg in marker_groups:
            mg_dict = mg.dict_representation

            # Check that markers for all required related activities exist
            # and all required ots are present
            failure = False
            for related_act in obj_counts:
                if related_act not in mg_dict:
                    failure = True
                for ot in obj_counts[related_act]:
                    if ot not in mg_dict[related_act]:
                        failure = True
            if failure:
                continue

            # 1: check that count matches (= is within cardinality bounds)
            counts_match = all(
                mg_dict[related_act][ot][1]
                >= obj_counts.get(related_act, {}).get(ot, 0)
                >= mg_dict[related_act][ot][0]
                for related_act in mg_dict
                for ot in mg_dict[related_act]
            )
            if not counts_match:
                continue

            # 2: check key constraints
            constraints_violated = any(
                obligations.get(rel_act_1, {})
                .get(ot, set())
                .intersection(obligations.get(rel_act_2, {}).get(ot, set()))
                for (rel_act_1, ot, rel_act_2) in mg.key_constraints
            )
            if constraints_violated:
                continue

            # found matching group
            return mg

        return None

    @classmethod
    def is_binding_enabled(
        cls,
        net: N,
        act: str,
        cons: dict[str, dict[str, Set]],
        prod: dict[str, dict[str, Set]],
        state: OCCausalNetState,
    ) -> Union[tuple[MG, MG], None]:
        """
        Checks whether the given binding is enabled in the object-centric causal net.
        A binding is enabled if the activity has input and output marker groupos that
        match the given objects and the state contains all necessary obligations.


        Parameters
        ----------
        net : N
            The object-centric causal net
        act : str
            The activity to bind
        cons : dict[str, dict[str, Set]]
            The obligations to consume, mapping predecessor activities to a dict mapping
            object types to a set of object ids
        prod : dict[str, dict[str, Set]]
            The obligations to produce, mapping successor activities to a dict mapping
            object types to a set of object ids
        state : OCCausalNetState
            The current state of the OCCN

        Returns
        -------
        Union[tuple[MG, MG], None]:
            The input and output marker groups enabling the binding if it is enabled, None otherwise.
        """
        # 1: check that all consumed obligations are present in the state
        if cons:
            if any(
                state[act].get((pred, obj_id, ot), 0) <= 0
                for pred in cons.keys()
                for ot in cons[pred].keys()
                for obj_id in cons[pred][ot]
            ):
                return None
        else:
            if not prod:
                # we need to either consume or produce obligations
                return None

        # 2: Find a matching input marker group
        if act.startswith("START_"):
            if cons:
                return None
            # For START activities, we do not consume obligations, cons has to be empty
            matched_img = None
        else:
            matched_img = cls._find_matching_marker_group(
                cons, net.input_marker_groups[act]
            )
            if matched_img is None:
                return None

        # 3: Find a matching output marker group
        if act.startswith("END_"):
            if prod:
                return None
            # For START activities, we do not consume obligations, prod has to be empty
            matched_omg = None
        else:
            matched_omg = cls._find_matching_marker_group(
                prod, net.output_marker_groups[act]
            )
            if matched_omg is None:
                return None

        return (matched_img, matched_omg)

    @classmethod
    def bind_activity(
        cls,
        net: N,
        act: str,
        cons: dict[str, dict[str, Set]],
        prod: dict[str, dict[str, Set]],
        state: OCCausalNetState,
    ) -> OCCausalNetState:
        """
        Binds an activity in the object-centric causal net.
        For performance reasons, this method does not check whether the binding
        is valid given the current state. If necessary, the caller should
        ensure this, e.g., using the `is_binding_enabled` method.

        Parameters
        ----------
        net : N
            The object-centric causal net
        act : str
            The activity to bind
        cons : dict[str, dict[str, Set]]
            The obligations to consume, mapping predecessor activities to a dict mapping
            object types to a set of object ids
        prod : dict[str, dict[str, Set]]
            The obligations to produce, mapping successor activities to a dict mapping
            object types to a set of object ids
        state : OCCausalNetState
            The current state of the OCCN

        Returns
        -------
        OCCausalNetState
            The new state after binding the activity
        """
        # consume obligations
        if cons:
            consume = OCCausalNetState(
                {
                    act: Counter(
                        [
                            (pred, obj_id, ot)
                            for pred in cons
                            for ot in cons[pred]
                            for obj_id in cons[pred][ot]
                        ]
                    )
                }
            )
            state -= consume

        # produce obligations
        if prod:
            produce = OCCausalNetState(
                {
                    succ: Counter(
                        [
                            (act, obj_id, ot)
                            for ot in prod[succ]
                            for obj_id in prod[succ][ot]
                        ]
                    )
                    for succ in prod
                }
            )
            state += produce

        return state

    @classmethod
    def replay(cls, occn: N, sequence: tuple) -> bool:
        """
        Replays a sequence of bindings on the object-centric causal net.

        Parameters
        ----------
        occn : N
            The object-centric causal net to replay on.
        sequence : tuple
            A sequence of bindings, where each binding is a tuple of (activity_name, consumed_obligations, produced_obligations).
            consumed_obligations and produced_obligations are dictionaries mapping
            related activities to a dict mapping object types to a set of object ids.

        Returns
        -------
        bool
            True if the sequence can be replayed on the net, False otherwise.
        """
        # start in the empty state
        state = OCCausalNetState()

        # replay each binding
        for act, cons, prod in sequence:
            if not cls.is_binding_enabled(occn, act, cons, prod, state):
                return False

            state = cls.bind_activity(occn, act, cons, prod, state)

        # check if we are in the empty state
        if state.activities:
            return False

        return True

    @classmethod
    def enabled_bindings_start_activity(
        cls,
        occn: N,
        act: str,
        object_type: str,
        objects: set,
        act_to_idx: dict = None,
        ot_to_idx: dict = None,
    ) -> tuple:
        """
        Computes all enabled bindings for a start activity with a given set of objects.
        These bindings will produce obligations for at least one of the objects.
        Based on the `enabled_bindings` method, but specialized for start activities.

        Parameters
        ----------
        occn : N
            The object-centric causal net
        act : str
            The start activity to bind
        object_type : str
            The object type of the start activity
        objects : set
            A set of objects to bind to the activity. All bindings will bind at least one.
        act_to_idx : dict, optional
            If activities are denoted in the state by an id instead of their name,
            a dictionary mapping activities to their index has to be provided here.
        ot_to_idx : dict, optional
            If object types are denoted in the state by an id instead of their name,
            a dictionary mapping object types to their index has to be provided here.

        Returns
        -------
        tuple
            A tuple where entries are tuples of activity id, consumed objects, and produced objects.
            Consumed / produces are tuples of (predecessor/successor activity id, objects_per_ot)
            where objects_per_ot is a tuples of entries (object_type, objects)
            where objects is a tuple (obj_id_1, obj_id_2, ...).
            If act_to_idx and ot_to_idx are provided, indices instead of names are
            used for activities and object types.
        """
        assert act.startswith("START_"), "This method is only for start activities."
        if act_to_idx:
            act_id = act_to_idx[act]
        else:
            act_id = act

        if ot_to_idx:
            ot_id = ot_to_idx[object_type]
        else:
            ot_id = object_type

        # create a list of fake consumed tuples that binds the powerset of objects
        fake_consumed = []
        for i in range(len(objects)):
            for combo in itertools.combinations(objects, i + 1):
                fake_consumed.append((
                    (-1, (
                        (ot_id, combo),
                        )
                     )
                    ,))

        # create the corresponding produced tuples
        memo_produced = {}
        memo_ot_assignments = {}

        enabled_bindings = []

        for consumed in fake_consumed:
            possible_produced_for_consumed = cls.__generate_produced_for_consumed(
                occn,
                act,
                consumed,
                memo_produced,
                memo_ot_assignments,
                act_to_idx,
                ot_to_idx,
            )

            for produced in possible_produced_for_consumed:
                enabled_bindings.append((act_id, None, produced))

        return tuple(enabled_bindings)

    @classmethod
    def enabled_bindings(
        cls,
        occn: N,
        act: str,
        state: OCCausalNetState,
        act_to_idx: dict = None,
        ot_to_idx: dict = None,
    ) -> tuple:
        """
        Computes all enabled bindings for a given activity in a given state.

        Parameters
        ----------
        occn : N
            The object-centric causal net
        act : str
            The activity to bind
        state : OCCausalNetState
            The current state of the OCCN
        act_to_idx : dict, optional
            If activities are denoted in the state by an id instead of their name,
            a dictionary mapping activities to their index has to be provided here.
        ot_to_idx : dict, optional
            If object types are denoted in the state by an id instead of their name,
            a dictionary mapping object types to their index has to be provided here.

        Returns
        -------
        tuple
            A tuple where entries are tuples of activity id, consumed objects, and produced objects.
            Consumed / produces are tuples of (predecessor/successor activity id, objects_per_ot)
            where objects_per_ot is a tuples of entries (object_type, objects)
            where objects is a tuple (obj_id_1, obj_id_2, ...).
            If act_to_idx and ot_to_idx are provided, indices instead of names are
            used for activities and object types.
        """
        if act_to_idx:
            act_id = act_to_idx[act]
        else:
            act_id = act

        # outstanding obligations for the activity
        obligations = state[act_id]

        # pre-process obligations to a dict where keys are (related activity, object_type)
        # and values are sets of object ids (neglecting the count)
        obligations_dict = defaultdict(set)
        for (related_act, obj_id, ot_id), _ in obligations.items():
            obligations_dict[(related_act, ot_id)].add(obj_id)

        # ----------- Create all possibilities for consumed -----------

        possible_consumed = cls.__generate_consumed(
            occn, act, obligations_dict, act_to_idx, ot_to_idx
        )
        if not possible_consumed:
            return ()

        # ----------- Create all possible produced tuples per consumed tuple -----------

        final_bindings = []
        # Memoization for produced tuples, keyed by comsumed object sets by object type
        memo_produced = {}
        # Memoization for sub-problem of assigning objects of one ot for one omg
        memo_ot_assignments = {}

        for consumed in possible_consumed:
            # End activities do not produce obligations
            if act.startswith("END_"):
                possible_produced_for_consumed = {None}
            else:
                possible_produced_for_consumed = cls.__generate_produced_for_consumed(
                    occn,
                    act,
                    consumed,
                    memo_produced,
                    memo_ot_assignments,
                    act_to_idx,
                    ot_to_idx,
                )

            # Create final bindings
            for produced in possible_produced_for_consumed:
                final_bindings.append((act_id, consumed, produced))

        return tuple(final_bindings)

    @classmethod
    def __generate_consumed(
        cls,
        occn: N,
        act: str,
        obligations_dict: dict,
        act_to_idx: dict = None,
        ot_to_idx: dict = None,
    ) -> Set[tuple]:
        """
        Generates all possible consumed tuples for a given activity and obligations.
        """
        possible_consumed = set()
        for img in occn.input_marker_groups[act]:
            img_dict = img.dict_representation

            # preprocess key constraints if ids are used
            key_constraints_by_id = []
            if act_to_idx:
                for rel_act_1_id, ot_id, rel_act_2_id in img.key_constraints:
                    key_constraints_by_id.append(
                        (
                            act_to_idx[rel_act_1_id],
                            ot_to_idx[ot_id],
                            act_to_idx[rel_act_2_id],
                        )
                    )
            else:
                key_constraints_by_id = img.key_constraints

            # get all combinations on which objects we can consume given the img
            keys, combinations_iter_list = (
                cls.__generate_predecessor_object_combinations(
                    img_dict, obligations_dict, act_to_idx, ot_to_idx
                )
            )

            if not keys:
                # img not enabled
                continue

            # from the consumed_per_pred, create all combinations of consumed obligations
            # these are added to possible_consumed
            cls.__consumed_from_predecessor_combinations(
                possible_consumed, keys, combinations_iter_list, key_constraints_by_id
            )

        return possible_consumed

    @classmethod
    def __generate_predecessor_object_combinations(
        cls,
        img_dict: dict,
        obligations_dict: dict,
        act_to_idx: dict = None,
        ot_to_idx: dict = None,
    ):
        """
        Generates all combinations of objects from obligations_dict that can be consumed given the img_dict.
        """
        # we build two lists: keys of format (predecessor_id, ot_id) and
        # a list of iterations where each iterator yields all possible object
        # combinations for all (predecessor, ot) pairs
        keys = []
        combinations_iter_list = []

        for predecessor in img_dict:
            for ot in img_dict[predecessor]:
                min_count, max_count = img_dict[predecessor][ot]

                if act_to_idx:
                    pred_id = act_to_idx[predecessor]
                else:
                    pred_id = predecessor

                if ot_to_idx:
                    ot_id = ot_to_idx[ot]
                else:
                    ot_id = ot

                # get all objects for obligations of the predecessor activity and object type
                objects_for_pred = sorted(obligations_dict[(pred_id, ot_id)])

                if len(objects_for_pred) < min_count:
                    # get to next img, this one cannot be bound
                    return [], []
                if not objects_for_pred:
                    # no objects available for this (pred, ot) pair, skip
                    continue
                else:
                    # get all combinations of objects
                    keys.append((pred_id, ot_id))
                    combinations_for_req = itertools.chain.from_iterable(
                        [
                            itertools.combinations(objects_for_pred, r)
                            for r in range(
                                # this (pred, ot) pair may consume min_count to max_count objects
                                min_count,
                                min(max_count, len(objects_for_pred)) + 1,
                            )
                        ]
                    )
                    combinations_iter_list.append(combinations_for_req)

        return keys, combinations_iter_list

    @staticmethod
    def __consumed_from_predecessor_combinations(
        possible_consumed: set,
        keys: list,
        combinations_iter_list: list,
        key_constraints_by_id: list,
    ):
        """
        Generates all consumed tuples given all possible assignments from
        (predecessor, object type) tuples to sets of objects that may be consumed
        by this pair.
        """
        # create cross product of all options per predecessor and object type
        cross_product_iter = itertools.product(*combinations_iter_list)
        for binding_selection in cross_product_iter:
            # create dict mapping predecessor activitiy to (ot_id, objects) tuples
            grouped_by_pred = defaultdict(dict)
            for (pred_id, ot_id), objects in zip(keys, binding_selection):
                if len(objects) > 0:
                    grouped_by_pred[pred_id][ot_id] = objects

            # if all markers of the img are optional, we can skip empty bindings
            if not grouped_by_pred:
                continue

            # Check key constraints
            constraint_violated = False
            for rel_act_1_id, ot_id, rel_act_2_id in key_constraints_by_id:
                objects1 = grouped_by_pred.get(rel_act_1_id, {}).get(ot_id)
                objects2 = grouped_by_pred.get(rel_act_2_id, {}).get(ot_id)
                if objects1 and objects2 and set(objects1).intersection(objects2):
                    # key constraint violated, move on to next binding
                    constraint_violated = True
                    break

            if constraint_violated:
                continue

            # convert to memory-efficient tuple representation
            consumed_tuple = tuple(
                # sorting necessary to ensure duplicate-free tuples in possible_consumed
                (pred_id, tuple(sorted(ot_obj_pairs.items())))
                for pred_id, ot_obj_pairs in sorted(grouped_by_pred.items())
            )
            # add to possible consumed obligations (duplicate-free)
            possible_consumed.add(consumed_tuple)

    @classmethod
    def __generate_produced_for_consumed(
        cls,
        occn: N,
        act: str,
        consumed: tuple,
        memo_produced: dict,
        memo_ot_assignments: dict,
        act_to_idx: dict = None,
        ot_to_idx: dict = None,
    ) -> Set[tuple]:
        """
        Generates all possible produced tuples for a given consumed tuple.
        """
        # 1. Process consumed tuple into sets of consumed objects per ot
        consumed_objects_by_ot = defaultdict(set)
        for _, ot_obj_pairs in consumed:
            for ot_id, objects in ot_obj_pairs:
                consumed_objects_by_ot[ot_id].update(objects)

        # Create hashable key for memo
        consumed_key = cls.__make_hashable(consumed_objects_by_ot)

        # 2. Check memo cache
        if consumed_key in memo_produced:
            possible_produced_for_consumed = memo_produced[consumed_key]
        else:
            # Compute all possible produced tuples
            possible_produced_for_consumed = set()  # set to avoid duplicates
            # Compute per omg; cache to avoid recomputation
            for omg in occn.output_marker_groups[act]:
                produced_for_omg = cls.__generate_produced_for_omg(
                    omg,
                    consumed_objects_by_ot,
                    memo_ot_assignments,
                    act_to_idx,
                    ot_to_idx,
                )
                possible_produced_for_consumed.update(produced_for_omg)

            # Store result in cache
            memo_produced[consumed_key] = possible_produced_for_consumed

        return possible_produced_for_consumed

    @classmethod
    def __generate_produced_for_omg(
        cls, omg, consumed_objects_by_ot, memo, act_to_idx, ot_to_idx
    ):
        """
        Generates all possible produced tuples for a given output marker group and
        consumed objects by object type (these need to be produced).
        """
        omg_dict = omg.dict_representation

        # Pre-process omg requirements and key constraints into efficient lookups in case ids are used
        reqs_by_ot = defaultdict(list)
        key_constraints_by_ot = defaultdict(set)

        for succ_name, ot_map in omg_dict.items():
            succ_id = act_to_idx[succ_name] if act_to_idx else succ_name
            for ot_name, (min_c, max_c) in ot_map.items():
                ot_id = ot_to_idx[ot_name] if ot_to_idx else ot_name
                reqs_by_ot[ot_id].append((succ_id, min_c, max_c))

        for s1_name, ot_name, s2_name in omg.key_constraints:
            s1_id = act_to_idx[s1_name] if act_to_idx else s1_name
            ot_id = ot_to_idx[ot_name] if ot_to_idx else ot_name
            s2_id = act_to_idx[s2_name] if act_to_idx else s2_name
            key_constraints_by_ot[ot_id].add(frozenset([s1_id, s2_id]))

        # Check if objects types match for early exit
        consumed_ots = set(consumed_objects_by_ot.keys())
        required_ots = set(reqs_by_ot.keys())

        if not consumed_ots.issubset(required_ots):
            # omg has no marker for some consumed object type
            return []

        missing_required_ots = required_ots - consumed_ots
        for missing_ot in missing_required_ots:
            # marker has an ot that was not consumed
            # this is an issue if that marker is not optional
            if any(min_c > 0 for _, min_c, _ in reqs_by_ot[missing_ot]):
                return []

        # Get all possible assignments of successor activities to consumed objects
        # this is done per individually per object type
        ot_ids_in_order, assignments_in_order = cls.__generate_successor_assignments(
            omg, memo, consumed_objects_by_ot, reqs_by_ot, key_constraints_by_ot
        )

        # Get cross product of all assignments per object type to get all possible produced tuples
        final_produced_tuples = cls.__produced_from_successor_assignments(
            ot_ids_in_order, assignments_in_order
        )

        return final_produced_tuples

    @staticmethod
    def __generate_successor_assignments(
        omg: MG,
        memo: dict,
        consumed_objects_by_ot: dict,
        reqs_by_ot: dict,
        key_constraints_by_ot: dict,
    ):
        """
        Generates all possible assignments of consumed objects to successor activities.
        """
        # we generate all possible assignments of consumed objects to successor activities
        # and then prune the ones that violate key constraints and
        # the ones that violate the min/max cardinality requirements
        ot_ids_in_order = []
        assignments_in_order = []
        # Solve assignment problem for each object type separetly
        # this is cached since different consumed_objects_by_ot may have
        # the same object sets for the same ot_id
        for ot_id, objects in consumed_objects_by_ot.items():
            memo_key = (id(omg), ot_id, frozenset(objects))
            if memo_key in memo:
                valid_ot_assignments = memo[memo_key]
            else:
                ot_reqs = reqs_by_ot.get(ot_id, [])
                successors_for_ot = [req[0] for req in ot_reqs]
                ot_key_constraints = key_constraints_by_ot.get(ot_id, set())

                per_object_choices = []
                for obj in objects:
                    obj_choices = []
                    # object may be assigned to 1 or more successors
                    for i in range(1, len(successors_for_ot) + 1):
                        # get all combinations of successors of size i
                        for succ_set in itertools.combinations(successors_for_ot, i):
                            # check key constraints
                            is_valid = all(
                                frozenset(pair) not in ot_key_constraints
                                for pair in itertools.combinations(succ_set, 2)
                            )
                            if is_valid:
                                obj_choices.append(succ_set)
                    if not obj_choices:
                        return [], []  # An object has no valid assignment
                    per_object_choices.append(obj_choices)

                # Create all combinations of assignments with cross-product over all objects
                valid_ot_assignments = []
                for assignment_choice in itertools.product(*per_object_choices):
                    final_assignment = defaultdict(list)
                    for obj, succs in zip(objects, assignment_choice):
                        for succ in succs:
                            final_assignment[succ].append(obj)

                    # Check cardinality constraints
                    counts_ok = True
                    for succ_id, min_c, max_c in ot_reqs:
                        count = len(final_assignment.get(succ_id, []))
                        if not (min_c <= count <= max_c):
                            counts_ok = False
                            break

                    if counts_ok:
                        # add to valid assignments
                        canonical_assignment = {
                            s: tuple(sorted(o)) for s, o in final_assignment.items()
                        }
                        valid_ot_assignments.append(canonical_assignment)

                # Store in memoization cache
                memo[memo_key] = valid_ot_assignments

            # Only proceed if we have valid assignments for this ot_id
            if not valid_ot_assignments:
                return [], []

            # Store ot_id and valid assignments
            ot_ids_in_order.append(ot_id)
            assignments_in_order.append(valid_ot_assignments)

        return ot_ids_in_order, assignments_in_order

    @staticmethod
    def __produced_from_successor_assignments(
        ot_ids_in_order: list, assignments_in_order: list
    ) -> Set[tuple]:
        """
        Generates all produced tuples given all possible assignments from
        successor activities to sets of objects that may be produced for this activity.
        """
        final_produced_tuples = set()  # avoid duplicates
        for final_choice in itertools.product(*assignments_in_order):
            # convert to dict first
            produced_grouped_by_succ = defaultdict(dict)

            for ot_id, ot_assignment_dict in zip(ot_ids_in_order, final_choice):
                for succ_id, assigned_objects in ot_assignment_dict.items():
                    if len(assigned_objects) > 0:
                        produced_grouped_by_succ[succ_id][ot_id] = assigned_objects

            # Has to produce at least one object
            if not produced_grouped_by_succ:
                continue

            # Convert to tuple representation
            produced_tuple = tuple(
                (succ_id, tuple(sorted(ot_obj_pairs.items())))
                for succ_id, ot_obj_pairs in sorted(produced_grouped_by_succ.items())
            )
            final_produced_tuples.add(produced_tuple)
        return final_produced_tuples

    @staticmethod
    def __make_hashable(d):
        """Helper function to create a hashable key from a dictionary."""
        # Converts a dict of {ot_id: set(obj_ids)} to a frozenset of items
        # so it can be used as a dictionary key for memoization.
        return frozenset((k, frozenset(v)) for k, v in d.items())
