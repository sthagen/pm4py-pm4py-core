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
from copy import deepcopy
from typing import Collection, Dict, Any, Set
from pm4py.objects.petri_net.obj import PetriNet


class OCMarking(defaultdict):
    """
    An object-centric marking represented as a mapping from places to multisets of object IDs.

    ```
    marking = OCMarking({p: Counter(["object1", "object2"])})
    ```
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the OCMarking, querying unspecified places defaults to an empty multiset."""
        super().__init__(Counter)
        data_args = args
        if args and args[0] is Counter:
            data_args = args[1:]
        initial_data = dict(*data_args, **kwargs)
        for place, objects in initial_data.items():
            self[place] = Counter(objects)

    def __hash__(self):
        return frozenset(
            (place, frozenset(counter.items()))
            for place, counter in self.items()
            if counter
        ).__hash__()

    def __eq__(self, other):
        if not isinstance(other, OCMarking):
            return False
        return all(
            self.get(p, Counter()) == other.get(p, Counter())
            for p in set(self.keys()) | set(other.keys())
        )

    def __le__(self, other):
        for place, self_counter in self.items():
            other_counter = other.get(place, Counter())
            # Every object count in self must be less than or equal to the count in other.
            if not all(
                other_counter.get(obj_id, 0) >= count
                for obj_id, count in self_counter.items()
            ):
                return False
        return True

    def __add__(self, other):
        result = OCMarking()
        for place, self_counter in self.items():
            result[place] += self_counter
        for place, other_counter in other.items():
            result[place] += other_counter
        return result

    def __sub__(self, other):
        result = OCMarking()
        for place, self_counter in self.items():
            diff = self_counter - other.get(place, Counter())
            if diff != Counter():
                result[place] = diff
        return result

    def __repr__(self):
        # e.g.  ["p1:{o1, o2}", "p2: {o2, o3}", …]
        sorted_entries = sorted(self.items(), key=lambda item: item[0].name)
        return (
            ", ".join(f"{place.name}: {objects}" for (place, objects) in sorted_entries)
            if sorted_entries
            else "[]"
        )

    def __str__(self):
        return self.__repr__()

    def __deepcopy__(self, memodict={}):
        new_marking = OCMarking()
        memodict[id(self)] = new_marking
        for place, objects in self.items():
            place_copy = (
                memodict[id(place)]
                if id(place) in memodict
                else deepcopy(place, memodict)
            )
            counter_copy = (
                memodict[id(objects)]
                if id(objects) in memodict
                else deepcopy(objects, memodict)
            )
            new_marking[place_copy] = counter_copy
        return new_marking

    @property
    def places(self) -> Set:
        """
        Returns the set of all places in the marking that contain tokens.

        Returns
        ------------
        Set[str]
            Set of place names in the marking.
        """
        return set([p for p in self.keys() if self[p]])


class OCPetriNet(PetriNet):
    class Place(PetriNet.Place):
        def __init__(
            self, name, object_type, in_arcs=None, out_arcs=None, properties=None
        ):
            """
            Constructor

            Parameters
            ------------
            name
                human-readable identifier
            object_type
                the type/color of objects this place holds
            in_arcs
                set of incoming arcs
            out_arcs
                set of outgoing arcs
            properties
                dict of additional properties
            """
            super().__init__(
                name, in_arcs=in_arcs, out_arcs=out_arcs, properties=properties
            )
            self.__object_type = object_type

        def add_in_arc(self, arc):
            """
            Adds an incoming arc to the place.

            Parameters
            ------------
            arc: OCPetriNet.Arc
                the arc to add
            """
            self.__in_arcs.add(arc)
            assert arc.target == self
            assert arc.object_type == self.object_type

        def add_out_arc(self, arc):
            """
            Adds an outgoing arc to the place.

            Parameters
            ------------
            arc: OCPetriNet.Arc
                the arc to add
            """
            self.__out_arcs.add(arc)
            assert arc.source == self
            assert arc.object_type == self.object_type

        def __get_object_type(self):
            return self.__object_type

        def __repr__(self):
            return f"{self.name}[{self.object_type}]"

        def __deepcopy__(self, memodict={}):
            if id(self) in memodict:
                return memodict[id(self)]
            new_place = OCPetriNet.Place(
                self.name, self.object_type, properties=self.properties
            )
            memodict[id(self)] = new_place
            # attached arcs
            for arc in self.in_arcs:
                arc_copy = deepcopy(arc, memodict)
                new_place.in_arcs.add(arc_copy)
            for arc in self.out_arcs:
                arc_copy = deepcopy(arc, memodict)
                new_place.out_arcs.add(arc_copy)

            return new_place

        object_type = property(__get_object_type)

    class Transition(PetriNet.Transition):
        def add_in_arc(self, arc):
            """
            Adds an incoming arc to the place.

            Parameters
            ------------
            arc: OCPetriNet.Arc
                the arc to add
            """
            self.__in_arcs.add(arc)
            assert arc.target == self

        def add_out_arc(self, arc):
            """
            Adds an outgoing arc to the place.

            Parameters
            ------------
            arc: OCPetriNet.Arc
                the arc to add
            """
            self.__out_arcs.add(arc)
            assert arc.source == self


    class Arc(PetriNet.Arc):
        def __init__(
            self,
            source,
            target,
            object_type,
            is_variable=False,
            properties=None,
        ):
            """
            Constructor

            Parameters
            ------------
            source
                source place / transition
            target
                target place / transition
            is_variable
                whether the arc is a variable arc
            properties
                dict of additional properties
            """
            super().__init__(source, target, weight=1, properties=properties)
            self.__object_type = object_type
            self.__is_variable = is_variable

        def __get_object_type(self):
            return self.__object_type

        def __get_is_variable(self):
            return self.__is_variable

        def __repr__(self):
            base = super().__repr__()
            var = "variable" if self.is_variable else "non-variable"
            return f"{base}:{self.object_type}:{var}"

        def __deepcopy__(self, memodict={}):
            if id(self) in memodict:
                return memodict[id(self)]
            new_source = memodict.get(id(self.source), deepcopy(self.source, memodict))
            new_target = memodict.get(id(self.target), deepcopy(self.target, memodict))
            new_arc = OCPetriNet.Arc(
                new_source,
                new_target,
                self.object_type,
                is_variable=self.is_variable,
                properties=self.properties,
            )
            memodict[id(self)] = new_arc
            # reattach
            new_source.out_arcs.add(new_arc)
            new_target.in_arcs.add(new_arc)
            return new_arc

        object_type = property(__get_object_type)
        is_variable = property(__get_is_variable)

    def __init__(
        self,
        name: str = None,
        places: Collection[Place] = None,
        transitions: Collection[Transition] = None,
        arcs: Collection[Arc] = None,
        initial_marking: OCMarking = None,
        final_marking: OCMarking = None,
        properties: Dict[str, Any] = None,
    ):
        """
        Constructor

        Parameters
        ------------
        name
            human-readable identifier
        places
            collection of places
        transitions
            collection of transitions
        arcs
            collection of arcs
        initial_marking
            initial marking of the net
        final_marking
            final marking of the net
        properties
            dict of additional properties
        """
        super().__init__(
            name=name,
            places=places,
            transitions=transitions,
            arcs=arcs,
            properties=properties,
        )
        self.__initial_marking = initial_marking
        self.__final_marking = final_marking
        self.__assert_well_formed()

    def __get_initial_marking(self):
        return self.__initial_marking

    def __get_final_marking(self):
        return self.__final_marking

    def __deepcopy__(self, memodict={}):
        new_net = OCPetriNet(self.name)
        memodict[id(self)] = new_net
        for p in self.places:
            p_copy = OCPetriNet.Place(p.name, p.object_type, properties=p.properties)
            new_net.places.add(p_copy)
            memodict[id(p)] = p_copy
        for t in self.transitions:
            t_copy = OCPetriNet.Transition(t.name, t.label, properties=t.properties)
            new_net.transitions.add(t_copy)
            memodict[id(t)] = t_copy
        for a in self.arcs:
            src = memodict[id(a.source)]
            tgt = memodict[id(a.target)]
            a_copy = OCPetriNet.Arc(
                src,
                tgt,
                a.object_type,
                is_variable=a.is_variable,
                properties=a.properties,
            )
            src.out_arcs.add(a_copy)
            tgt.in_arcs.add(a_copy)
            new_net.arcs.add(a_copy)
            memodict[id(a)] = a_copy

        def copy_marking(marking):
            if marking is None:
                return None
            copied_marking = OCMarking()
            for place, objects in marking.items():
                place_copy = memodict.get(id(place))
                if place_copy is None:
                    place_copy = OCPetriNet.Place(
                        place.name, place.object_type, properties=place.properties
                    )
                    memodict[id(place)] = place_copy
                    new_net.places.add(place_copy)
                copied_marking[place_copy] = objects.copy()
            return copied_marking

        new_net._OCPetriNet__initial_marking = copy_marking(self.initial_marking)
        new_net._OCPetriNet__final_marking = copy_marking(self.final_marking)
        return new_net

    def __repr__(self):
        ret = [f"OCPN {self.name}:\nobject_types: ["]
        object_types_rep = []
        for ot in self.object_types:
            object_types_rep.append(ot)
        object_types_rep.sort()
        ret.append(" " + ", ".join(object_types_rep) + " ")
        ret.append("]\nplaces: [")
        places_rep = []
        for place in self.places:
            places_rep.append(repr(place))
        places_rep.sort()
        ret.append(" " + ", ".join(places_rep) + " ")
        ret.append("]\ntransitions: [")
        trans_rep = []
        for trans in self.transitions:
            trans_rep.append(repr(trans))
        trans_rep.sort()
        ret.append(" " + ", ".join(trans_rep) + " ")
        ret.append("]\narcs: [")
        arcs_rep = []
        for arc in self.arcs:
            arcs_rep.append(repr(arc))
        arcs_rep.sort()
        ret.append(" " + ", ".join(arcs_rep) + " ")
        ret.append("]\ninitial_marking: [")
        initial_marking_rep = [repr(self.initial_marking)]
        ret.append(" " + ", ".join(initial_marking_rep) + " ")
        ret.append("]\nfinal_marking: [")
        final_marking_rep = [repr(self.final_marking)]
        ret.append(" " + ", ".join(final_marking_rep) + " ")
        ret.append("]")
        return "".join(ret)

    def __str__(self):
        return self.__repr__()

    def __assert_well_formed(self):
        """
        Asserts that the OCPN is well-formed, i.e., all transitions have,
        for each object type, only either variable or non-variable arcs, but not both.
        """
        for t in self.transitions:
            for ot in self.object_types:
                var_arcs = {
                    a for a in t.in_arcs if a.is_variable and a.object_type == ot
                }
                non_var_arcs = {
                    a for a in t.in_arcs if not a.is_variable and a.object_type == ot
                }
                if var_arcs and non_var_arcs:
                    raise ValueError(f"Transition {t} is not well-formed.")

    initial_marking = property(__get_initial_marking)
    final_marking = property(__get_final_marking)

    @property
    def object_types(self) -> Set[str]:
        """
        Returns the set of all object types (colors) used in this net.

        Returns
        ------------
        Set[str]
            Set of object types (colors) used in this net.
        """
        return {p.object_type for p in self.places}
