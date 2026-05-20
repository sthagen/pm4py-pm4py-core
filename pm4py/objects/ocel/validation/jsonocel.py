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
import importlib.util
from pm4py.objects.ocel.util import compression


def apply(input_path, validation_path, parameters=None):
    if not importlib.util.find_spec("jsonschema"):
        raise Exception(
            "please install jsonschema in order to validate a JSONOCEL file."
        )

    import json
    import jsonschema
    from jsonschema import validate

    if parameters is None:
        parameters = {}

    with compression.open_text(input_path, "rt", encoding="utf-8") as F:
        file_content = json.load(F)
    with open(validation_path, "rb") as F:
        schema_content = json.load(F)
    try:
        validate(instance=file_content, schema=schema_content)
        return True
    except jsonschema.exceptions.ValidationError as err:
        return False
