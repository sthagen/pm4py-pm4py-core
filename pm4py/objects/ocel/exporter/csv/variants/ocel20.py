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
import codecs
from decimal import Decimal
import json
import math

import pandas as pd

from pm4py.objects.ocel import constants
from pm4py.objects.ocel.exporter.util import clean_dataframes
from pm4py.objects.ocel.obj import OCEL
from pm4py.objects.ocel.util import ocel_consistency
from pm4py.util import exec_utils, constants as pm4_constants, pandas_utils


class Parameters(Enum):
    EVENT_ID = constants.PARAM_EVENT_ID
    EVENT_ACTIVITY = constants.PARAM_EVENT_ACTIVITY
    EVENT_TIMESTAMP = constants.PARAM_EVENT_TIMESTAMP
    OBJECT_ID = constants.PARAM_OBJECT_ID
    OBJECT_TYPE = constants.PARAM_OBJECT_TYPE
    QUALIFIER = constants.PARAM_QUALIFIER
    CHANGED_FIELD = constants.PARAM_CHNGD_FIELD
    ENCODING = "encoding"
    OBJECT_TYPE_PREFIX = "object_type_prefix"
    O2O_ACTIVITY = "o2o_activity"
    CSV_EVENT_ID = "csv_event_id"
    CSV_EVENT_ACTIVITY = "csv_event_activity"
    CSV_EVENT_TIMESTAMP = "csv_event_timestamp"


def _is_null(value) -> bool:
    return clean_dataframes.is_null(value)


def _timestamp_value(value):
    timestamp = value if isinstance(value, pd.Timestamp) else pd.Timestamp(value)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        timestamp = timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def _timestamp_sort_key(value):
    return _timestamp_value(value).value


def _format_timestamp(value) -> str:
    if _is_null(value):
        return ""
    try:
        return _timestamp_value(value).isoformat()
    except BaseException:
        raise ValueError(
            "OCEL2 CSV timestamps must be ISO 8601 timestamps with timezone information."
        )


def _validate_reference_part(value: Any, name: str) -> str:
    value = clean_dataframes.normalize_value(value)
    if _is_null(value):
        raise ValueError("OCEL2 CSV %s values cannot be empty." % name)
    if isinstance(value, (list, dict, tuple, set)):
        raise ValueError("OCEL2 CSV %s values must be scalar." % name)
    value = str(value)
    if value != value.strip():
        raise ValueError(
            "OCEL2 CSV %s values cannot contain leading or trailing whitespace." % name
        )
    if not value:
        raise ValueError("OCEL2 CSV %s values cannot be empty." % name)
    if any(char in value for char in ("/", "#", "{")):
        raise ValueError(
            "OCEL2 CSV %s values cannot contain '/', '#', or '{'." % name
        )
    return value


def _validate_json_attribute_value(value: Any):
    if isinstance(value, (list, dict, tuple, set)):
        raise ValueError(
            "JSON arrays and objects are not valid OCEL2 CSV attribute values."
        )
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(
            "Non-finite JSON numbers are not valid OCEL2 CSV attribute values."
        )


def _json_dumps(attrs: Dict[str, Any]) -> str:
    normalized = {}
    for key, value in attrs.items():
        if _is_null(value):
            continue
        value = clean_dataframes.normalize_value(value)
        _validate_json_attribute_value(value)
        normalized[str(key)] = value
    if not normalized:
        return ""
    return json.dumps(
        normalized, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def _format_reference(object_id: Any, qualifier: Any = None, attrs: Optional[Dict[str, Any]] = None) -> str:
    value = _validate_reference_part(object_id, "object id")
    if not _is_null(qualifier) and str(qualifier) != "":
        value += "#" + _validate_reference_part(qualifier, "qualifier")
    if attrs:
        value += _json_dumps(attrs)
    return value


def _non_ocel_attribute_columns(df: pd.DataFrame, reserved: List[str]) -> List[str]:
    return [
        column
        for column in df.columns
        if column not in reserved and not str(column).startswith("ocel:")
    ]


def _reference_sort_value(value: Any) -> str:
    return str(clean_dataframes.normalize_value(value))


def _new_row(header_len: int) -> List[str]:
    return [""] * header_len


def _require_utf8(encoding: str) -> str:
    try:
        normalized = codecs.lookup(encoding).name
    except LookupError as exc:
        raise ValueError("Unknown OCEL2 CSV encoding '%s'." % encoding) from exc
    if normalized != "utf-8":
        raise ValueError("OCEL2 CSV files must use UTF-8 encoding.")
    return "utf-8"


def _require_unique(df: pd.DataFrame, column: str, kind: str):
    if column not in df.columns or df[column].isna().any():
        raise ValueError("OCEL2 CSV %s must have non-empty '%s' values." % (kind, column))
    if df[column].duplicated().any():
        duplicate = df.loc[df[column].duplicated(), column].iloc[0]
        raise ValueError("Duplicate %s id '%s' cannot be exported." % (kind, duplicate))


def _require_trimmed(value: Any, kind: str) -> str:
    value = clean_dataframes.normalize_value(value)
    if _is_null(value):
        raise ValueError("OCEL2 CSV %s values cannot be empty." % kind)
    value = str(value)
    if not value or value != value.strip():
        raise ValueError(
            "OCEL2 CSV %s values must be non-empty and contain no leading or trailing whitespace."
            % kind
        )
    return value


def _values_equal(left: Any, right: Any) -> bool:
    left = clean_dataframes.normalize_value(left)
    right = clean_dataframes.normalize_value(right)
    if (
        isinstance(left, (int, float))
        and not isinstance(left, bool)
        and isinstance(right, (int, float))
        and not isinstance(right, bool)
    ):
        return Decimal(str(left)) == Decimal(str(right))
    return type(left) is type(right) and left == right


def apply(
    ocel: OCEL,
    output_path: str,
    objects_path=None,
    parameters: Optional[Dict[Any, Any]] = None,
):
    """
    Exports an OCEL 2.0 object-centric event log to the compact CSV format.
    """
    if parameters is None:
        parameters = {}
    output_path = str(output_path)
    if not output_path.lower().endswith(".ocel.csv"):
        raise ValueError("OCEL2 compact CSV exports use the '.ocel.csv' extension.")

    encoding = exec_utils.get_param_value(
        Parameters.ENCODING, parameters, pm4_constants.DEFAULT_ENCODING
    )
    encoding = _require_utf8(encoding)
    event_id_column = exec_utils.get_param_value(
        Parameters.EVENT_ID, parameters, ocel.event_id_column
    )
    event_activity_column = exec_utils.get_param_value(
        Parameters.EVENT_ACTIVITY, parameters, ocel.event_activity
    )
    event_timestamp_column = exec_utils.get_param_value(
        Parameters.EVENT_TIMESTAMP, parameters, ocel.event_timestamp
    )
    object_id_column = exec_utils.get_param_value(
        Parameters.OBJECT_ID, parameters, ocel.object_id_column
    )
    object_type_column = exec_utils.get_param_value(
        Parameters.OBJECT_TYPE, parameters, ocel.object_type_column
    )
    qualifier_column = exec_utils.get_param_value(
        Parameters.QUALIFIER, parameters, ocel.qualifier
    )
    changed_field_column = exec_utils.get_param_value(
        Parameters.CHANGED_FIELD, parameters, ocel.changed_field
    )
    object_type_prefix = exec_utils.get_param_value(
        Parameters.OBJECT_TYPE_PREFIX, parameters, "ot:"
    )
    o2o_activity = exec_utils.get_param_value(
        Parameters.O2O_ACTIVITY, parameters, "o2o"
    )
    csv_event_id = exec_utils.get_param_value(
        Parameters.CSV_EVENT_ID, parameters, "id"
    )
    csv_event_activity = exec_utils.get_param_value(
        Parameters.CSV_EVENT_ACTIVITY, parameters, "activity"
    )
    csv_event_timestamp = exec_utils.get_param_value(
        Parameters.CSV_EVENT_TIMESTAMP, parameters, "timestamp"
    )

    ocel = ocel_consistency.apply(ocel, parameters=parameters)

    _require_unique(ocel.events, event_id_column, "event")
    _require_unique(ocel.objects, object_id_column, "object")

    object_types = sorted(
        str(x)
        for x in pandas_utils.format_unique(ocel.objects[object_type_column].dropna().unique())
    )
    object_type_columns = [object_type_prefix + object_type for object_type in object_types]

    event_attribute_columns = _non_ocel_attribute_columns(
        ocel.events, [event_id_column, event_activity_column, event_timestamp_column]
    )
    object_attribute_columns = _non_ocel_attribute_columns(
        ocel.objects, [object_id_column, object_type_column]
    )
    reserved_output_columns = {
        csv_event_id,
        csv_event_activity,
        csv_event_timestamp,
        *object_type_columns,
    }
    duplicate_attributes = reserved_output_columns.intersection(event_attribute_columns)
    if duplicate_attributes:
        raise ValueError(
            "Event attribute columns collide with reserved OCEL2 CSV columns: %s."
            % ", ".join(sorted(str(value) for value in duplicate_attributes))
        )

    object_type = (
        ocel.objects[[object_id_column, object_type_column]]
        .drop_duplicates(subset=[object_id_column])
        .set_index(object_id_column)[object_type_column]
        .to_dict()
    )
    object_records = ocel.objects.to_dict("records")
    for record in object_records:
        if _is_null(record.get(object_id_column)) or _is_null(record.get(object_type_column)):
            raise ValueError("OCEL2 CSV objects must have non-empty ids and types.")
        _validate_reference_part(record[object_id_column], "object id")

    object_attrs = {}
    for record in object_records:
        attrs = {}
        for column in object_attribute_columns:
            value = record.get(column)
            if not _is_null(value):
                attrs[column] = value
        if attrs:
            object_attrs[record[object_id_column]] = attrs

    type_established_ids = set()
    event_relations = {}
    relation_columns = [
        event_id_column,
        object_id_column,
        object_type_column,
        qualifier_column,
    ]
    event_ids = set(ocel.events[event_id_column].tolist())
    relation_keys = set()
    for event_id, object_id, relation_object_type, qualifier in ocel.relations[
        relation_columns
    ].itertuples(index=False, name=None):
        if event_id not in event_ids:
            raise ValueError("Relation references unknown event '%s'." % event_id)
        known_object_type = object_type.get(object_id)
        if _is_null(known_object_type):
            raise ValueError("Relation references unknown object '%s'." % object_id)
        if not _is_null(relation_object_type) and str(relation_object_type) != str(known_object_type):
            raise ValueError(
                "Relation object type for '%s' does not match the object table." % object_id
            )
        relation_key = (event_id, object_id, "" if _is_null(qualifier) else str(qualifier))
        if relation_key in relation_keys:
            raise ValueError("Duplicate event-to-object relation cannot be exported.")
        relation_keys.add(relation_key)
        event_relations.setdefault(event_id, []).append(
            (object_id, known_object_type, qualifier)
        )

    timed_change_groups = {}
    epoch = pd.Timestamp("1970-01-01T00:00:00Z")
    for change_index, record in enumerate(ocel.object_changes.to_dict("records")):
        oid = record.get(object_id_column)
        known_type = object_type.get(oid)
        record_type = record.get(object_type_column, known_type)
        timestamp = record.get(event_timestamp_column)
        changed_attr = record.get(changed_field_column)
        if _is_null(oid) or _is_null(known_type):
            raise ValueError("Object change references an unknown object.")
        if not _is_null(record_type) and str(record_type) != str(known_type):
            raise ValueError("Object change type does not match object '%s'." % oid)
        if _is_null(timestamp) or _is_null(changed_attr):
            raise ValueError("Object changes require a timestamp and changed field.")
        if changed_attr not in record or _is_null(record.get(changed_attr)):
            raise ValueError(
                "Object change for '%s' does not contain a value in column '%s'."
                % (oid, changed_attr)
            )
        value = record.get(changed_attr)
        normalized_timestamp = _timestamp_value(timestamp)
        if normalized_timestamp == epoch:
            existing = object_attrs.setdefault(oid, {}).get(changed_attr)
            if existing is not None and not _values_equal(existing, value):
                raise ValueError(
                    "Object '%s' has conflicting time-0 values for attribute '%s'."
                    % (oid, changed_attr)
                )
            object_attrs[oid][changed_attr] = value
            continue
        key = (normalized_timestamp.value, str(known_type), oid)
        group = timed_change_groups.setdefault(
            key,
            {
                "timestamp": normalized_timestamp,
                "object_type": str(known_type),
                "object_id": oid,
                "first_index": change_index,
                "attributes": {},
            },
        )
        existing = group["attributes"].get(changed_attr)
        if existing is not None and not _values_equal(existing, value):
            raise ValueError(
                "Object '%s' has conflicting values for attribute '%s' at %s."
                % (oid, changed_attr, normalized_timestamp.isoformat())
            )
        group["attributes"][changed_attr] = value

    header = (
        [csv_event_id, csv_event_activity, csv_event_timestamp]
        + object_type_columns
        + event_attribute_columns
    )
    header_index = {column: index for index, column in enumerate(header)}
    object_type_column_index = {
        object_type: header_index[object_type_prefix + object_type]
        for object_type in object_types
    }
    rows = []
    header_len = len(header)

    event_records = list(enumerate(ocel.events.to_dict("records")))
    event_records = sorted(
        event_records,
        key=lambda item: (_timestamp_sort_key(item[1][event_timestamp_column]), item[0]),
    )

    for _, event in event_records:
        row = _new_row(header_len)
        event_id = _require_trimmed(event[event_id_column], "event id")
        event_activity = _require_trimmed(
            event[event_activity_column], "event activity"
        )
        if event_activity.casefold() == str(o2o_activity).casefold():
            raise ValueError("An event type named 'o2o' is not representable in OCEL2 CSV.")
        row[header_index[csv_event_id]] = event_id
        row[header_index[csv_event_activity]] = event_activity
        row[header_index[csv_event_timestamp]] = _format_timestamp(event[event_timestamp_column])

        for column in event_attribute_columns:
            value = event.get(column)
            if not _is_null(value):
                row[header_index[column]] = clean_dataframes.normalize_value(value)

        entries = {object_type: [] for object_type in object_types}
        for oid, ot, qualifier in event_relations.get(event_id, []):
            if _is_null(ot):
                ot = object_type.get(oid)
            if _is_null(ot):
                raise ValueError(
                    "Cannot export OCEL2 CSV relation for object '%s' without an object type."
                    % oid
                )
            type_established_ids.add(oid)
            entries.setdefault(str(ot), []).append(
                _format_reference(oid, qualifier)
            )

        for ot, values in entries.items():
            if values:
                row[object_type_column_index[ot]] = "/".join(values)
        rows.append(row)

    declaration_records = sorted(
        object_records,
        key=lambda record: (
            str(record[object_type_column]),
            _reference_sort_value(record[object_id_column]),
        ),
    )
    for record in declaration_records:
        oid = record[object_id_column]
        attrs = object_attrs.get(oid, {})
        if oid in type_established_ids and not attrs:
            continue
        ot = str(record[object_type_column])
        row = _new_row(header_len)
        row[object_type_column_index[ot]] = _format_reference(oid, attrs=attrs)
        rows.append(row)

    o2o_entries = {}
    o2o_columns = [object_id_column, object_id_column + "_2", qualifier_column]
    o2o_keys = set()
    for source_id, target_id, qualifier in ocel.o2o[o2o_columns].itertuples(
        index=False, name=None
    ):
        source_type = object_type.get(source_id)
        target_type = object_type.get(target_id)
        if _is_null(source_id) or _is_null(source_type):
            raise ValueError(
                "Cannot export OCEL2 CSV object-to-object source '%s' without an object type."
                % source_id
            )
        if _is_null(target_id) or _is_null(target_type):
            raise ValueError(
                "Cannot export OCEL2 CSV object-to-object target '%s' without an object type."
                % target_id
            )
        o2o_key = (source_id, target_id, "" if _is_null(qualifier) else str(qualifier))
        if o2o_key in o2o_keys:
            raise ValueError("Duplicate object-to-object relation cannot be exported.")
        o2o_keys.add(o2o_key)
        o2o_entries.setdefault(source_id, {}).setdefault(str(target_type), []).append(
            _format_reference(target_id, qualifier)
        )

    for source_id in sorted(o2o_entries, key=_reference_sort_value):
        entries = o2o_entries[source_id]
        row = _new_row(header_len)
        row[header_index[csv_event_id]] = source_id
        row[header_index[csv_event_activity]] = o2o_activity
        for ot in sorted(entries):
            row[object_type_column_index[ot]] = "/".join(sorted(entries[ot]))
        rows.append(row)

    change_groups = sorted(
        timed_change_groups.values(),
        key=lambda group: (group["timestamp"].value, group["first_index"]),
    )
    for group in change_groups:
        row = _new_row(header_len)
        row[header_index[csv_event_timestamp]] = _format_timestamp(group["timestamp"])
        row[object_type_column_index[group["object_type"]]] = _format_reference(
            group["object_id"], attrs=group["attributes"]
        )
        rows.append(row)

    dataframe = pandas_utils.instantiate_dataframe(rows, columns=header)
    dataframe.to_csv(
        output_path,
        index=False,
        na_rep="",
        encoding=encoding,
        lineterminator="\r\n",
    )

    if objects_path is not None:
        ocel.objects.to_csv(objects_path, index=False, na_rep="", encoding=encoding)
