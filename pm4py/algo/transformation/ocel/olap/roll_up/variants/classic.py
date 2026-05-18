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
    OBJECT_TYPE = "object_type"
    OBJECT_ATTRIBUTE = "object_attribute"
    TUPLE_MATCHER = "tuple_matcher"


def _default_matcher(type_value: Any, parent: str) -> bool:
    """Recognizes the default ``"(parent, value)"`` tuple encoding."""
    if not isinstance(type_value, str):
        return False
    if type_value == parent:
        return False
    return type_value.startswith("(" + parent + ", ") and type_value.endswith(
        ")"
    )


def apply(ocel: OCEL, parameters: Optional[Dict[Any, Any]] = None) -> OCEL:
    """
    Roll-up: the inverse of drill-down. Collapses tuple-style sub-types of
    a given parent object type back to the parent type.

    Parameters
    --------------
    ocel
        Object-centric event log
    parameters
        - Parameters.OBJECT_TYPE: name of the parent object type to merge
          back to (required)
        - Parameters.OBJECT_ATTRIBUTE: optional, accepted for API symmetry
          with drill_down; if provided, must be a column of
          ``ocel.objects``. Not semantically required because the tuple
          type value already encodes the split.
        - Parameters.TUPLE_MATCHER: optional callable
          ``(type_value, parent) -> bool`` deciding whether ``type_value``
          is a sub-type of ``parent``. Default matches the
          ``"(parent, value)"`` encoding produced by drill_down.

    Returns a new OCEL; the input log is left untouched.
    """
    if parameters is None:
        parameters = {}

    ot = exec_utils.get_param_value(Parameters.OBJECT_TYPE, parameters, None)
    oa = exec_utils.get_param_value(
        Parameters.OBJECT_ATTRIBUTE, parameters, None
    )
    matcher: Callable[[Any, str], bool] = exec_utils.get_param_value(
        Parameters.TUPLE_MATCHER, parameters, _default_matcher
    )

    if ot is None:
        raise ValueError("roll_up requires Parameters.OBJECT_TYPE")

    result = copy_mod.deepcopy(ocel)
    type_col = result.object_type_column
    oid_col = result.object_id_column

    if oa is not None and oa not in result.objects.columns:
        raise ValueError(
            "object attribute %r is not a column of ocel.objects" % (oa,)
        )

    mask = result.objects[type_col].map(lambda t: matcher(t, ot))

    if mask.any():
        result.objects.loc[mask, type_col] = ot

        oid_to_type = dict(
            zip(result.objects[oid_col], result.objects[type_col])
        )
        result.relations[type_col] = (
            result.relations[oid_col]
            .map(oid_to_type)
            .fillna(result.relations[type_col])
        )

        if (
            type_col in result.object_changes.columns
            and len(result.object_changes) > 0
        ):
            result.object_changes[type_col] = (
                result.object_changes[oid_col]
                .map(oid_to_type)
                .fillna(result.object_changes[type_col])
            )

    return result
