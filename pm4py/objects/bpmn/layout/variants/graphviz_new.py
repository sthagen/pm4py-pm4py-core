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
from pm4py.objects.bpmn.obj import BPMN
from typing import Optional, Dict, Any, Tuple, List
from copy import copy
import tempfile


def _get_node_center(layout, node) -> Tuple[float, float]:
    """Get the center point of a node."""
    node_layout = layout.get(node)
    x = node_layout.get_x() + node_layout.get_width() / 2
    y = node_layout.get_y() + node_layout.get_height() / 2
    return (x, y)


def _get_node_boundary_point(layout, node, target_point: Tuple[float, float]) -> Tuple[float, float]:
    """
    Calculate the intersection point on the node boundary
    towards a target point.
    """
    node_layout = layout.get(node)
    x = node_layout.get_x()
    y = node_layout.get_y()
    w = node_layout.get_width()
    h = node_layout.get_height()

    cx, cy = x + w / 2, y + h / 2
    tx, ty = target_point

    dx = tx - cx
    dy = ty - cy

    if dx == 0 and dy == 0:
        return (cx, y)  # Default to top edge

    # Calculate intersection with rectangle boundary
    if dx == 0:
        return (cx, y if dy < 0 else y + h)
    if dy == 0:
        return (x if dx < 0 else x + w, cy)

    # Check intersection with each edge
    scale_x = (w / 2) / abs(dx)
    scale_y = (h / 2) / abs(dy)
    scale = min(scale_x, scale_y)

    return (cx + dx * scale, cy + dy * scale)


def apply(
        bpmn_graph: BPMN, parameters: Optional[Dict[Any, Any]] = None
) -> BPMN:
    """
    Layouts the BPMN graph using node positioning and edge waypoints from Graphviz SVG.
    Ensures edges connect properly to node boundaries.
    """
    if parameters is None:
        parameters = {}

    from pm4py.visualization.bpmn.variants import classic as bpmn_visualizer
    from pm4py.visualization.common import svg_pos_parser

    layout = bpmn_graph.get_layout()

    filename_svg = tempfile.NamedTemporaryFile(suffix=".svg", delete=False)
    filename_svg.close()

    vis_parameters = copy(parameters)
    vis_parameters["format"] = "svg"
    vis_parameters["include_name_in_events"] = False
    vis_parameters["endpoints_shape"] = "box"

    gviz = bpmn_visualizer.apply(bpmn_graph, parameters=vis_parameters)
    bpmn_visualizer.save(gviz, filename_svg.name)

    nodes_p, edges_p = svg_pos_parser.apply(filename_svg.name)

    # First pass: layout all nodes
    for node in list(bpmn_graph.get_nodes()):
        node_id = str(id(node))
        if node_id in nodes_p:
            node_info = nodes_p[node_id]
            if node_info["polygon"] is not None:
                min_x = min(p[0] for p in node_info["polygon"])
                max_x = max(p[0] for p in node_info["polygon"])
                min_y = min(p[1] for p in node_info["polygon"])
                max_y = max(p[1] for p in node_info["polygon"])

                layout.get(node).set_width(max_x - min_x)
                layout.get(node).set_height(max_y - min_y)
                layout.get(node).set_x(min_x)
                layout.get(node).set_y(min_y)

    # Second pass: layout edges with proper connection points
    for flow in list(bpmn_graph.get_flows()):
        flow_id = (str(id(flow.source)), str(id(flow.target)))
        if flow_id in edges_p:
            flow_info = edges_p[flow_id]
            if flow_info["waypoints"] is not None and len(flow_info["waypoints"]) >= 2:
                flow.del_waypoints()

                waypoints = list(flow_info["waypoints"])

                # Adjust start point to source node boundary
                if len(waypoints) > 1:
                    start_boundary = _get_node_boundary_point(layout, flow.source, waypoints[1])
                    waypoints[0] = start_boundary

                # Adjust end point to target node boundary
                if len(waypoints) > 1:
                    end_boundary = _get_node_boundary_point(layout, flow.target, waypoints[-2])
                    waypoints[-1] = end_boundary

                for wayp in waypoints:
                    flow.add_waypoint(wayp)

    return bpmn_graph
