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
from pm4py.objects.ocel.exporter.jsonocel.variants import ocel20
from pm4py.objects.ocel.obj import OCEL
from typing import Optional, Dict, Any
from enum import Enum
import json
from pm4py.util import exec_utils, constants as pm4_constants
from pm4py.objects.ocel.exporter.util import clean_dataframes


class Parameters(Enum):
    ENCODING = "encoding"


def apply(
    ocel: OCEL, target_path: str, parameters: Optional[Dict[Any, Any]] = None
):
    """
    Exports an object-centric event log (OCEL 2.0) in a JSON-OCEL 2.0 standard file

    Parameters
    ------------------
    ocel
        Object-centric event log
    target_path
        Destination path
    parameters
        Possible parameters of the method, including:
        - Parameters.ENCODING
    """
    if parameters is None:
        parameters = {}

    encoding = exec_utils.get_param_value(
        Parameters.ENCODING, parameters, pm4_constants.DEFAULT_ENCODING
    )

    legacy_object = ocel20.get_enriched_object(ocel)

    json_object = {}
    json_object["objectTypes"] = []
    json_object["eventTypes"] = []
    json_object["objects"] = []
    json_object["events"] = []

    for ot, attrs in legacy_object["ocel:objectTypes"].items():
        descr = {
            "name": ot,
            "attributes": [{"name": x, "type": y} for x, y in attrs.items()],
        }
        json_object["objectTypes"].append(descr)

    for et, attrs in legacy_object["ocel:eventTypes"].items():
        descr = {
            "name": et,
            "attributes": [{"name": x, "type": y} for x, y in attrs.items()],
        }
        json_object["eventTypes"].append(descr)

    obj_idx = {}
    for objid, obj in legacy_object["ocel:objects"].items():
        descr = {}
        descr["id"] = objid
        descr["type"] = obj["ocel:type"]
        if "ocel:ovmap" in obj and obj["ocel:ovmap"]:
            descr["attributes"] = []
            for k, v in obj["ocel:ovmap"].items():
                norm_value = clean_dataframes.normalize_value(v)
                if clean_dataframes.is_null(norm_value):
                    continue
                descr["attributes"].append(
                    {
                        "name": k,
                        "time": "1970-01-01T00:00:00Z",
                        "value": norm_value,
                    }
                )
        if "ocel:o2o" in obj and obj["ocel:o2o"]:
            descr["relationships"] = []
            for v in obj["ocel:o2o"]:
                descr["relationships"].append(
                    {
                        "objectId": v["ocel:oid"],
                        "qualifier": v["ocel:qualifier"],
                    }
                )
        json_object["objects"].append(descr)
        obj_idx[objid] = len(obj_idx)

    eve_idx = {}
    for evid, eve in legacy_object["ocel:events"].items():
        descr = {}
        descr["id"] = evid
        descr["type"] = eve["ocel:activity"]
        descr["time"] = eve["ocel:timestamp"]
        if "ocel:vmap" in eve and eve["ocel:vmap"]:
            descr["attributes"] = []
            for k, v in eve["ocel:vmap"].items():
                norm_value = clean_dataframes.normalize_value(v)
                if clean_dataframes.is_null(norm_value):
                    continue
                descr["attributes"].append(
                    {"name": k, "value": norm_value}
                )
        if "ocel:typedOmap" in eve and eve["ocel:typedOmap"]:
            descr["relationships"] = []
            for v in eve["ocel:typedOmap"]:
                descr["relationships"].append(
                    {
                        "objectId": v["ocel:oid"],
                        "qualifier": v["ocel:qualifier"],
                    }
                )
        json_object["events"].append(descr)
        eve_idx[evid] = len(eve_idx)

    for change in legacy_object["ocel:objectChanges"]:
        field = change.get("ocel:field")
        if field is None or field not in change:
            continue
        oid = change["ocel:oid"]
        obj = json_object["objects"][obj_idx[oid]]

        norm_value = clean_dataframes.normalize_value(
            change[field]
        )
        if clean_dataframes.is_null(norm_value):
            continue
        obj.setdefault("attributes", []).append(
            {
                "name": field,
                "time": change["ocel:timestamp"],
                "value": norm_value,
            }
        )

        json_object["objects"][obj_idx[oid]] = obj

    F = open(target_path, "w", encoding=encoding)
    json.dump(json_object, F, indent=2)
    F.close()
