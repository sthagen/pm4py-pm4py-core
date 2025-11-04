'''
    PM4Py â€“ A Process Mining Library for Python
Copyright (C) 2024 Process Intelligence Solutions UG (haftungsbeschrÃ¤nkt)

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
from pm4py.algo.discovery.ocel.otg.variants import classic
from enum import Enum
from pm4py.util import exec_utils
from pm4py.objects.ocel.obj import OCEL
from typing import Optional, Dict, Any, Tuple, Set


class Variants(Enum):
    CLASSIC = classic


def apply(ocel: OCEL,
          variant=Variants.CLASSIC,
          parameters: Optional[Dict[Any,
                                    Any]] = None) -> Tuple[Set[str],
                                                           Dict[Tuple[str,
                                                                str,
                                                                str],
                                                                int]]:
    """
    Discovers an OTG (object-type-graph) from the provided OCEL

    Published in: https://publications.rwth-aachen.de/record/1014107

    Parameters
    -----------------
    ocel
        OCEL
    variant
        Variant to be used (available: Variants.CLASSIC)
    parameters
        Variant-specific parameters

    Returns
    -----------------
    otg
        Object-type-graph (tuple; the first element is the set of object types, the second element is the OTG)
    """
    if parameters is None:
        parameters = {}

    return exec_utils.get_variant(variant).apply(ocel, parameters)
