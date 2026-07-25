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
import base64
import os
import subprocess
import sys
from typing import Optional, Dict


MAX_EDGE_PENWIDTH_GRAPHVIZ = 2.6
MIN_EDGE_PENWIDTH_GRAPHVIZ = 1.0


def get_business_hour_slots(parameters, performance_dfg=None):
    """Return the schedule to use for duration labels, if configured.

    Explicit visualization parameters take precedence over metadata retained
    by a discovered performance DFG.
    """
    from pm4py.util import constants, exec_utils

    missing = object()
    business_hours = exec_utils.get_param_value(
        "business_hours", parameters, missing
    )
    business_hour_slots = exec_utils.get_param_value(
        "business_hour_slots", parameters, missing
    )
    if business_hours is not missing and not business_hours:
        return None
    if business_hour_slots is not missing and business_hour_slots is not None:
        return business_hour_slots
    if performance_dfg is not None:
        discovered_slots = getattr(
            performance_dfg, "business_hour_slots", None
        )
        if discovered_slots is not None:
            return discovered_slots
    if business_hours is not missing and business_hours:
        return constants.DEFAULT_BUSINESS_HOUR_SLOTS
    return None


def human_readable_stat(
    timedelta,
    stat_locale: Optional[Dict[str, str]] = None,
    business_hour_slots=None,
) -> str:
    """
    Transform a timedelta into a human readable string

    Parameters
    ----------
    timedelta
        Timedelta
    stat_locale
        Labels used for the displayed time units
    business_hour_slots
        Optional weekly business-hour schedule. When provided, days, months,
        and years are expressed in configured working days instead of
        24-hour calendar days.

    Returns
    ----------
    string
        Human readable string
    """
    if stat_locale is None:
        stat_locale = {}

    seconds_per_day = 86400.0
    if business_hour_slots is not None:
        from pm4py.util.business_hours import get_business_day_seconds

        seconds_per_day = get_business_day_seconds(business_hour_slots)

    c = int(float(timedelta))
    years = int(c // (seconds_per_day * 360))
    months = int(c // (seconds_per_day * 30))
    days = int(c // seconds_per_day)
    hours = c // 3600
    minutes = c // 60 % 60
    seconds = c % 60
    if years > 0:
        return str(years) + stat_locale.get("year", "Y")
    elif months > 0:
        return str(months) + stat_locale.get("month", "MO")
    elif days > 0:
        return str(days) + stat_locale.get("day", "D")
    elif hours > 0:
        return str(hours) + stat_locale.get("hour", "h")
    elif minutes > 0:
        return str(minutes) + stat_locale.get("minute", "m")
    elif seconds > 0:
        return str(seconds) + stat_locale.get("second", "s")
    else:
        c = int(float(timedelta) * 1000)
        if c > 0:
            return str(c) + stat_locale.get("millisecond", "ms")
        else:
            return str(int(float(timedelta) * 10**9)) + stat_locale.get(
                "nanosecond", "ns"
            )


def get_arc_penwidth(arc_measure, min_arc_measure, max_arc_measure):
    """
    Calculate arc width given the current arc measure value, the minimum arc measure value and the
    maximum arc measure value

    Parameters
    -----------
    arc_measure
        Current arc measure value
    min_arc_measure
        Minimum measure value among all arcs
    max_arc_measure
        Maximum measure value among all arcs

    Returns
    -----------
    penwidth
        Current arc width in the graph
    """
    return MIN_EDGE_PENWIDTH_GRAPHVIZ + (
        MAX_EDGE_PENWIDTH_GRAPHVIZ - MIN_EDGE_PENWIDTH_GRAPHVIZ
    ) * (arc_measure - min_arc_measure) / (
        max_arc_measure - min_arc_measure + 0.00001
    )


def get_trans_freq_color(trans_count, min_trans_count, max_trans_count):
    """
    Gets transition frequency color

    Parameters
    ----------
    trans_count
        Current transition count
    min_trans_count
        Minimum transition count
    max_trans_count
        Maximum transition count

    Returns
    ----------
    color
        Frequency color for visible transition
    """
    trans_base_color = int(
        255
        - 100
        * (trans_count - min_trans_count)
        / (max_trans_count - min_trans_count + 0.00001)
    )
    trans_base_color_hex = str(hex(trans_base_color))[2:].upper()
    return "#" + trans_base_color_hex + trans_base_color_hex + "FF"


def get_base64_from_gviz(gviz):
    """
    Get base 64 from string content of the file

    Parameters
    -----------
    gviz
        Graphviz diagram

    Returns
    -----------
    base64
        Base64 string
    """
    render = gviz.render(view=False)
    with open(render, "rb") as f:
        return base64.b64encode(f.read())


def get_base64_from_file(temp_file):
    """
    Get base 64 from string content of the file

    Parameters
    -----------
    temp_file
        Temporary file path

    Returns
    -----------
    base64
        Base64 string
    """
    with open(temp_file, "rb") as f:
        return base64.b64encode(f.read())


def check_visualization_inside_jupyter():
    """
    Checks if the visualization of the model is performed
    inside a Jupyter notebook
    """
    try:
        shell = get_ipython().__class__.__name__
        if shell == "ZMQInteractiveShell" or shell == "Shell":
            return True
        else:
            return False
    except NameError:
        return False


def view_image_in_jupyter(file_name):
    """
    Visualizes a picture inside the Jupyter notebooks

    Parameters
    -------------
    file_name
        Name of the file
    """
    from IPython.display import Image

    image = Image(file_name)
    from IPython.display import display

    return display(image)


def open_opsystem_image_viewer(file_name):
    """
    Visualizes a picture using the image viewer of the operating system

    Parameters
    -------------
    file_name
        Name of the file
    """
    if sys.platform.startswith("darwin"):
        subprocess.call(("open", file_name))
    elif os.name == "nt":  # For Windows
        os.startfile(file_name)
    elif os.name == "posix":  # For Linux, Mac, etc.
        subprocess.call(("xdg-open", file_name))


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


def value_to_color(val, min_value, max_value):
    # Normalize values to the range [0, 1]
    val = (val - min_value) / (max_value - min_value + 0.000001)

    # Function to interpolate between two colors
    def interpolate_color(val, color1, color2):
        return tuple(
            int(color1[i] + (color2[i] - color1[i]) * val) for i in range(3)
        )

    # Blue to red color gradient
    blue = (0, 0, 255)  # RGB for blue
    red = (255, 0, 0)  # RGB for red

    # Map normalized values to colors
    color = interpolate_color(val, blue, red)

    # Convert RGB colors to hexadecimal format
    def rgb_to_hex(rgb):
        return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])

    hex_color = rgb_to_hex(color)

    return hex_color
