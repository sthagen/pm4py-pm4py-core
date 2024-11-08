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
from graphviz import Digraph
from enum import Enum
from pm4py.util import exec_utils
from pm4py.visualization.ocel.ocdfg.variants import classic
from typing import Optional, Dict, Any
from pm4py.visualization.common import gview
from pm4py.visualization.common import save as gsave


class Variants(Enum):
    CLASSIC = classic


def apply(ocdfg: Dict[str, Any], variant=Variants.CLASSIC, parameters: Optional[Dict[Any, Any]] = None) -> Digraph:
    """
    Visualizes an OC-DFG using one of the provided visualizations.

    Parameters
    ----------------
    ocdfg
        Object-centric directly-follows graph
    variant
        Available variants. Possible values:
        - Variants.CLASSIC
    parameters
        Variant-specific parameters

    Returns
    ----------------
    viz
        Graphviz DiGraph
    """
    return exec_utils.get_variant(variant).apply(ocdfg, parameters)


def save(gviz: Digraph, output_file_path: str, parameters=None):
    """
    Save the diagram

    Parameters
    -----------
    gviz
        GraphViz diagram
    output_file_path
        Path where the GraphViz output should be saved
    """
    gsave.save(gviz, output_file_path, parameters=parameters)
    return ""


def view(gviz: Digraph, parameters=None):
    """
    View the diagram

    Parameters
    -----------
    gviz
        GraphViz diagram
    """
    return gview.view(gviz, parameters=parameters)


def matplotlib_view(gviz: Digraph, parameters=None):
    """
    Views the diagram using Matplotlib

    Parameters
    ---------------
    gviz
        Graphviz
    """

    return gview.matplotlib_view(gviz, parameters=parameters)
