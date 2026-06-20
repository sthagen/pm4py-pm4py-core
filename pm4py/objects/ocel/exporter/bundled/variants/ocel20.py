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
import datetime as dt
import io
import json
import os
import zipfile

import numpy as np
import pandas as pd

from pm4py.objects.ocel import constants
from pm4py.objects.ocel.exporter.util import clean_dataframes
from pm4py.objects.ocel.obj import OCEL
from pm4py.objects.ocel.util import ocel_consistency
from pm4py.util import constants as pm4_constants, exec_utils, pandas_utils


class Parameters(Enum):
    EVENT_ID = constants.PARAM_EVENT_ID
    EVENT_ACTIVITY = constants.PARAM_EVENT_ACTIVITY
    EVENT_TIMESTAMP = constants.PARAM_EVENT_TIMESTAMP
    OBJECT_ID = constants.PARAM_OBJECT_ID
    OBJECT_TYPE = constants.PARAM_OBJECT_TYPE
    QUALIFIER = constants.PARAM_QUALIFIER
    CHANGED_FIELD = constants.PARAM_CHNGD_FIELD
    ENCODING = "encoding"
    STORAGE_FORMAT = "storage_format"


_SAFE_FILENAME_BYTES = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")


def _percent_encode(value: str) -> str:
    encoded = []
    for byte in str(value).encode("utf-8"):
        if byte in _SAFE_FILENAME_BYTES:
            encoded.append(chr(byte))
        else:
            encoded.append("%%%02X" % byte)
    return "".join(encoded)


def _is_null(value) -> bool:
    return clean_dataframes.is_null(value)


def _attribute_columns(df: pd.DataFrame, reserved: List[str]) -> List[str]:
    return [
        column
        for column in df.columns
        if column not in reserved and not str(column).startswith("ocel:")
    ]


def _primitive_type_from_values(values: List[Any]) -> str:
    non_null = [clean_dataframes.normalize_value(value) for value in values if not _is_null(value)]
    if not non_null:
        return "string"

    if all(isinstance(value, (bool, np.bool_)) for value in non_null):
        return "boolean"
    if all(isinstance(value, (int, np.integer)) and not isinstance(value, (bool, np.bool_)) for value in non_null):
        return "integer"
    if all(isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, (bool, np.bool_)) for value in non_null):
        return "float"
    if all(isinstance(value, (pd.Timestamp, dt.datetime, dt.date, np.datetime64)) for value in non_null):
        return "datetime"
    return "string"


def _primitive_type(df: pd.DataFrame, column: str) -> str:
    if column not in df.columns:
        return "string"
    dtype = df[column].dtype
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    if pd.api.types.is_integer_dtype(dtype):
        return "integer"
    if pd.api.types.is_float_dtype(dtype):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"
    return _primitive_type_from_values(df[column].tolist())


def _normalize_table(df: pd.DataFrame, storage_format: str) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if str(df[col].dtype) == "object":
            df[col] = df[col].map(clean_dataframes.normalize_value)
        elif storage_format == "csv" and (
            "date" in str(df[col].dtype) or "time" in str(df[col].dtype)
        ):
            df[col] = df[col].map(
                lambda value: "" if _is_null(value) else pd.Timestamp(value).isoformat()
            )
    return df


def _write_table_to_archive(
    archive: zipfile.ZipFile,
    table_path: str,
    df: pd.DataFrame,
    storage_format: str,
    encoding: str,
):
    if storage_format == "csv":
        buffer = io.StringIO()
        df.to_csv(buffer, index=False, na_rep="")
        archive.writestr(table_path, buffer.getvalue().encode(encoding))
    else:
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False)
        archive.writestr(table_path, buffer.getvalue())


def _write_table_to_directory(
    root_path: str,
    table_path: str,
    df: pd.DataFrame,
    storage_format: str,
    encoding: str,
):
    full_path = os.path.join(root_path, *table_path.split("/"))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    if storage_format == "csv":
        df.to_csv(full_path, index=False, na_rep="", encoding=encoding)
    else:
        df.to_parquet(full_path, index=False)


def _write_json_to_archive(archive: zipfile.ZipFile, path: str, content: Dict[str, Any], encoding: str):
    archive.writestr(
        path,
        json.dumps(content, ensure_ascii=False, indent=2).encode(encoding),
    )


def _write_json_to_directory(root_path: str, path: str, content: Dict[str, Any], encoding: str):
    full_path = os.path.join(root_path, *path.split("/"))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding=encoding) as f:
        json.dump(content, f, ensure_ascii=False, indent=2)


def _cleanup_known_bundle_files(root_path: str):
    for relative_dir in ("events", "objects", "object_changes", "relations"):
        full_dir = os.path.join(root_path, relative_dir)
        if not os.path.isdir(full_dir):
            continue
        for filename in os.listdir(full_dir):
            if filename.endswith(".csv") or filename.endswith(".parquet"):
                os.remove(os.path.join(full_dir, filename))


def _relation_table(df: pd.DataFrame, columns: Dict[str, str]) -> pd.DataFrame:
    source_columns = list(columns.keys())
    df = df.copy()
    for column in source_columns:
        if column not in df.columns:
            df[column] = None
    return df[source_columns].rename(columns=columns)


def _object_type_by_id(ocel: OCEL, object_id: str, object_type: str) -> Dict[Any, Any]:
    return (
        ocel.objects[[object_id, object_type]]
        .drop_duplicates(subset=[object_id])
        .set_index(object_id)[object_type]
        .to_dict()
    )


def _changes_for_type(
    ocel: OCEL,
    object_type_name: str,
    object_type_by_id: Dict[Any, Any],
    object_id: str,
    object_type: str,
) -> pd.DataFrame:
    changes = ocel.object_changes.copy()
    if len(changes) == 0:
        return changes
    if object_type not in changes.columns:
        changes[object_type] = changes[object_id].map(object_type_by_id)
    else:
        missing_type = changes[object_type].isna()
        if missing_type.any():
            changes.loc[missing_type, object_type] = changes.loc[missing_type, object_id].map(object_type_by_id)
    return changes[changes[object_type] == object_type_name]


def _object_change_table(
    changes: pd.DataFrame,
    attr_columns: List[str],
    object_id: str,
    event_timestamp: str,
    changed_field: str,
) -> pd.DataFrame:
    records = []
    for record in changes.to_dict("records"):
        changed_attr = record.get(changed_field)
        if (
            _is_null(record.get(object_id))
            or _is_null(record.get(event_timestamp))
            or _is_null(changed_attr)
        ):
            continue
        row = {
            "ocel_id": record.get(object_id),
            "ocel_time": record.get(event_timestamp),
            "ocel_changed_field": changed_attr,
        }
        for column in attr_columns:
            row[column] = None
        if changed_attr in attr_columns:
            row[changed_attr] = record.get(changed_attr)
        records.append(row)

    columns = ["ocel_id", "ocel_time", "ocel_changed_field"] + attr_columns
    if records:
        return pandas_utils.instantiate_dataframe(records, columns=columns)
    return pandas_utils.instantiate_dataframe({column: [] for column in columns})


def apply(ocel: OCEL, target_path: str, parameters: Optional[Dict[Any, Any]] = None):
    """
    Exports an OCEL 2.0 object-centric event log to the bundled CSV/Parquet format.
    """
    if parameters is None:
        parameters = {}

    encoding = exec_utils.get_param_value(
        Parameters.ENCODING, parameters, pm4_constants.DEFAULT_ENCODING
    )
    storage_format = exec_utils.get_param_value(
        Parameters.STORAGE_FORMAT, parameters, "parquet"
    )
    if storage_format not in {"csv", "parquet"}:
        raise ValueError("OCEL bundle storage format must be 'csv' or 'parquet'.")

    event_id = exec_utils.get_param_value(
        Parameters.EVENT_ID, parameters, ocel.event_id_column
    )
    event_activity = exec_utils.get_param_value(
        Parameters.EVENT_ACTIVITY, parameters, ocel.event_activity
    )
    event_timestamp = exec_utils.get_param_value(
        Parameters.EVENT_TIMESTAMP, parameters, ocel.event_timestamp
    )
    object_id = exec_utils.get_param_value(
        Parameters.OBJECT_ID, parameters, ocel.object_id_column
    )
    object_type = exec_utils.get_param_value(
        Parameters.OBJECT_TYPE, parameters, ocel.object_type_column
    )
    qualifier = exec_utils.get_param_value(
        Parameters.QUALIFIER, parameters, ocel.qualifier
    )
    changed_field = exec_utils.get_param_value(
        Parameters.CHANGED_FIELD, parameters, ocel.changed_field
    )

    ocel = ocel_consistency.apply(ocel, parameters=parameters)
    object_type_by_id = _object_type_by_id(ocel, object_id, object_type)

    extension = storage_format
    event_types = sorted(
        str(value)
        for value in pandas_utils.format_unique(ocel.events[event_activity].dropna().unique())
    )
    object_types = sorted(
        str(value)
        for value in pandas_utils.format_unique(ocel.objects[object_type].dropna().unique())
    )

    meta = {
        "ocelVersion": "2.0",
        "bundleFormatVersion": "1.0",
        "storageFormat": storage_format,
        "eventTypes": {},
        "objectTypes": {},
        "relations": {
            "e2o": "relations/e2o.%s" % extension,
            "o2o": "relations/o2o.%s" % extension,
        },
    }
    tables = {}

    for event_type_name in event_types:
        encoded_type = _percent_encode(event_type_name)
        table_path = "events/event_%s.%s" % (encoded_type, extension)
        df = ocel.events[ocel.events[event_activity] == event_type_name].copy()
        attr_columns = _attribute_columns(
            df, [event_id, event_activity, event_timestamp]
        )
        df = df[[event_id, event_timestamp] + attr_columns].rename(
            columns={event_id: "ocel_id", event_timestamp: "ocel_time"}
        )
        df = _normalize_table(df, storage_format)
        tables[table_path] = df
        meta["eventTypes"][event_type_name] = {
            "file": table_path,
            "attributes": {column: _primitive_type(df, column) for column in attr_columns},
        }

    for object_type_name in object_types:
        encoded_type = _percent_encode(object_type_name)
        table_path = "objects/object_%s.%s" % (encoded_type, extension)
        changes_path = "object_changes/object_changes_%s.%s" % (
            encoded_type,
            extension,
        )

        df = ocel.objects[ocel.objects[object_type] == object_type_name].copy()
        object_attr_columns = _attribute_columns(df, [object_id, object_type])

        changes = _changes_for_type(
            ocel, object_type_name, object_type_by_id, object_id, object_type
        )
        change_attr_columns = _attribute_columns(
            changes, [object_id, object_type, event_timestamp, changed_field]
        )
        for changed_attr in (
            changes[changed_field].dropna().tolist()
            if changed_field in changes.columns
            else []
        ):
            if changed_attr not in change_attr_columns:
                change_attr_columns.append(changed_attr)

        attr_columns = []
        for column in object_attr_columns + change_attr_columns:
            if column not in attr_columns:
                attr_columns.append(column)

        object_table = df[[object_id] + object_attr_columns].copy()
        for column in attr_columns:
            if column not in object_table.columns:
                object_table[column] = None
        object_table = object_table[[object_id] + attr_columns].rename(
            columns={object_id: "ocel_id"}
        )
        object_table = _normalize_table(object_table, storage_format)
        tables[table_path] = object_table

        change_table = _object_change_table(
            changes, attr_columns, object_id, event_timestamp, changed_field
        )
        change_table = _normalize_table(change_table, storage_format)
        tables[changes_path] = change_table

        meta["objectTypes"][object_type_name] = {
            "file": table_path,
            "changesFile": changes_path,
            "attributes": {
                column: _primitive_type(
                    pandas_utils.concat(
                        [
                            object_table.rename(columns={"ocel_id": object_id}),
                            change_table.rename(
                                columns={
                                    "ocel_id": object_id,
                                    "ocel_time": event_timestamp,
                                    "ocel_changed_field": changed_field,
                                }
                            ),
                        ],
                        ignore_index=True,
                    ),
                    column,
                )
                for column in attr_columns
            },
        }

    e2o = _relation_table(
        ocel.relations,
        {
            event_id: "ocel_event_id",
            object_id: "ocel_object_id",
            qualifier: "ocel_qualifier",
        },
    )
    tables[meta["relations"]["e2o"]] = _normalize_table(e2o, storage_format)

    o2o = _relation_table(
        ocel.o2o,
        {
            object_id: "ocel_source_id",
            object_id + "_2": "ocel_target_id",
            qualifier: "ocel_qualifier",
        },
    )
    tables[meta["relations"]["o2o"]] = _normalize_table(o2o, storage_format)

    target_path = str(target_path)
    if target_path.lower().endswith(".zip"):
        if os.path.exists(target_path):
            os.remove(target_path)
        with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as archive:
            _write_json_to_archive(archive, "ocel-meta.json", meta, encoding)
            for table_path, df in tables.items():
                _write_table_to_archive(archive, table_path, df, storage_format, encoding)
    else:
        os.makedirs(target_path, exist_ok=True)
        _cleanup_known_bundle_files(target_path)
        _write_json_to_directory(target_path, "ocel-meta.json", meta, encoding)
        for table_path, df in tables.items():
            _write_table_to_directory(target_path, table_path, df, storage_format, encoding)
