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
from pm4py.algo.conformance.ocel.ocdfg.variants import graph_comparison
from pm4py.util import exec_utils
from typing import Optional, Dict, Any, Union
from enum import Enum
from pm4py.objects.ocel.obj import OCEL


class Variants(Enum):
    GRAPH_COMPARISON = graph_comparison


def apply(real: Union[OCEL,
                      Dict[str,
                           Any]],
          normative: Dict[str,
                          Any],
          variant=Variants.GRAPH_COMPARISON,
          parameters: Optional[Dict[Any,
                                    Any]] = None) -> Dict[str,
                                                          Any]:
    """
    Applies object-centric conformance checking between the given real object (object-centric event log or DFG)
    and a normative OC-DFG.

    Published in: https://publications.rwth-aachen.de/record/1014107

    Parameters
    -----------------
    real
        Real entity (OCEL or OC-DFG)
    normative
        Normative entity (OC-DFG)
    variant
        Variant of the algorithm to be used (default: Variants.GRAPH_COMPARISON)
    parameters
        Variant-specific parameters

    Returns
    -----------------
    conf_diagn_dict
        Dictionary with conformance diagnostics
    """
    return exec_utils.get_variant(variant).apply(real, normative, parameters)
