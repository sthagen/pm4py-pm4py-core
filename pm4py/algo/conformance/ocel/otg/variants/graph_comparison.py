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
from enum import Enum
from pm4py.util import exec_utils
from pm4py.objects.ocel.obj import OCEL
from typing import Optional, Dict, Any, Union, Tuple, Set


class Parameters(Enum):
    THETA = "theta"
    ALPHA = "alpha"
    BETA = "beta"
    GAMMA = "gamma"


def apply(real: Union[OCEL,
                      Tuple[Set[str],
                            Dict[Tuple[str,
                                       str,
                                       str],
                                 int]]],
          normative: Tuple[Set[str],
                           Dict[Tuple[str,
                                str,
                                str],
                                int]],
          parameters: Optional[Dict[Any,
                                    Any]] = None) -> Dict[str,
                                                          Any]:
    """
    Applies OTG-based conformance checking between a 'real' object (OCEL or OTG) and a 'normative' OTG.

    Published in: https://publications.rwth-aachen.de/record/1014107

    Parameters
    -----------------
    real
        Real object (OCEL or OTG)
    normative
        Normative OTG
    parameters
        Variant-specific parameters:
        - Parameters.THETA
        - Parameters.ALPHA
        - Parameters.BETA
        - Parameters.GAMMA

    Returns
    -----------------
    conf_diagn
        Diagnostics dictionary
    """
    if parameters is None:
        parameters = {}

    theta = exec_utils.get_param_value(Parameters.THETA, parameters, None)
    alpha = exec_utils.get_param_value(Parameters.ALPHA, parameters, 1)
    beta = exec_utils.get_param_value(Parameters.BETA, parameters, 1)
    gamma = exec_utils.get_param_value(Parameters.GAMMA, parameters, 1)

    if isinstance(real, OCEL):
        from pm4py.algo.discovery.ocel.otg import algorithm as otg_discovery
        real = otg_discovery.apply(real, parameters=parameters)

    return conformance_checking_multigraph(
        real,
        normative,
        theta=theta,
        alpha=alpha,
        beta=beta,
        gamma=gamma)


def conformance_checking_multigraph(
        discovered_otg,
        normative_otg,
        theta=None,
        alpha=1,
        beta=1,
        gamma=1):
    object_types_L, edges_L = discovered_otg
    object_types_M, edges_M = normative_otg

    # Default thresholds for each relationship type if not provided
    if theta is None:
        theta = {
            'object_interaction': 0.2,
            'object_descendants': 0.2,
            'object_inheritance': 0.2,
            'object_cobirth': 0.2,
            'object_codeath': 0.2
        }

    # Object Type Conformance
    missing_object_types = object_types_M - object_types_L
    additional_object_types = object_types_L - object_types_M

    # Edge Conformance
    missing_edges = set(edges_M.keys()) - set(edges_L.keys())
    additional_edges = set(edges_L.keys()) - set(edges_M.keys())

    # Edge Frequency Conformance
    non_conforming_edges = {}
    for edge in set(edges_M.keys()) & set(edges_L.keys()):
        f_M = edges_M[edge]
        f_L = edges_L[edge]
        sigma = edge[1]  # Relationship type
        delta = abs(f_L - f_M) / f_M if f_M != 0 else float('inf')
        if delta > theta.get(sigma, 0.2):
            non_conforming_edges[edge] = delta

    # Fitness Value Calculation
    total_object_types = len(object_types_M)
    total_edges = len(edges_M)
    total_edge_checks = len(edges_M)
    N = alpha * total_object_types + beta * total_edges + gamma * total_edge_checks
    fitness = 1 - (
        alpha * len(missing_object_types) +
        beta * len(missing_edges) +
        gamma * len(non_conforming_edges)
    ) / N

    # Prepare the result
    result = {
        'missing_object_types': missing_object_types,
        'additional_object_types': additional_object_types,
        'missing_edges': missing_edges,
        'additional_edges': additional_edges,
        'non_conforming_edges': non_conforming_edges,
        'fitness': fitness
    }
    return result
