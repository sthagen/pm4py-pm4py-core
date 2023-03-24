'''
    This file is part of PM4Py (More Info: https://pm4py.fit.fraunhofer.de).

    PM4Py is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    PM4Py is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with PM4Py.  If not, see <https://www.gnu.org/licenses/>.
'''
from enum import Enum
from typing import Optional, Dict, Any

from pm4py.objects.ocel import constants
from pm4py.objects.ocel.obj import OCEL
from pm4py.util import exec_utils
import pandas as pd


class Parameters(Enum):
    EVENT_ID = constants.PARAM_EVENT_ID
    EVENT_ACTIVITY = constants.PARAM_EVENT_ACTIVITY
    EVENT_TIMESTAMP = constants.PARAM_EVENT_TIMESTAMP
    OBJECT_ID = constants.PARAM_OBJECT_ID
    OBJECT_TYPE = constants.PARAM_OBJECT_TYPE
    INTERNAL_INDEX = constants.PARAM_INTERNAL_INDEX
    QUALIFIER = constants.PARAM_QUALIFIER
    CHANGED_FIELD = constants.PARAM_CHNGD_FIELD


def apply(file_path: str, parameters: Optional[Dict[Any, Any]] = None):
    if parameters is None:
        parameters = {}

    import sqlite3

    event_id = exec_utils.get_param_value(Parameters.EVENT_ID, parameters, constants.DEFAULT_EVENT_ID)
    event_activity = exec_utils.get_param_value(Parameters.EVENT_ACTIVITY, parameters, constants.DEFAULT_EVENT_ACTIVITY)
    event_timestamp = exec_utils.get_param_value(Parameters.EVENT_TIMESTAMP, parameters,
                                                 constants.DEFAULT_EVENT_TIMESTAMP)
    object_id = exec_utils.get_param_value(Parameters.OBJECT_ID, parameters, constants.DEFAULT_OBJECT_ID)
    object_type = exec_utils.get_param_value(Parameters.OBJECT_TYPE, parameters, constants.DEFAULT_OBJECT_TYPE)
    internal_index = exec_utils.get_param_value(Parameters.INTERNAL_INDEX, parameters, constants.DEFAULT_INTERNAL_INDEX)
    qualifier_field = exec_utils.get_param_value(Parameters.QUALIFIER, parameters, constants.DEFAULT_QUALIFIER)
    changed_field = exec_utils.get_param_value(Parameters.CHANGED_FIELD, parameters, constants.DEFAULT_CHNGD_FIELD)

    conn = sqlite3.connect(file_path)

    EVENTS = pd.read_sql("SELECT * FROM event", conn)
    OBJECTS = pd.read_sql("SELECT * FROM object", conn)

    etypes = sorted(list(EVENTS["ocel_type"].unique()))
    otypes = sorted(list(OBJECTS["ocel_type"].unique()))

    EVENTS = EVENTS.to_dict("records")
    OBJECTS = OBJECTS.to_dict("records")
    events_id_type = {x["ocel_id"]: x["ocel_type"] for x in EVENTS}
    objects_id_type = {x["ocel_id"]: x["ocel_type"] for x in OBJECTS}

    EVENT_CORR_TYPE = pd.read_sql("SELECT * FROM event_map_type", conn)
    OBJECT_CORR_TYPE = pd.read_sql("SELECT * FROM object_map_type", conn)
    EVENT_CORR_TYPE = EVENT_CORR_TYPE.to_dict("records")
    OBJECT_CORR_TYPE = OBJECT_CORR_TYPE.to_dict("records")

    events_type_map = {x["ocel_type"]: x["ocel_type_map"] for x in EVENT_CORR_TYPE}
    objects_type_map = {x["ocel_type"]: x["ocel_type_map"] for x in OBJECT_CORR_TYPE}

    event_types_coll = []
    object_types_coll = []

    for act in etypes:
        act_red = events_type_map[act]
        df = pd.read_sql("SELECT * FROM event_"+act_red, conn)
        df = df.rename(columns={"ocel_id": event_id, "ocel_time": event_timestamp})
        event_types_coll.append(df)

    for ot in otypes:
        ot_red = objects_type_map[ot]
        df = pd.read_sql("SELECT * FROM object_"+ot_red, conn)
        df = df.rename(columns={"ocel_id": object_id, "ocel_time": event_timestamp})
        object_types_coll.append(df)

    event_types_coll = pd.concat(event_types_coll)
    event_types_coll[event_activity] = event_types_coll[event_id].map(events_id_type)
    event_types_coll[event_timestamp] = pd.to_datetime(event_types_coll[event_timestamp])
    object_types_coll = pd.concat(object_types_coll)
    object_types_coll[object_type] = object_types_coll[object_id].map(objects_id_type)
    object_types_coll = object_types_coll.rename(columns={"ocel_changed_field": changed_field})

    events_timestamp = event_types_coll[[event_id, event_timestamp]].to_dict('records')
    events_timestamp = {x[event_id]: x[event_timestamp] for x in events_timestamp}
    if changed_field in object_types_coll:
        objects = object_types_coll[object_types_coll[changed_field].isna()]
        object_changes = object_types_coll[~object_types_coll[changed_field].isna()]
        if len(object_changes) == 0:
            object_changes = None
        del objects[changed_field]
    else:
        objects = object_types_coll
        object_changes = None

    del objects[event_timestamp]

    E2O = pd.read_sql("SELECT * FROM event_object", conn)
    E2O = E2O.rename(columns={"ocel_event_id": event_id, "ocel_object_id": object_id, "ocel_qualifier": qualifier_field})
    E2O[event_activity] = E2O[event_id].map(events_id_type)
    E2O[event_timestamp] = E2O[event_id].map(events_timestamp)
    E2O[object_type] = E2O[object_id].map(objects_id_type)

    O2O = pd.read_sql("SELECT * FROM object_object", conn)
    O2O = O2O.rename(columns={"ocel_source_id": object_id, "ocel_target_id": object_id+"_2", "ocel_qualifier": qualifier_field})
    if len(O2O) == 0:
        O2O = None

    conn.close()

    event_types_coll[internal_index] = event_types_coll.index
    E2O[internal_index] = E2O.index

    event_types_coll = event_types_coll.sort_values([event_timestamp, internal_index])
    E2O = E2O.sort_values([event_timestamp, internal_index])

    del event_types_coll[internal_index]
    del E2O[internal_index]

    if object_changes is not None:
        object_changes[event_timestamp] = pd.to_datetime(object_changes[event_timestamp])
        object_changes[internal_index] = object_changes.index
        object_changes = object_changes.sort_values([event_timestamp, internal_index])
        del object_changes[internal_index]

    ocel = OCEL(events=event_types_coll, objects=objects, relations=E2O, object_changes=object_changes, o2o=O2O, parameters=parameters)

    return ocel
