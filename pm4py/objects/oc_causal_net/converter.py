'''
    PM4Py – A Process Mining Library for Python
Copyright (C) 2024 Process Intelligence Solutions UG (haftungsbeschränkt)

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
from pm4py.objects.oc_causal_net.variants import to_ocpn
from pm4py.util import exec_utils
from enum import Enum

class Variants(Enum):
    TO_OCPN = to_ocpn
    
def apply(oc_causal_net, parameters=None, variant=Variants.TO_OCPN):
    """
    Method for converting from Object-centric Causal Net Object-centric Petri Net

    Parameters
    -----------
    oc_causal_net
        Object-centric Causal net
    parameters
        Parameters of the algorithm
    variant
        Chosen variant of the algorithm:
            - Variants.TO_OCPN

    Returns
    -----------
    OCPetriNet
        Object-centric Petri net converted from the Object-centric Causal Net
    """
    return exec_utils.get_variant(variant).apply(oc_causal_net, parameters=parameters)