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
from enum import Enum
from typing import Any, Dict, Optional

from pm4py.algo.transformation.ocel.olap.drill_down.variants import classic
from pm4py.objects.ocel.obj import OCEL
from pm4py.util import exec_utils


class Variants(Enum):
    CLASSIC = classic


def apply(
    ocel: OCEL,
    variant=Variants.CLASSIC,
    parameters: Optional[Dict[Any, Any]] = None,
) -> OCEL:
    """
    Applies the drill-down OLAP operation on an object-centric event log,
    splitting the target object type into tuple-style sub-types based on
    the values of a given object attribute.

    Reference: Khayatbashi, Miri, Jalali. "Advancing Object-Centric Process
    Mining with Multi-Dimensional Data Operations." CAiSE Forum 2025
    (arXiv:2412.00393).

    Parameters
    --------------
    ocel
        Object-centric event log
    variant
        Variant of the algorithm to be used, possible values:
        - Variants.CLASSIC
    parameters
        Variant-specific parameters

    Returns
    --------------
    new_ocel
        A new object-centric event log with the drilled-down object type.
    """
    if parameters is None:
        parameters = {}

    return exec_utils.get_variant(variant).apply(ocel, parameters=parameters)
