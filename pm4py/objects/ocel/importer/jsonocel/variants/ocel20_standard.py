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
from pm4py.util import exec_utils, dt_parsing
from pm4py.objects.ocel.obj import OCEL
from typing import Optional, Dict, Any
from pm4py.objects.ocel.util import filtering_utils
from pm4py.objects.ocel.util import ocel_consistency
from pm4py.objects.ocel.importer.jsonocel.variants import classic
from pm4py.util import constants as pm4_constants
from enum import Enum
import json


class Parameters(Enum):
    ENCODING = "encoding"


def _parse_attr_value(value, attr_type, parser):
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() == "null":
        return None

    attr_type = "" if attr_type is None else str(attr_type).lower()
    if "date" in attr_type or "time" in attr_type:
        try:
            return parser.apply(value)
        except BaseException:
            from dateutil.parser import parse

            try:
                return parse(value)
            except BaseException:
                return value
    if "float" in attr_type or "double" in attr_type:
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    if "int" in attr_type:
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    if "bool" in attr_type:
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ("true", "false"):
                return lowered == "true"
        return bool(value)
    return value


def apply(file_path: str, parameters: Optional[Dict[Any, Any]] = None) -> OCEL:
    """
    Imports an OCEL from a JSON-OCEL 2 standard file

    Parameters
    --------------
    file_path
        Path to the object-centric event log
    parameters
        Possible parameters of the method, including:
        - Parameters.ENCODING

    Returns
    -------------
    ocel
        Object-centric event log
    """
    if parameters is None:
        parameters = {}

    encoding = exec_utils.get_param_value(
        Parameters.ENCODING, parameters, pm4_constants.DEFAULT_ENCODING
    )

    F = open(file_path, "r", encoding=encoding)
    json_obj = json.load(F)
    F.close()

    event_attr_types = {}
    for et in json_obj.get("eventTypes", []):
        event_attr_types[et["name"]] = {
            x["name"]: x["type"] for x in et.get("attributes", [])
        }

    object_attr_types = {}
    for ot in json_obj.get("objectTypes", []):
        object_attr_types[ot["name"]] = {
            x["name"]: x["type"] for x in ot.get("attributes", [])
        }

    parser = dt_parsing.parser.get()

    legacy_obj = {}
    legacy_obj["ocel:events"] = {}
    legacy_obj["ocel:objects"] = {}
    legacy_obj["ocel:objectChanges"] = []

    for eve in json_obj["events"]:
        dct = {}
        dct["ocel:activity"] = eve["type"]
        dct["ocel:timestamp"] = eve["time"]
        dct["ocel:vmap"] = {}
        if "attributes" in eve and eve["attributes"]:
            type_map = event_attr_types.get(eve["type"], {})
            dct["ocel:vmap"] = {
                x["name"]: _parse_attr_value(
                    x["value"], type_map.get(x["name"]), parser
                )
                for x in eve["attributes"]
            }
        dct["ocel:typedOmap"] = []
        if "relationships" in eve and eve["relationships"]:
            dct["ocel:typedOmap"] = [
                {"ocel:oid": x["objectId"], "ocel:qualifier": x["qualifier"]}
                for x in eve["relationships"]
            ]
        dct["ocel:omap"] = list(
            set(x["ocel:oid"] for x in dct["ocel:typedOmap"])
        )
        legacy_obj["ocel:events"][eve["id"]] = dct

    for obj in json_obj["objects"]:
        dct = {}
        dct["ocel:type"] = obj["type"]
        dct["ocel:ovmap"] = {}
        if "attributes" in obj and obj["attributes"]:
            type_map = object_attr_types.get(obj["type"], {})
            attrs_by_name = {}
            for x in obj["attributes"]:
                value = _parse_attr_value(
                    x["value"], type_map.get(x["name"]), parser
                )
                time_raw = x.get("time")
                if time_raw is None:
                    time_key = None
                    time_val = None
                elif str(time_raw).startswith("1970-01-01T00:00:00") or str(
                    time_raw
                ) == "0":
                    time_key = None
                    time_val = time_raw
                else:
                    try:
                        time_val = parser.apply(time_raw)
                        time_key = time_val
                    except BaseException:
                        time_val = time_raw
                        time_key = time_raw
                attrs_by_name.setdefault(x["name"], []).append(
                    (time_key, time_val, value)
                )

            for name, entries in attrs_by_name.items():
                base_time_key, base_time_val, base_value = entries[0]
                dct["ocel:ovmap"][name] = base_value
                for time_key, time_val, value in entries[1:]:
                    legacy_obj["ocel:objectChanges"].append(
                        {
                            "ocel:oid": obj["id"],
                            "ocel:type": obj["type"],
                            "ocel:field": name,
                            name: value,
                            "ocel:timestamp": time_val,
                        }
                    )
        dct["ocel:o2o"] = []
        if "relationships" in obj and obj["relationships"]:
            dct["ocel:o2o"] = [
                {"ocel:oid": x["objectId"], "ocel:qualifier": x["qualifier"]}
                for x in obj["relationships"]
            ]
        legacy_obj["ocel:objects"][obj["id"]] = dct

    legacy_obj["ocel:global-log"] = {}
    legacy_obj["ocel:global-event"] = {}
    legacy_obj["ocel:global-object"] = {}

    log = classic.get_base_ocel(legacy_obj, parameters=parameters)

    log = ocel_consistency.apply(log, parameters=parameters)
    log = filtering_utils.propagate_relations_filtering(
        log, parameters=parameters
    )

    return log
