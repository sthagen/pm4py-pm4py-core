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

from typing import Set


def pre_set(elem, object_type: str = None) -> Set:
    """
    Returns the set of predecessors of an element (place or transition) in an object-centric Petri net.
    Restricted to predecessors connected using arcs of the object type, if specified.

    Parameters
    ----------
    elem
        Element (place or transition) for which to get the predecessors
    object_type
        Object type to restrict the predecessors to (optional)

    Returns
    -------
    Set
        Set of predecessor elements (places or transitions) of the specified object type.
    """
    pre = set()
    for a in elem.in_arcs:
        if object_type is None or a.object_type == object_type:
            pre.add(a.source)
    return pre

def post_set(elem, object_type: str = None) -> Set:
    """
    Returns the set of successors of an element (place or transition) in an object-centric Petri net.
    Restricted to successors connected using arcs of the object type, if specified.

    Parameters
    ----------
    elem
        Element (place or transition) for which to get the successors
    object_type
        Object type to restrict the successors to (optional)

    Returns
    -------
    Set
        Set of successor elements (places or transitions) of the specified object type.
    """
    post = set()
    for a in elem.out_arcs:
        if object_type is None or a.object_type == object_type:
            post.add(a.target)
    return post