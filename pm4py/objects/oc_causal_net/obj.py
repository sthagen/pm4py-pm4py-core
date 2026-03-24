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

from itertools import combinations
import networkx as nx
from pm4py.objects.oc_causal_net.utils.filters import filter4
from typing import Tuple, List, Dict
from collections import Counter, defaultdict
from functools import cached_property


class OCCausalNet(object):
    """
    Object-Centric Causal Net capturing dependency graph and marker groups.
    """

    class Marker(object):
        """
        Represents a single marker in an object-centric causal net.
        """

        def __init__(
            self, related_activity, object_type, count_range: Tuple, marker_key: int
        ):
            """
            Constructor

            Parameters
            ----------
            related_activity : str
                Activity that has to fulfill the marker (predecessor or successor)
            object_type : str
                object type of the marker
            count_range : Tuple
                Min and max number of markers consumable ('cardinalities')
            marker_key : int
                Key of the marker
            """
            self.__related_activity = related_activity
            self.__object_type = object_type
            self.__count_range = count_range
            self.__marker_key = marker_key

        def __repr__(self):
            return f"(a={self.related_activity}, ot={self.object_type}, c={self.count_range}, k={self.marker_key})"

        def __str__(self):
            return self.__repr__()

        def __hash__(self):
            return hash(
                (
                    self.related_activity,
                    self.object_type,
                    self.min_count,
                    self.max_count,
                    self.marker_key,
                )
            )

        def __get_related_activity(self):
            return self.__related_activity

        def __get_object_type(self):
            return self.__object_type

        def __get_count_range(self):
            return self.__count_range

        def __get_min_count(self):
            return self.__count_range[0]

        def __get_max_count(self):
            return self.__count_range[1]

        def __get_marker_key(self):
            return self.__marker_key

        def __set_marker_key(self, marker_key: int):
            self.__marker_key = marker_key

        def __eq__(self, other):
            if isinstance(other, OCCausalNet.Marker):
                return (
                    self.related_activity == other.related_activity
                    and self.object_type == other.object_type
                    and self.min_count == other.min_count
                    and self.max_count == other.max_count
                    and self.marker_key == other.marker_key
                )
            return False

        related_activity = property(__get_related_activity)
        object_type = property(__get_object_type)
        count_range = property(__get_count_range)
        min_count = property(__get_min_count)
        max_count = property(__get_max_count)
        marker_key = property(__get_marker_key, __set_marker_key)

    class MarkerGroup(object):
        """
        Represents a group of markers. A group of markers semantically
        represents the AND gate of all markers in the group.
        """

        def __init__(
            self,
            markers: List["OCCausalNet.Marker"],
            support_count: int = float("inf"),
        ):
            """
            Constructor

            Parameters
            ----------
            markers : List[OCCausalNet.Marker]
                List of markers that comprise the group
            support_count : int
                Frequency of this marker group in the event log. May be used to
                filter infrequent marker groups.
                Default is inf.
            """
            self.__markers = markers
            self.__support_count = support_count

        def __repr__(self):
            return f"({self.markers}, count={self.support_count})"

        def __str__(self):
            return self.__repr__()

        def __eq__(self, other):
            if isinstance(other, OCCausalNet.MarkerGroup):
                return (
                    Counter(self.markers) == Counter(other.markers)
                    and self.support_count == other.support_count
                )
            return False

        def __hash__(self):
            return hash(
                (
                    frozenset(self.markers),
                    self.support_count,
                )
            )

        def __get_markers(self):
            return self.__markers

        def __get_support_count(self):
            return self.__support_count

        @cached_property
        def dict_representation(self):
            """
            Returns a dictionary representation of the marker group for
            efficient checking if the marker group can be bound with a
            given set of objects per related activity and object type.
            Is only computed once and cached.
            Is invalid if the marker group is changed after initialization.
            Assumes that the marker group is valid, i.e., there is at most one marker per
            related activity and object type.

            Returns
            -------
            defaultdict[str, defaultdict[str, tuple[int, int]]]
                Dictionary representation of the marker group, mapping
                related activities to objects types to min and max cardinalities.
            """
            result = defaultdict(lambda: defaultdict(lambda: (float("inf"), 0)))
            for marker in self.markers:
                related_activity = marker.related_activity
                object_type = marker.object_type
                result[related_activity][object_type] = (
                    marker.min_count,
                    marker.max_count if marker.max_count != -1 else float("inf"),
                )
            return result

        @cached_property
        def key_constraints(self):
            """
            Returns all tuples (related_activity, object_type, related_activity_2) that
            cannot share objects due to having the same key.
            Is only computed once and cached.
            Is invalid if the marker group is changed after initialization.

            Returns
            -------
            List[Tuple[str, str, str]]
                List of tuples (related_activity, object_type, related_activity_2)
                that cannot share the same marker key.
            """
            # group related activities by (marker_key, object_type)
            grouped = defaultdict(list)
            for marker in self.markers:
                grouped[(marker.marker_key, marker.object_type)].append(
                    marker.related_activity
                )

            # Generate constraints from groups with >= 2 elements
            constraints = []
            for (marker_key, object_type), related_activities in grouped.items():
                if len(related_activities) > 1:
                    for act1, act2 in combinations(related_activities, 2):
                        constraints.append((act1, object_type, act2))

            return constraints

        markers = property(__get_markers)
        support_count = property(__get_support_count)

    def __init__(
        self,
        dependency_graph: nx.MultiDiGraph,
        output_marker_groups: Dict[str, List["OCCausalNet.MarkerGroup"]],
        input_marker_groups: Dict[str, List["OCCausalNet.MarkerGroup"]],
        activity_count: Dict[str, int] = None,
        relative_occurrence_threshold: float = 0,
    ):
        """
        Constructor

        Parameters
        ----------
        dependency_graph : nx.MultiDiGraph
            Object-centric dependency graph
            Arc (a, object_type, a') must be encoded as dg[a][a'][object_type] = {"object_type": object_type}
        output_marker_groups : Dict[str, List[OCCausalNet.MarkerGroup]]
            Output marker groups per activity
        input_marker_groups : Dict[str, List[OCCausalNet.MarkerGroup]]
            Input marker groups per activity
        activity_count : Dict[str, int]
            Activity counts in the event log for filtering of infrequent marker groups.
        relative_occurrence_threshold : float
            Relative threshold for filtering infrequent marker groups. Range is [0,1].
            Default is 0, meaning no filtering.
        """
        self.__dependency_graph = dependency_graph
        self.__activities = list(dependency_graph._node.keys())
        if activity_count is None:
            activity_count = {act: 1 for act in self.activities}
        self.__edges = dependency_graph._succ
        self.__relative_occurrence_threshold = relative_occurrence_threshold
        self.__input_marker_groups, self.__output_marker_groups = filter4(
            input_marker_groups,
            output_marker_groups,
            self.__relative_occurrence_threshold,
            activity_count,
        )
        self.__object_types = {
            o.object_type
            for binds in self.__input_marker_groups.values()
            for bs in binds
            for o in bs.markers
        }
        self.__activity_count = activity_count

    def __repr__(self):
        # a OCCN is fully defined by its activities and marker groups
        ret = f"Activities: {self.activities}"
        for act in self.activities:
            img = (
                self.input_marker_groups[act] if act in self.input_marker_groups else []
            )
            ret += f"\nInput_marker_groups[{act}]: {img}\n"
            omg = (
                self.output_marker_groups[act]
                if act in self.output_marker_groups
                else []
            )
            ret += f"Output_marker_groups[{act}]: {omg}"
        return ret

    def __str__(self):
        return self.__repr__()

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        if isinstance(other, OCCausalNet):
            def normalize_edges(edges):
                normalized = Counter()
                for source, target_dict in edges.items():
                    for target, key_dict in target_dict.items():
                        for edge_key, attributes in key_dict.items():
                            object_type = (
                                attributes.get("object_type")
                                if isinstance(attributes, dict)
                                else None
                            )
                            normalized[(source, target, edge_key, object_type)] += 1
                return normalized

            return (
                set(self.activities) == set(other.activities)
                and normalize_edges(self.edges) == normalize_edges(other.edges)
                and all(
                    Counter(self.input_marker_groups.get(a, []))
                    == Counter(other.input_marker_groups.get(a, []))
                    for a in self.activities
                )
                and all(
                    Counter(self.output_marker_groups.get(a, []))
                    == Counter(other.output_marker_groups.get(a, []))
                    for a in self.activities
                )
                and set(self.object_types) == set(other.object_types)
                and all(
                    self.activity_count.get(a, 0) == other.activity_count.get(a, 0)
                    for a in self.activities
                )
                and self.relative_occurrence_threshold
                == other.relative_occurrence_threshold
            )
        return False

    def __get_dependency_graph(self):
        return self.__dependency_graph

    def __get_activities(self):
        return self.__activities

    def __get_edges(self):
        return self.__edges

    def __get_input_marker_groups(self):
        return self.__input_marker_groups

    def __get_output_marker_groups(self):
        return self.__output_marker_groups

    def __get_object_types(self):
        return self.__object_types

    def __get_activity_count(self):
        return self.__activity_count

    def __get_relative_occurrence_threshold(self):
        return self.__relative_occurrence_threshold

    dependency_graph = property(__get_dependency_graph)
    activities = property(__get_activities)
    edges = property(__get_edges)
    input_marker_groups = property(__get_input_marker_groups)
    output_marker_groups = property(__get_output_marker_groups)
    object_types = property(__get_object_types)
    activity_count = property(__get_activity_count)
    relative_occurrence_threshold = property(__get_relative_occurrence_threshold)
