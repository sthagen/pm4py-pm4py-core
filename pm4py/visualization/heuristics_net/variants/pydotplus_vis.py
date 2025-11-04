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

import math
import tempfile
from uuid import uuid4
from enum import Enum
from typing import Optional, Dict, Any, Union

from graphviz import Digraph

from pm4py.objects.heuristics_net.obj import HeuristicsNet
from pm4py.util import constants, exec_utils
from pm4py.util.vis_utils import human_readable_stat


class Parameters(Enum):
    FORMAT = "format"
    BGCOLOR = "bgcolor"
    ENABLE_GRAPH_TITLE = "enable_graph_title"
    GRAPH_TITLE = "graph_title"


def get_corr_hex(num):
    """
    Gets correspondence between a number
    and an hexadecimal string

    Parameters
    -------------
    num
        Number

    Returns
    -------------
    hex_string
        Hexadecimal string
    """
    if num < 10:
        return str(int(num))
    elif num < 11:
        return "A"
    elif num < 12:
        return "B"
    elif num < 13:
        return "C"
    elif num < 14:
        return "D"
    elif num < 15:
        return "E"
    elif num < 16:
        return "F"


def transform_to_hex(graycolor):
    """
    Transform color to hexadecimal representation

    Parameters
    -------------
    graycolor
        Gray color (int from 0 to 255)

    Returns
    -------------
    hex_string
        Hexadecimal color
    """
    left0 = graycolor / 16
    right0 = graycolor % 16

    left00 = get_corr_hex(left0)
    right00 = get_corr_hex(right0)

    return "#" + left00 + right00 + left00 + right00 + left00 + right00


def transform_to_hex_2(color):
    """
    Transform color to hexadecimal representation

    Parameters
    -------------
    color
        Gray color (int from 0 to 255)

    Returns
    -------------
    hex_string
        Hexadecimal color
    """
    color = 255 - color
    color2 = 255 - color

    left0 = color / 16
    right0 = color % 16

    left1 = color2 / 16
    right1 = color2 % 16

    left0 = get_corr_hex(left0)
    right0 = get_corr_hex(right0)
    left1 = get_corr_hex(left1)
    right1 = get_corr_hex(right1)

    return "#" + left0 + right0 + left1 + right1 + left1 + right1


def get_graph(
    heu_net: HeuristicsNet,
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> Digraph:
    """
    Gets a representation of an Heuristics Net

    Parameters
    -------------
    heu_net
        Heuristics net
    parameters
        Possible parameters of the algorithm, including:
            - Parameters.FORMAT

    Returns
    ------------
    graph
        Graphviz graph
    """
    if parameters is None:
        parameters = {}

    enable_graph_title = exec_utils.get_param_value(
        Parameters.ENABLE_GRAPH_TITLE,
        parameters,
        constants.DEFAULT_ENABLE_GRAPH_TITLES,
    )
    graph_title = exec_utils.get_param_value(
        Parameters.GRAPH_TITLE, parameters, "Heuristics Net"
    )

    bgcolor = exec_utils.get_param_value(
        Parameters.BGCOLOR, parameters, constants.DEFAULT_BGCOLOR
    )
    image_format = exec_utils.get_param_value(
        Parameters.FORMAT, parameters, "png"
    )

    filename = tempfile.NamedTemporaryFile(suffix=".gv")
    filename.close()

    graph = Digraph(filename=filename.name, strict=True, engine="dot")
    graph.attr(bgcolor=bgcolor)

    if enable_graph_title:
        graph.attr(
            label=graph_title,
            labelloc="top",
            labeljust="center",
            fontsize="20",
        )

    corr_nodes = {}
    corr_nodes_names = {}
    is_frequency = False

    start_end_nodes_set = set()

    for index, sa_list in enumerate(heu_net.start_activities):
        start_end_nodes_set = start_end_nodes_set.union(
            {n for n in sa_list if n in corr_nodes_names}
        )

    for index, ea_list in enumerate(heu_net.end_activities):
        start_end_nodes_set = start_end_nodes_set.union(
            {n for n in ea_list if n in corr_nodes_names}
        )

    for node_name in heu_net.nodes:
        node = heu_net.nodes[node_name]
        if (
            node_name in start_end_nodes_set
            or node.input_connections
            or node.output_connections
        ):
            node_occ = node.node_occ
            graycolor = transform_to_hex_2(
                max(255 - math.log(node_occ) * 9, 0)
            )
            node_id = str(uuid4())
            if node.node_type == "frequency":
                is_frequency = True
                node_label = f"{node_name} ({node_occ})"
            else:
                sojourn = (
                    human_readable_stat(heu_net.sojourn_times[node_name])
                    if node_name in heu_net.sojourn_times
                    else "0s"
                )
                node_label = f"{node_name} ({sojourn})"

            graph.node(
                node_id,
                label=node_label,
                shape="box",
                style="filled",
                fillcolor=node.get_fill_color(graycolor),
                fontcolor=node.get_font_color(),
            )
            corr_nodes[node] = node_id
            corr_nodes_names[node_name] = node_id

    # gets max arc value
    max_arc_value = -1
    for node_name in heu_net.nodes:
        node = heu_net.nodes[node_name]
        for other_node in node.output_connections:
            if other_node in corr_nodes:
                for edge in node.output_connections[other_node]:
                    max_arc_value = max(max_arc_value, edge.repr_value)

    for node_name in heu_net.nodes:
        node = heu_net.nodes[node_name]
        for other_node in node.output_connections:
            if other_node in corr_nodes:
                for edge in node.output_connections[other_node]:
                    this_pen_width = 1.0 + math.log(1 + edge.repr_value) / 11.0
                    repr_value = str(edge.repr_value)
                    edge_kwargs = {
                        "color": edge.get_color(),
                        "fontcolor": edge.get_font_color(),
                        "penwidth": str(edge.get_penwidth(this_pen_width)),
                    }
                    if edge.net_name:
                        if node.node_type == "frequency":
                            label = f"{edge.net_name} ({repr_value})"
                        else:
                            label = (
                                f"{edge.net_name} "
                                f"({human_readable_stat(repr_value)})"
                            )
                    else:
                        if node.node_type == "frequency":
                            label = repr_value
                        else:
                            label = human_readable_stat(repr_value)
                    graph.edge(
                        corr_nodes[node], corr_nodes[other_node], label=label, **edge_kwargs
                    )

    for index, sa_list in enumerate(heu_net.start_activities):
        effective_sa_list = [n for n in sa_list if n in corr_nodes_names]
        if effective_sa_list:
            start_id = f"start_{index}"
            graph.node(
                start_id,
                label="@@S",
                color=heu_net.default_edges_color[index],
                fontsize="8",
                fontcolor="#32CD32",
                fillcolor="#32CD32",
                style="filled",
            )
            for node_name in effective_sa_list:
                sa = corr_nodes_names[node_name]
                if type(heu_net.start_activities[index]) is dict:
                    occ = heu_net.start_activities[index][node_name]
                    if occ >= heu_net.min_dfg_occurrences:
                        if is_frequency:
                            this_pen_width = 1.0 + math.log(1 + occ) / 11.0
                            penwidth = str(this_pen_width)
                            if heu_net.net_name[index]:
                                label = f"{heu_net.net_name[index]} ({occ})"
                            else:
                                label = str(occ)
                            graph.edge(
                                start_id,
                                sa,
                                label=label,
                                color=heu_net.default_edges_color[index],
                                fontcolor=heu_net.default_edges_color[index],
                                penwidth=penwidth,
                            )
                        else:
                            graph.edge(
                                start_id,
                                sa,
                                label=heu_net.net_name[index],
                                color=heu_net.default_edges_color[index],
                                fontcolor=heu_net.default_edges_color[index],
                            )
                else:
                    graph.edge(
                        start_id,
                        sa,
                        label=heu_net.net_name[index],
                        color=heu_net.default_edges_color[index],
                        fontcolor=heu_net.default_edges_color[index],
                    )

    for index, ea_list in enumerate(heu_net.end_activities):
        effective_ea_list = [n for n in ea_list if n in corr_nodes_names]
        if effective_ea_list:
            end_id = f"end_{index}"
            graph.node(
                end_id,
                label="@@E",
                color="#FFA500",
                fillcolor="#FFA500",
                fontcolor="#FFA500",
                fontsize="8",
                style="filled",
            )
            for node_name in effective_ea_list:
                ea = corr_nodes_names[node_name]
                if type(heu_net.end_activities[index]) is dict:
                    occ = heu_net.end_activities[index][node_name]
                    if occ >= heu_net.min_dfg_occurrences:
                        if is_frequency:
                            this_pen_width = 1.0 + math.log(1 + occ) / 11.0
                            penwidth = str(this_pen_width)
                            if heu_net.net_name[index]:
                                label = f"{heu_net.net_name[index]} ({occ})"
                            else:
                                label = str(occ)
                            graph.edge(
                                ea,
                                end_id,
                                label=label,
                                color=heu_net.default_edges_color[index],
                                fontcolor=heu_net.default_edges_color[index],
                                penwidth=penwidth,
                            )
                        else:
                            graph.edge(
                                ea,
                                end_id,
                                label=heu_net.net_name[index],
                                color=heu_net.default_edges_color[index],
                                fontcolor=heu_net.default_edges_color[index],
                            )
                else:
                    graph.edge(
                        ea,
                        end_id,
                        label=heu_net.net_name[index],
                        color=heu_net.default_edges_color[index],
                        fontcolor=heu_net.default_edges_color[index],
                    )

    graph.format = image_format.replace("html", "plain-ext")

    return graph


def apply(
    heu_net: HeuristicsNet,
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> str:
    """
    Gets a representation of an Heuristics Net

    Parameters
    -------------
    heu_net
        Heuristics net
    parameters
        Possible parameters of the algorithm, including:
            - Parameters.FORMAT

    Returns
    ------------
    gviz
        Representation of the Heuristics Net
    """
    if parameters is None:
        parameters = {}


    graph = get_graph(heu_net, parameters=parameters)

    return graph
