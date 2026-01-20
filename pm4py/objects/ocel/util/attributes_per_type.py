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
from pm4py.objects.ocel.obj import OCEL
from typing import Optional, Dict, Any
from pm4py.objects.ocel import constants
from enum import Enum
from pm4py.util import exec_utils
import datetime as dt
import numpy as np
import pandas as pd


class Parameters(Enum):
    EVENT_ACTIVITY = constants.PARAM_EVENT_ACTIVITY
    OBJECT_TYPE = constants.PARAM_OBJECT_TYPE


def _infer_type_from_series(series):
    dtype_str = str(series.dtype)
    if "date" in dtype_str or "time" in dtype_str:
        return "date"
    if "float" in dtype_str or "double" in dtype_str:
        return "float"
    if "int" in dtype_str:
        return "int"
    if "bool" in dtype_str:
        return "boolean"

    if dtype_str != "object":
        return "string"

    values = series.dropna()
    if values.empty:
        return "string"

    def _isinstance_all(values_iter, types):
        return all(isinstance(v, types) for v in values_iter)

    values_list = values.tolist()
    if _isinstance_all(values_list, (bool,)):
        return "boolean"
    if _isinstance_all(values_list, (int,)):
        return "int"
    if _isinstance_all(values_list, (float, int)):
        return "float"
    if _isinstance_all(values_list, (pd.Timestamp, np.datetime64, dt.datetime, dt.date)):
        return "date"

    return "string"


def get(ocel: OCEL, parameters: Optional[Dict[Any, Any]] = None):
    if parameters is None:
        parameters = {}

    event_activity_column = exec_utils.get_param_value(
        Parameters.EVENT_ACTIVITY, parameters, ocel.event_activity
    )
    object_type_column = exec_utils.get_param_value(
        Parameters.OBJECT_TYPE, parameters, ocel.object_type_column
    )

    ets = {}
    for k, v in ocel.events.groupby(event_activity_column):
        cols = v.dropna(axis="columns", how="all").columns
        ets[k] = {
            x: _infer_type_from_series(v[x])
            for x in cols
            if not x.startswith("ocel:")
        }

    ots = {}
    for k, v in ocel.objects.groupby(object_type_column):
        cols = v.dropna(axis="columns", how="all").columns
        ots[k] = {
            x: _infer_type_from_series(v[x])
            for x in cols
            if not x.startswith("ocel:")
        }

    ots2 = {}
    for k, v in ocel.object_changes.groupby(object_type_column):
        cols = v.dropna(axis="columns", how="all").columns
        ots2[k] = {
            x: _infer_type_from_series(v[x])
            for x in cols
            if not x.startswith("ocel:")
        }

    for k in ots2:
        if k not in ots:
            ots[k] = ots2[k]
        else:
            for x in ots2[k]:
                if x not in ots[k]:
                    ots[k][x] = ots2[k][x]

    return ets, ots
