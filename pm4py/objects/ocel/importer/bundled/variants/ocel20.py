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
from enum import Enum
from typing import Optional, Dict, Any, List
import io
import json
import os
import zipfile

import pandas as pd

from pm4py.objects.log.util import dataframe_utils
from pm4py.objects.ocel import constants
from pm4py.objects.ocel.obj import OCEL
from pm4py.objects.ocel.util import ocel_consistency
from pm4py.util import constants as pm4_constants, exec_utils, pandas_utils


class Parameters(Enum):
    EVENT_ID = constants.PARAM_EVENT_ID
    EVENT_ACTIVITY = constants.PARAM_EVENT_ACTIVITY
    EVENT_TIMESTAMP = constants.PARAM_EVENT_TIMESTAMP
    OBJECT_ID = constants.PARAM_OBJECT_ID
    OBJECT_TYPE = constants.PARAM_OBJECT_TYPE
    INTERNAL_INDEX = constants.PARAM_INTERNAL_INDEX
    QUALIFIER = constants.PARAM_QUALIFIER
    CHANGED_FIELD = constants.PARAM_CHNGD_FIELD
    ENCODING = "encoding"


def _instantiate_dataframe(records: List[Dict[str, Any]], columns: List[str]):
    if records:
        return pandas_utils.instantiate_dataframe(records)
    return pandas_utils.instantiate_dataframe({column: [] for column in columns})


def _read_meta(file_path: str, encoding: str) -> Dict[str, Any]:
    if os.path.isdir(file_path):
        meta_path = os.path.join(file_path, "ocel-meta.json")
        with open(meta_path, "r", encoding=encoding) as f:
            return json.load(f)

    with zipfile.ZipFile(file_path, "r") as archive:
        with archive.open("ocel-meta.json", "r") as f:
            return json.loads(f.read().decode(encoding))


def _read_table(file_path: str, table_path: str, storage_format: str, encoding: str) -> pd.DataFrame:
    if not table_path:
        raise ValueError("Missing table file declaration in OCEL bundle metadata.")
    if os.path.isdir(file_path):
        full_path = os.path.join(file_path, *table_path.split("/"))
        if storage_format == "csv":
            return pandas_utils.read_csv(full_path, index_col=False, encoding=encoding)
        return pd.read_parquet(full_path)

    with zipfile.ZipFile(file_path, "r") as archive:
        with archive.open(table_path, "r") as f:
            data = f.read()
    if storage_format == "csv":
        return pandas_utils.read_csv(io.BytesIO(data), index_col=False, encoding=encoding)
    return pd.read_parquet(io.BytesIO(data))


def _ensure_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    df = df.copy()
    for column in columns:
        if column not in df.columns:
            df[column] = None
    return df


def _normalize_id_series(series: pd.Series) -> pd.Series:
    if series is None:
        return series
    if pd.api.types.is_float_dtype(series):
        non_null = series.dropna()
        if len(non_null) > 0 and ((non_null % 1) == 0).all():
            series = series.astype("Int64")
            return series.astype("string")
    if pd.api.types.is_numeric_dtype(series):
        return series.astype("string")
    series = series.astype("string")
    return series.str.replace(r"\.0$", "", regex=True)


def _convert_time_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in df.columns:
        return df
    return dataframe_utils.convert_timestamp_columns_in_df(
        df,
        timest_format=pm4_constants.DEFAULT_TIMESTAMP_PARSE_FORMAT,
        timest_columns=[column],
    )


def _read_declared_table(
    file_path: str,
    descriptor: Dict[str, Any],
    key: str,
    storage_format: str,
    encoding: str,
    required_columns: List[str],
) -> pd.DataFrame:
    if key not in descriptor:
        raise ValueError("Missing '%s' in OCEL bundle metadata." % key)
    df = _read_table(file_path, descriptor[key], storage_format, encoding)
    return _ensure_columns(df, required_columns)


def apply(file_path: str, parameters: Optional[Dict[Any, Any]] = None) -> OCEL:
    """
    Imports an OCEL 2.0 object-centric event log from the bundled CSV/Parquet format.
    """
    if parameters is None:
        parameters = {}

    encoding = exec_utils.get_param_value(
        Parameters.ENCODING, parameters, pm4_constants.DEFAULT_ENCODING
    )
    event_id = exec_utils.get_param_value(
        Parameters.EVENT_ID, parameters, constants.DEFAULT_EVENT_ID
    )
    event_activity = exec_utils.get_param_value(
        Parameters.EVENT_ACTIVITY, parameters, constants.DEFAULT_EVENT_ACTIVITY
    )
    event_timestamp = exec_utils.get_param_value(
        Parameters.EVENT_TIMESTAMP, parameters, constants.DEFAULT_EVENT_TIMESTAMP
    )
    object_id = exec_utils.get_param_value(
        Parameters.OBJECT_ID, parameters, constants.DEFAULT_OBJECT_ID
    )
    object_type = exec_utils.get_param_value(
        Parameters.OBJECT_TYPE, parameters, constants.DEFAULT_OBJECT_TYPE
    )
    internal_index = exec_utils.get_param_value(
        Parameters.INTERNAL_INDEX, parameters, constants.DEFAULT_INTERNAL_INDEX
    )
    qualifier = exec_utils.get_param_value(
        Parameters.QUALIFIER, parameters, constants.DEFAULT_QUALIFIER
    )
    changed_field = exec_utils.get_param_value(
        Parameters.CHANGED_FIELD, parameters, constants.DEFAULT_CHNGD_FIELD
    )

    meta = _read_meta(file_path, encoding)
    storage_format = meta.get("storageFormat")
    if storage_format not in {"csv", "parquet"}:
        raise ValueError("OCEL bundle storageFormat must be 'csv' or 'parquet'.")

    event_frames = []
    event_id_type = {}
    event_id_time = {}
    event_types = meta.get("eventTypes", {})
    for event_type_name, descriptor in event_types.items():
        df = _read_declared_table(
            file_path,
            descriptor,
            "file",
            storage_format,
            encoding,
            ["ocel_id", "ocel_time"],
        )
        df = df.rename(columns={"ocel_id": event_id, "ocel_time": event_timestamp})
        df[event_id] = _normalize_id_series(df[event_id])
        df[event_activity] = event_type_name
        df = _convert_time_column(df, event_timestamp)
        event_frames.append(df)
        for row in df[[event_id, event_timestamp]].to_dict("records"):
            event_id_type[row[event_id]] = event_type_name
            event_id_time[row[event_id]] = row[event_timestamp]

    object_frames = []
    object_change_frames = []
    object_id_type = {}
    object_types = meta.get("objectTypes", {})
    for object_type_name, descriptor in object_types.items():
        df = _read_declared_table(
            file_path,
            descriptor,
            "file",
            storage_format,
            encoding,
            ["ocel_id"],
        )
        df = df.rename(columns={"ocel_id": object_id})
        df[object_id] = _normalize_id_series(df[object_id])
        df[object_type] = object_type_name
        object_frames.append(df)
        for oid in pandas_utils.format_unique(df[object_id].dropna().unique()):
            object_id_type[oid] = object_type_name

        changes_df = _read_declared_table(
            file_path,
            descriptor,
            "changesFile",
            storage_format,
            encoding,
            ["ocel_id", "ocel_time", "ocel_changed_field"],
        )
        changes_df = changes_df.rename(
            columns={
                "ocel_id": object_id,
                "ocel_time": event_timestamp,
                "ocel_changed_field": changed_field,
            }
        )
        changes_df[object_id] = _normalize_id_series(changes_df[object_id])
        changes_df[object_type] = object_type_name
        changes_df = _convert_time_column(changes_df, event_timestamp)
        object_change_frames.append(changes_df)

    events = (
        pandas_utils.concat(event_frames, ignore_index=True)
        if event_frames
        else _instantiate_dataframe([], [event_id, event_timestamp, event_activity])
    )
    objects = (
        pandas_utils.concat(object_frames, ignore_index=True)
        if object_frames
        else _instantiate_dataframe([], [object_id, object_type])
    )
    object_changes = (
        pandas_utils.concat(object_change_frames, ignore_index=True)
        if object_change_frames
        else _instantiate_dataframe([], [object_id, event_timestamp, changed_field, object_type])
    )

    relations_meta = meta.get("relations", {})
    e2o = _read_table(file_path, relations_meta.get("e2o", ""), storage_format, encoding)
    e2o = _ensure_columns(e2o, ["ocel_event_id", "ocel_object_id", "ocel_qualifier"])
    e2o = e2o.rename(
        columns={
            "ocel_event_id": event_id,
            "ocel_object_id": object_id,
            "ocel_qualifier": qualifier,
        }
    )
    e2o[event_id] = _normalize_id_series(e2o[event_id])
    e2o[object_id] = _normalize_id_series(e2o[object_id])
    e2o[event_activity] = e2o[event_id].map(event_id_type)
    e2o[event_timestamp] = e2o[event_id].map(event_id_time)
    e2o[object_type] = e2o[object_id].map(object_id_type)

    o2o = _read_table(file_path, relations_meta.get("o2o", ""), storage_format, encoding)
    o2o = _ensure_columns(o2o, ["ocel_source_id", "ocel_target_id", "ocel_qualifier"])
    o2o = o2o.rename(
        columns={
            "ocel_source_id": object_id,
            "ocel_target_id": object_id + "_2",
            "ocel_qualifier": qualifier,
        }
    )
    o2o[object_id] = _normalize_id_series(o2o[object_id])
    o2o[object_id + "_2"] = _normalize_id_series(o2o[object_id + "_2"])

    if len(events) > 0:
        events[internal_index] = events.index
        events = events.sort_values([event_timestamp, internal_index])
        del events[internal_index]

    if len(e2o) > 0:
        e2o[internal_index] = e2o.index
        e2o = e2o.sort_values([event_timestamp, internal_index])
        del e2o[internal_index]

    if len(object_changes) > 0:
        object_changes[internal_index] = object_changes.index
        object_changes = object_changes.sort_values([event_timestamp, internal_index])
        del object_changes[internal_index]

    ocel = OCEL(
        events=events,
        objects=objects,
        relations=e2o,
        o2o=o2o,
        object_changes=object_changes,
        parameters=parameters,
    )
    ocel = ocel_consistency.apply(ocel, parameters=parameters)

    return ocel
