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
from collections import defaultdict
from typing import Optional, Dict, Any, Tuple, Set
from pm4py.objects.ocel.obj import OCEL
from enum import Enum
from pm4py.util import exec_utils
from pm4py.algo.discovery.ocel.etot.variants import classic


class Variants(Enum):
    CLASSIC = classic


def apply(ocel: OCEL,
          variant=Variants.CLASSIC,
          parameters: Optional[Dict[Any,
                                    Any]] = None) -> Tuple[Set[str],
                                                           Set[str],
                                                           Set[Tuple[str,
                                                                     str]],
                                                           Dict[Tuple[str,
                                                                      str],
                                                                int]]:
    """
    Discovers the ET-OT graph from an OCEL

    Published in: https://publications.rwth-aachen.de/record/1014107

    Parameters
    ---------------
    ocel
        Object-centric event log
    variant
        Variant of the algorithm to be used (available: Variants.CLASSIC)
    parameters
        Variant-specific parameters

    Returns
    ----------------
    activities
        Set of activities
    object_types
        Set of object types
    edges
        Set of edges
    edges_frequency
        Dictionary associating to each edge a frequency
    """
    return exec_utils.get_variant(variant).apply(ocel, parameters)
