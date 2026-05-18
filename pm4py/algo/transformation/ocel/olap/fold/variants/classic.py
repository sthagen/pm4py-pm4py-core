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
from typing import Any, Callable, Dict, Optional

from pm4py.objects.ocel.obj import OCEL
from pm4py.util import exec_utils


class Parameters(Enum):
    EVENT_TYPE = "event_type"
    OBJECT_TYPE = "object_type"
    TUPLE_FORMAT = "tuple_format"


def _default_format(parent: str, value: str) -> str:
    return "(" + parent + ", " + value + ")"


def apply(ocel: OCEL, parameters: Optional[Dict[Any, Any]] = None) -> OCEL:
    """
    Fold: the inverse of unfold. Replaces the unfolded activity
    ``tuple_format(event_type, object_type)`` back with ``event_type`` in
    both ``ocel.events`` and ``ocel.relations``.

    Parameters
    --------------
    ocel
        Object-centric event log
    parameters
        - Parameters.EVENT_TYPE: the parent event type to merge back to
          (required)
        - Parameters.OBJECT_TYPE: the object type used during the matching
          unfold (required)
        - Parameters.TUPLE_FORMAT: optional callable matching unfold's
          encoding; default ``"(event_type, object_type)"``.

    Returns a new OCEL; the input log is left untouched.
    """
    if parameters is None:
        parameters = {}

    et = exec_utils.get_param_value(Parameters.EVENT_TYPE, parameters, None)
    ot = exec_utils.get_param_value(Parameters.OBJECT_TYPE, parameters, None)
    fmt: Callable[[str, str], str] = exec_utils.get_param_value(
        Parameters.TUPLE_FORMAT, parameters, _default_format
    )

    if et is None:
        raise ValueError("fold requires Parameters.EVENT_TYPE")
    if ot is None:
        raise ValueError("fold requires Parameters.OBJECT_TYPE")

    result = copy_mod.deepcopy(ocel)
    act_col = result.event_activity

    folded_act = fmt(et, ot)

    ev_mask = result.events[act_col] == folded_act
    if ev_mask.any():
        result.events.loc[ev_mask, act_col] = et
    rel_mask = result.relations[act_col] == folded_act
    if rel_mask.any():
        result.relations.loc[rel_mask, act_col] = et

    return result
