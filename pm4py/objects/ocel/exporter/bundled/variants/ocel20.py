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
from typing import Optional, Dict, Any, List, Tuple
import codecs
import csv
import datetime as dt
from decimal import Decimal
import io
import json
import math
import os
import zipfile

import numpy as np
import pandas as pd

from pm4py.objects.ocel import constants
from pm4py.objects.ocel.exporter.util import clean_dataframes
from pm4py.objects.ocel.obj import OCEL
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


_SAFE_FILENAME_BYTES = set(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"
)


def _require_utf8(encoding: str) -> str:
    try:
        normalized = codecs.lookup(encoding).name
    except LookupError as exc:
        raise ValueError("Unknown OCEL bundle encoding '%s'." % encoding) from exc
    if normalized != "utf-8":
        raise ValueError("OCEL bundle metadata and CSV tables must use UTF-8 encoding.")
    return "utf-8"


def _percent_encode(value: str) -> str:
    encoded = []
    for byte in value.encode("utf-8"):
        encoded.append(chr(byte) if byte in _SAFE_FILENAME_BYTES else "%%%02X" % byte)
    return "".join(encoded)


def _is_null(value) -> bool:
    return clean_dataframes.is_null(value)


def _values_equal(left: Any, right: Any) -> bool:
    if (
        isinstance(left, (int, float, np.integer, np.floating))
        and not isinstance(left, (bool, np.bool_))
        and isinstance(right, (int, float, np.integer, np.floating))
        and not isinstance(right, (bool, np.bool_))
    ):
        return Decimal(str(left)) == Decimal(str(right))
    return type(left) is type(right) and left == right


def _attribute_columns(dataframe: pd.DataFrame, reserved: List[str]) -> List[str]:
    columns = []
    for column in dataframe.columns:
        if column in reserved or str(column).startswith("ocel:"):
            continue
        if not isinstance(column, str) or not column:
            raise ValueError("OCEL bundle attribute names must be non-empty strings.")
        columns.append(column)
    return columns


def _primitive_type_from_values(values: List[Any]) -> str:
    non_null = [value for value in values if not _is_null(value)]
    if not non_null:
        return "string"
    if all(isinstance(value, (bool, np.bool_)) for value in non_null):
        return "boolean"
    if all(
        isinstance(value, (int, np.integer))
        and not isinstance(value, (bool, np.bool_))
        for value in non_null
    ):
        return "integer"
    if all(
        isinstance(value, (int, float, np.integer, np.floating))
        and not isinstance(value, (bool, np.bool_))
        and math.isfinite(float(value))
        for value in non_null
    ):
        return "float"
    if all(
        isinstance(value, (pd.Timestamp, dt.datetime, dt.date, np.datetime64))
        for value in non_null
    ):
        return "time"
    return "string"


def _timestamp(value: Any, label: str) -> pd.Timestamp:
    if _is_null(value):
        raise ValueError("%s cannot be missing." % label)
    try:
        timestamp = value if isinstance(value, pd.Timestamp) else pd.Timestamp(value)
    except BaseException as exc:
        raise ValueError("%s is not a timestamp." % label) from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        timestamp = timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def _coerce_value(value: Any, primitive_type: str, label: str, optional: bool):
    if _is_null(value):
        if optional:
            return None
        raise ValueError("%s cannot be missing." % label)
    value = clean_dataframes.normalize_value(value)
    if primitive_type == "string":
        if isinstance(value, (list, dict, tuple, set)):
            raise ValueError("%s must be a scalar string value." % label)
        return str(value)
    if primitive_type == "integer":
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
            raise ValueError("%s must be an integer." % label)
        return int(value)
    if primitive_type == "float":
        if isinstance(value, (bool, np.bool_)) or not isinstance(
            value, (int, float, np.integer, np.floating)
        ):
            raise ValueError("%s must be a floating-point number." % label)
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("%s must be finite." % label)
        return value
    if primitive_type == "boolean":
        if not isinstance(value, (bool, np.bool_)):
            raise ValueError("%s must be boolean." % label)
        return bool(value)
    return _timestamp(value, label)


def _prepare_table(
    dataframe: pd.DataFrame,
    fixed: List[Tuple[str, str, bool]],
    attributes: List[Tuple[str, str]],
) -> pd.DataFrame:
    expected = [name for name, _, _ in fixed] + [name for name, _ in attributes]
    dataframe = dataframe.copy()
    for column in expected:
        if column not in dataframe.columns:
            dataframe[column] = None
    dataframe = dataframe[expected]
    fixed_names = {name for name, _, _ in fixed}
    type_by_name = {name: primitive_type for name, primitive_type, _ in fixed}
    type_by_name.update(attributes)
    allow_empty = {name for name, _, empty_allowed in fixed if empty_allowed}
    for column in expected:
        optional = column not in fixed_names
        values = [
            _coerce_value(value, type_by_name[column], column, optional)
            for value in dataframe[column].tolist()
        ]
        if column in fixed_names and column not in allow_empty and any(value == "" for value in values):
            raise ValueError("Fixed column '%s' cannot contain empty strings." % column)
        dataframe[column] = pd.Series(
            values, index=dataframe.index, dtype="object"
        )
    return dataframe


def _csv_value(value: Any, primitive_type: str) -> str:
    if value is None or _is_null(value):
        return ""
    if primitive_type == "boolean":
        return "true" if value else "false"
    if primitive_type == "time":
        return _timestamp(value, "timestamp").isoformat()
    if primitive_type == "integer":
        return str(int(value))
    if primitive_type == "float":
        return repr(float(value))
    return str(value)


def _table_csv_bytes(
    dataframe: pd.DataFrame,
    fixed: List[Tuple[str, str, bool]],
    attributes: List[Tuple[str, str]],
    encoding: str,
) -> bytes:
    type_by_name = {name: primitive_type for name, primitive_type, _ in fixed}
    type_by_name.update(attributes)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, dialect="excel", lineterminator="\r\n")
    writer.writerow(dataframe.columns)
    for row in dataframe.itertuples(index=False, name=None):
        writer.writerow(
            [_csv_value(value, type_by_name[column]) for column, value in zip(dataframe.columns, row)]
        )
    return buffer.getvalue().encode(encoding)


def _arrow_type(primitive_type: str):
    try:
        import pyarrow as pa
    except ImportError as exc:
        raise ImportError(
            "pyarrow is required for specification-compliant OCEL Parquet bundles."
        ) from exc
    return {
        "string": pa.string(),
        "integer": pa.int64(),
        "float": pa.float64(),
        "boolean": pa.bool_(),
        "time": pa.timestamp("us", tz="UTC"),
    }[primitive_type]


def _table_parquet_bytes(
    dataframe: pd.DataFrame,
    fixed: List[Tuple[str, str, bool]],
    attributes: List[Tuple[str, str]],
) -> bytes:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ImportError(
            "pyarrow is required for specification-compliant OCEL Parquet bundles."
        ) from exc
    fields = [
        pa.field(name, _arrow_type(primitive_type), nullable=False)
        for name, primitive_type, _ in fixed
    ] + [
        pa.field(name, _arrow_type(primitive_type), nullable=True)
        for name, primitive_type in attributes
    ]
    schema = pa.schema(fields)
    arrays = []
    for field in fields:
        values = dataframe[field.name].tolist()
        if pa.types.is_timestamp(field.type):
            values = [
                None
                if value is None or _is_null(value)
                else _timestamp(value, field.name).floor("us")
                for value in values
            ]
        arrays.append(pa.array(values, type=field.type))
    table = pa.Table.from_arrays(arrays, schema=schema)
    buffer = io.BytesIO()
    pq.write_table(
        table,
        buffer,
        version="2.6",
        coerce_timestamps="us",
        allow_truncated_timestamps=False,
    )
    return buffer.getvalue()


def _table_bytes(
    dataframe: pd.DataFrame,
    storage_format: str,
    fixed: List[Tuple[str, str, bool]],
    attributes: List[Tuple[str, str]],
    encoding: str,
) -> bytes:
    dataframe = _prepare_table(dataframe, fixed, attributes)
    if storage_format == "csv":
        return _table_csv_bytes(dataframe, fixed, attributes, encoding)
    return _table_parquet_bytes(dataframe, fixed, attributes)


def _write_archive(target_path: str, files: Dict[str, bytes]):
    with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in files.items():
            archive.writestr(path, content)


def _cleanup_known_bundle_files(root_path: str):
    for relative_dir in ("events", "objects", "object_changes", "relations"):
        full_dir = os.path.join(root_path, relative_dir)
        if not os.path.isdir(full_dir):
            continue
        for filename in os.listdir(full_dir):
            if filename.endswith(".csv") or filename.endswith(".parquet"):
                os.remove(os.path.join(full_dir, filename))


def _write_directory(target_path: str, files: Dict[str, bytes]):
    os.makedirs(target_path, exist_ok=True)
    _cleanup_known_bundle_files(target_path)
    for path, content in files.items():
        full_path = os.path.join(target_path, *path.split("/"))
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as file:
            file.write(content)


def _normalized_string(value: Any, label: str, allow_empty: bool = False) -> str:
    if _is_null(value):
        if allow_empty:
            return ""
        raise ValueError("%s cannot be missing." % label)
    value = str(clean_dataframes.normalize_value(value))
    if not value and not allow_empty:
        raise ValueError("%s cannot be empty." % label)
    return value


def _require_unique(values: List[str], label: str):
    if len(values) != len(set(values)):
        raise ValueError("OCEL bundle %s identifiers must be unique." % label)


def _relation_dataframe(records: List[Dict[str, Any]], columns: List[str]) -> pd.DataFrame:
    return pandas_utils.instantiate_dataframe(records, columns=columns)


def apply(ocel: OCEL, target_path: str, parameters: Optional[Dict[Any, Any]] = None):
    """Exports an OCEL 2.0 log to the bundled CSV/Parquet format."""
    if parameters is None:
        parameters = {}
    encoding = exec_utils.get_param_value(
        Parameters.ENCODING, parameters, pm4_constants.DEFAULT_ENCODING
    )
    encoding = _require_utf8(encoding)
    storage_format = exec_utils.get_param_value(Parameters.STORAGE_FORMAT, parameters, "parquet")
    if storage_format not in {"csv", "parquet"}:
        raise ValueError("OCEL bundle storage format must be 'csv' or 'parquet'.")

    event_id = exec_utils.get_param_value(Parameters.EVENT_ID, parameters, ocel.event_id_column)
    event_activity = exec_utils.get_param_value(Parameters.EVENT_ACTIVITY, parameters, ocel.event_activity)
    event_timestamp = exec_utils.get_param_value(Parameters.EVENT_TIMESTAMP, parameters, ocel.event_timestamp)
    object_id = exec_utils.get_param_value(Parameters.OBJECT_ID, parameters, ocel.object_id_column)
    object_type = exec_utils.get_param_value(Parameters.OBJECT_TYPE, parameters, ocel.object_type_column)
    qualifier = exec_utils.get_param_value(Parameters.QUALIFIER, parameters, ocel.qualifier)
    changed_field = exec_utils.get_param_value(Parameters.CHANGED_FIELD, parameters, ocel.changed_field)

    events = ocel.events.copy()
    objects = ocel.objects.copy()
    relations = ocel.relations.copy()
    o2o = ocel.o2o.copy()
    changes = ocel.object_changes.copy()
    for dataframe, required, label in (
        (events, [event_id, event_activity, event_timestamp], "events"),
        (objects, [object_id, object_type], "objects"),
        (relations, [event_id, object_id, qualifier], "E2O relations"),
        (o2o, [object_id, object_id + "_2", qualifier], "O2O relations"),
        (changes, [object_id, event_timestamp, changed_field], "object changes"),
    ):
        missing = [column for column in required if column not in dataframe.columns]
        if missing:
            raise ValueError("OCEL %s are missing columns: %s." % (label, ", ".join(missing)))

    event_ids = [_normalized_string(value, "event id") for value in events[event_id].tolist()]
    object_ids = [_normalized_string(value, "object id") for value in objects[object_id].tolist()]
    _require_unique(event_ids, "event")
    _require_unique(object_ids, "object")
    events[event_id] = event_ids
    objects[object_id] = object_ids
    events[event_activity] = [
        _normalized_string(value, "event type") for value in events[event_activity].tolist()
    ]
    objects[object_type] = [
        _normalized_string(value, "object type") for value in objects[object_type].tolist()
    ]
    event_id_set = set(event_ids)
    object_type_by_id = dict(zip(object_ids, objects[object_type].tolist()))

    event_attribute_columns = _attribute_columns(
        events, [event_id, event_activity, event_timestamp]
    )
    object_attribute_columns = _attribute_columns(objects, [object_id, object_type])
    change_attribute_columns = _attribute_columns(
        changes, [object_id, object_type, event_timestamp, changed_field]
    )
    if set(event_attribute_columns).intersection({"ocel_id", "ocel_time"}):
        raise ValueError("Event attribute name collides with a fixed bundle column.")
    if set(object_attribute_columns + change_attribute_columns).intersection(
        {"ocel_id", "ocel_time", "ocel_changed_field"}
    ):
        raise ValueError("Object attribute name collides with a fixed bundle column.")

    normalized_changes = []
    change_keys = {}
    for record in changes.to_dict("records"):
        oid = _normalized_string(record.get(object_id), "object-change id")
        if oid not in object_type_by_id:
            raise ValueError("Object change references unknown object '%s'." % oid)
        record_type = record.get(object_type, object_type_by_id[oid])
        if not _is_null(record_type) and str(record_type) != object_type_by_id[oid]:
            raise ValueError("Object change type does not match object '%s'." % oid)
        field = _normalized_string(record.get(changed_field), "changed field")
        if field not in record or _is_null(record.get(field)):
            raise ValueError("Object change for '%s' has no value for '%s'." % (oid, field))
        populated_fields = [
            column
            for column in change_attribute_columns
            if column in record and not _is_null(record.get(column))
        ]
        if populated_fields != [field]:
            raise ValueError("An object-change row must assign exactly its changed field.")
        normalized_timestamp = _timestamp(
            record.get(event_timestamp), "object-change timestamp"
        )
        key = (oid, normalized_timestamp.value, field)
        value = clean_dataframes.normalize_value(record.get(field))
        if key in change_keys:
            if not _values_equal(change_keys[key], value):
                raise ValueError("Object attribute has conflicting values at one timestamp.")
            raise ValueError("Duplicate object attribute assignment cannot be exported.")
        change_keys[key] = value
        normalized = dict(record)
        normalized[object_id] = oid
        normalized[object_type] = object_type_by_id[oid]
        normalized[event_timestamp] = normalized_timestamp
        normalized[changed_field] = field
        normalized_changes.append(normalized)
        if field not in change_attribute_columns:
            change_attribute_columns.append(field)
    changes = pandas_utils.instantiate_dataframe(normalized_changes) if normalized_changes else changes.iloc[0:0].copy()

    extension = storage_format
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
    table_specs = {}

    for event_type_name in sorted(set(events[event_activity].tolist())):
        selected = events[events[event_activity] == event_type_name].copy()
        attributes = [
            column
            for column in event_attribute_columns
            if selected[column].notna().any()
        ]
        attribute_types = [
            (column, _primitive_type_from_values(selected[column].tolist()))
            for column in attributes
        ]
        table_path = "events/event_%s.%s" % (_percent_encode(event_type_name), extension)
        table = selected[[event_id, event_timestamp] + attributes].rename(
            columns={event_id: "ocel_id", event_timestamp: "ocel_time"}
        )
        fixed = [("ocel_id", "string", False), ("ocel_time", "time", False)]
        table_specs[table_path] = (table, fixed, attribute_types)
        meta["eventTypes"][event_type_name] = {
            "file": table_path,
            "attributes": [
                {"name": name, "type": primitive_type}
                for name, primitive_type in attribute_types
            ],
        }

    for object_type_name in sorted(set(objects[object_type].tolist())):
        selected = objects[objects[object_type] == object_type_name].copy()
        type_changes = (
            changes[changes[object_type] == object_type_name].copy()
            if len(changes) > 0 and object_type in changes.columns
            else changes.iloc[0:0].copy()
        )
        attributes = []
        for column in object_attribute_columns:
            if selected[column].notna().any() and column not in attributes:
                attributes.append(column)
        if len(type_changes) > 0:
            for field in type_changes[changed_field].tolist():
                if field not in attributes:
                    attributes.append(field)
        reserved = {"ocel_id", "ocel_time", "ocel_changed_field"}
        if any(attribute in reserved for attribute in attributes):
            raise ValueError("Object attribute name collides with a fixed bundle column.")

        attribute_types = []
        for column in attributes:
            values = selected[column].tolist() if column in selected.columns else []
            if column in type_changes.columns:
                values += type_changes[column].tolist()
            attribute_types.append((column, _primitive_type_from_values(values)))

        encoded_type = _percent_encode(object_type_name)
        table_path = "objects/object_%s.%s" % (encoded_type, extension)
        changes_path = "object_changes/object_changes_%s.%s" % (encoded_type, extension)
        object_table = selected[[object_id] + [column for column in attributes if column in selected.columns]].copy()
        for column in attributes:
            if column not in object_table.columns:
                object_table[column] = None
        object_table = object_table[[object_id] + attributes].rename(columns={object_id: "ocel_id"})
        table_specs[table_path] = (object_table, [("ocel_id", "string", False)], attribute_types)

        change_records = []
        for record in type_changes.to_dict("records"):
            field = record[changed_field]
            row = {
                "ocel_id": record[object_id],
                "ocel_time": record[event_timestamp],
                "ocel_changed_field": field,
            }
            for attribute in attributes:
                row[attribute] = record.get(attribute) if attribute == field else None
            change_records.append(row)
        change_columns = ["ocel_id", "ocel_time", "ocel_changed_field"] + attributes
        change_table = pandas_utils.instantiate_dataframe(change_records, columns=change_columns)
        table_specs[changes_path] = (
            change_table,
            [
                ("ocel_id", "string", False),
                ("ocel_time", "time", False),
                ("ocel_changed_field", "string", False),
            ],
            attribute_types,
        )
        meta["objectTypes"][object_type_name] = {
            "file": table_path,
            "changesFile": changes_path,
            "attributes": [
                {"name": name, "type": primitive_type}
                for name, primitive_type in attribute_types
            ],
        }

    e2o_records = []
    e2o_keys = set()
    for record in relations.to_dict("records"):
        eid = _normalized_string(record.get(event_id), "E2O event id")
        oid = _normalized_string(record.get(object_id), "E2O object id")
        relation_qualifier = _normalized_string(record.get(qualifier), "E2O qualifier", allow_empty=True)
        if eid not in event_id_set or oid not in object_type_by_id:
            raise ValueError("E2O relation references an unknown event or object.")
        key = (eid, oid, relation_qualifier)
        if key in e2o_keys:
            raise ValueError("Duplicate E2O relation cannot be exported.")
        e2o_keys.add(key)
        e2o_records.append(
            {"ocel_event_id": eid, "ocel_object_id": oid, "ocel_qualifier": relation_qualifier}
        )
    e2o_fixed = [
        ("ocel_event_id", "string", False),
        ("ocel_object_id", "string", False),
        ("ocel_qualifier", "string", True),
    ]
    table_specs[meta["relations"]["e2o"]] = (
        _relation_dataframe(e2o_records, [name for name, _, _ in e2o_fixed]),
        e2o_fixed,
        [],
    )

    o2o_records = []
    o2o_keys = set()
    for record in o2o.to_dict("records"):
        source = _normalized_string(record.get(object_id), "O2O source id")
        target = _normalized_string(record.get(object_id + "_2"), "O2O target id")
        relation_qualifier = _normalized_string(record.get(qualifier), "O2O qualifier", allow_empty=True)
        if source not in object_type_by_id or target not in object_type_by_id:
            raise ValueError("O2O relation references an unknown object.")
        key = (source, target, relation_qualifier)
        if key in o2o_keys:
            raise ValueError("Duplicate O2O relation cannot be exported.")
        o2o_keys.add(key)
        o2o_records.append(
            {"ocel_source_id": source, "ocel_target_id": target, "ocel_qualifier": relation_qualifier}
        )
    o2o_fixed = [
        ("ocel_source_id", "string", False),
        ("ocel_target_id", "string", False),
        ("ocel_qualifier", "string", True),
    ]
    table_specs[meta["relations"]["o2o"]] = (
        _relation_dataframe(o2o_records, [name for name, _, _ in o2o_fixed]),
        o2o_fixed,
        [],
    )

    files = {
        "ocel-meta.json": json.dumps(
            meta, ensure_ascii=False, indent=2, allow_nan=False
        ).encode(encoding)
    }
    for table_path, (dataframe, fixed, attributes) in table_specs.items():
        files[table_path] = _table_bytes(
            dataframe, storage_format, fixed, attributes, encoding
        )

    target_path = str(target_path)
    if target_path.lower().endswith(".ocel.zip"):
        _write_archive(target_path, files)
    elif target_path.lower().endswith(".zip"):
        raise ValueError("Bundled OCEL archives use the '.ocel.zip' extension.")
    else:
        _write_directory(target_path, files)
