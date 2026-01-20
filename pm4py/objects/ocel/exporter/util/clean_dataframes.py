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
from typing import Optional, Dict, Any, Tuple
import datetime as dt

import numpy as np
import pandas as pd

from pm4py.objects.ocel.obj import OCEL


def is_null(value) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, dict, tuple, set)):
        return False
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def normalize_value(value):
    if is_null(value):
        return None
    if isinstance(value, (list, dict, tuple, set)):
        return value
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, np.datetime64):
        return pd.to_datetime(value).isoformat()
    if isinstance(value, np.timedelta64):
        return str(pd.to_timedelta(value))
    if isinstance(value, np.generic):
        return value.item()
    return value


def get_dataframes_from_ocel(
    ocel: OCEL, parameters: Optional[Dict[Any, Any]] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if parameters is None:
        parameters = {}

    events = ocel.events.copy()
    for col in events.columns:
        if str(events[col].dtype) == "object":
            events[col] = events[col].map(normalize_value)
        elif "date" in str(events[col].dtype):
            events[col] = events[col].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    objects = ocel.objects.copy()
    for col in objects.columns:
        if str(objects[col].dtype) == "object":
            objects[col] = objects[col].map(normalize_value)
        elif "date" in str(objects[col].dtype):
            objects[col] = objects[col].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return events, objects
