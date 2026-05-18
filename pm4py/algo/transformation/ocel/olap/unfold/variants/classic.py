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
import copy as copy_mod
from enum import Enum
from typing import Any, Callable, Dict, Iterable, Optional

from pm4py.objects.ocel.obj import OCEL
from pm4py.util import exec_utils


class Parameters(Enum):
    EVENT_TYPE = "event_type"
    OBJECT_TYPE = "object_type"
    QUALIFIERS = "qualifiers"
    TUPLE_FORMAT = "tuple_format"


def _default_format(parent: str, value: str) -> str:
    return "(" + parent + ", " + value + ")"


def apply(ocel: OCEL, parameters: Optional[Dict[Any, Any]] = None) -> OCEL:
    """
    Unfold: splits an event type into a tuple-style sub-type keyed by a
    related object type.

    For every event of type ``event_type`` that has at least one E2O
    relation to an object of type ``object_type`` (optionally restricted
    to qualifiers in ``qualifiers``), the event's activity is rewritten
    to ``tuple_format(event_type, object_type)`` in both ``ocel.events``
    and ``ocel.relations``.

    Parameters
    --------------
    ocel
        Object-centric event log
    parameters
        - Parameters.EVENT_TYPE: the event type/activity to unfold (required)
        - Parameters.OBJECT_TYPE: the related object type to unfold over
          (required)
        - Parameters.QUALIFIERS: optional iterable of qualifier values;
          when provided, only E2O relations whose qualifier is in this
          set contribute to the unfolding. Default: all qualifiers.
        - Parameters.TUPLE_FORMAT: optional callable
          ``(event_type, object_type) -> str`` producing the new activity
          name. Must match fold's format to be reversible. Default:
          ``"(event_type, object_type)"``.

    Returns a new OCEL; the input log is left untouched.
    """
    if parameters is None:
        parameters = {}

    et = exec_utils.get_param_value(Parameters.EVENT_TYPE, parameters, None)
    ot = exec_utils.get_param_value(Parameters.OBJECT_TYPE, parameters, None)
    qualifiers: Optional[Iterable[Any]] = exec_utils.get_param_value(
        Parameters.QUALIFIERS, parameters, None
    )
    fmt: Callable[[str, str], str] = exec_utils.get_param_value(
        Parameters.TUPLE_FORMAT, parameters, _default_format
    )

    if et is None:
        raise ValueError("unfold requires Parameters.EVENT_TYPE")
    if ot is None:
        raise ValueError("unfold requires Parameters.OBJECT_TYPE")

    result = copy_mod.deepcopy(ocel)
    eid_col = result.event_id_column
    act_col = result.event_activity
    type_col = result.object_type_column
    qual_col = result.qualifier

    rel = result.relations
    mask = (rel[act_col] == et) & (rel[type_col] == ot)
    if qualifiers is not None:
        mask = mask & rel[qual_col].isin(list(qualifiers))

    matched_eids = set(rel.loc[mask, eid_col].unique())

    if matched_eids:
        new_act = fmt(et, ot)
        ev_mask = result.events[eid_col].isin(matched_eids)
        result.events.loc[ev_mask, act_col] = new_act
        rel_mask = result.relations[eid_col].isin(matched_eids)
        result.relations.loc[rel_mask, act_col] = new_act

    return result
