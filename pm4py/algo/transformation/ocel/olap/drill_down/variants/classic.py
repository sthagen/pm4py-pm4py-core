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
    TUPLE_FORMAT = "tuple_format"


def _default_format(parent: str, value: str) -> str:
    return "(" + parent + ", " + value + ")"


def apply(ocel: OCEL, parameters: Optional[Dict[Any, Any]] = None) -> OCEL:
    """
    Drill-down: splits a target object type into sub-types based on the
    values of a given object attribute.

    For every object whose type equals ``object_type`` and whose
    ``object_attribute`` value is defined, the type is rewritten to
    ``tuple_format(object_type, value)``. Objects whose attribute value is
    undefined (NaN / empty) keep their original type.

    Parameters
    --------------
    ocel
        Object-centric event log
    parameters
        - Parameters.OBJECT_TYPE: name of the object type to split (required)
        - Parameters.OBJECT_ATTRIBUTE: name of the object attribute column
          to split by (required; must be a column of ``ocel.objects``)
        - Parameters.TUPLE_FORMAT: optional callable
          ``(parent: str, value: str) -> str`` used to build the new type
          name; defaults to ``"(parent, value)"``.

    Notes
    --------------
    This implementation reads attribute values from ``ocel.objects`` only;
    time-varying attribute values in ``ocel.object_changes`` are not used
    to drive the split.

    Returns a new OCEL; the input log is left untouched.
    """
    if parameters is None:
        parameters = {}

    ot = exec_utils.get_param_value(Parameters.OBJECT_TYPE, parameters, None)
    oa = exec_utils.get_param_value(
        Parameters.OBJECT_ATTRIBUTE, parameters, None
    )
    fmt: Callable[[str, str], str] = exec_utils.get_param_value(
        Parameters.TUPLE_FORMAT, parameters, _default_format
    )

    if ot is None:
        raise ValueError("drill_down requires Parameters.OBJECT_TYPE")
    if oa is None:
        raise ValueError("drill_down requires Parameters.OBJECT_ATTRIBUTE")

    result = copy_mod.deepcopy(ocel)
    type_col = result.object_type_column
    oid_col = result.object_id_column

    if ot not in set(result.objects[type_col].unique()):
        raise ValueError(
            "object type %r not found in ocel.objects[%r]" % (ot, type_col)
        )
    if oa not in result.objects.columns:
        raise ValueError(
            "object attribute %r is not a column of ocel.objects" % (oa,)
        )

    attr = result.objects[oa]
    type_match = result.objects[type_col] == ot
    attr_defined = attr.notna() & (attr.astype(str) != "")
    mask = type_match & attr_defined

    if mask.any():
        new_types = [
            fmt(ot, str(v)) for v in result.objects.loc[mask, oa].tolist()
        ]
        result.objects.loc[mask, type_col] = new_types

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
