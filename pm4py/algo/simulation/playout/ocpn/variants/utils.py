"""
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
"""

from enum import Enum
import pandas as pd
from pm4py.objects.ocel.obj import OCEL
from pm4py.objects.ocel import constants
from pm4py.util import exec_utils


class Parameters(Enum):
    EVENT_ID = constants.PARAM_EVENT_ID
    EVENT_ACTIVITY = constants.PARAM_EVENT_ACTIVITY
    EVENT_TIMESTAMP = constants.PARAM_EVENT_TIMESTAMP
    OBJECT_ID = constants.PARAM_OBJECT_ID
    OBJECT_TYPE = constants.PARAM_OBJECT_TYPE
    OBJECTS_UNIQUE_PER_TRACE = "objects_unique_per_trace"

def feasible_traces_to_ocel(
    feasible_traces_iter, all_transitions, id_to_obj_type, parameters
):
    """
    Converts the feasible traces into an OCEL object.

    Parameters
    ----------
    feasible_traces_iter : iter
        An iterator over feasible traces, where each trace is a tuple of events
    all_transitions : list
        Ordered list of all transitions in the object-centric Petri net
    id_to_obj_type : dict
        Mapping from object IDs to their types
    parameters : dict
        Additional parameters for the conversion

    Returns
    -------
    OCEL
        The resulting OCEL object
    """
    event_id_column = exec_utils.get_param_value(
        Parameters.EVENT_ID, parameters, constants.DEFAULT_EVENT_ID
    )
    object_id_column = exec_utils.get_param_value(
        Parameters.OBJECT_ID, parameters, constants.DEFAULT_OBJECT_ID
    )
    object_type_column = exec_utils.get_param_value(
        Parameters.OBJECT_TYPE, parameters, constants.DEFAULT_OBJECT_TYPE
    )

    event_activity = exec_utils.get_param_value(
        Parameters.EVENT_ACTIVITY, parameters, constants.DEFAULT_EVENT_ACTIVITY
    )
    event_timestamp = exec_utils.get_param_value(
        Parameters.EVENT_TIMESTAMP, parameters, constants.DEFAULT_EVENT_TIMESTAMP
    )
    objects_unique_per_trace = exec_utils.get_param_value(
        Parameters.OBJECTS_UNIQUE_PER_TRACE, parameters, False
    )
    # Convert all found traces to OCEL format

    # Create the OCEL object
    events_list = []
    objects_list = []
    relations_list = []

    all_objects_seen = set()
    event_id_counter = 0
    # assigns to each event an increased timestamp from 1970
    curr_timestamp = 10000000

    if objects_unique_per_trace:
        object_id_counter = 0

    # convert trace to set of events, objects, and relations
    for trace in feasible_traces_iter:
        for event in trace:
            transition_idx, object_ids = event
            transition = all_transitions[transition_idx]

            # Do not add silent transitions to the log
            if transition.label is not None:
                # Create event
                event_id = f"event_{event_id_counter}"
                event_id_counter += 1
                curr_timestamp += 1

                events_list.append(
                    {
                        event_id_column: event_id,
                        event_activity: transition.label,
                        event_timestamp: pd.to_datetime(curr_timestamp, unit="s"),
                    }
                )

                # Create objects and relations
                for obj_id in object_ids:
                    obj_type = id_to_obj_type[obj_id]
                    if objects_unique_per_trace:
                            obj_id = f"{obj_id}_{object_id_counter}"

                    # Add object
                    if obj_id not in all_objects_seen:
                        all_objects_seen.add(obj_id)
                        objects_list.append(
                            {object_id_column: obj_id, object_type_column: obj_type}
                        )

                    # Add relation
                    relations_list.append(
                        {
                            event_id_column: event_id,
                            event_activity: transition.label,
                            event_timestamp: pd.to_datetime(curr_timestamp, unit="s"),
                            object_id_column: obj_id,
                            object_type_column: obj_type,
                        }
                    )
        if objects_unique_per_trace:
            object_id_counter += 1

    # Convert to dfs
    events_df = pd.DataFrame(events_list)
    objects_df = pd.DataFrame(objects_list)
    relations_df = pd.DataFrame(relations_list)

    # Create the OCEL object
    ocel = OCEL(
        events=events_df,
        objects=objects_df,
        relations=relations_df,
        parameters=parameters,
    )

    return ocel