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
import importlib
import importlib.util
from typing import Any, Optional, Tuple


def _has_module(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


def get_rustxes_backend_name() -> Optional[str]:
    if _has_module("r4pm.df"):
        return "r4pm"
    if _has_module("rustxes"):
        return "rustxes"
    return None


def import_rustxes_backend() -> Tuple[Any, str]:
    backend_name = get_rustxes_backend_name()
    if backend_name == "r4pm":
        return importlib.import_module("r4pm.df"), backend_name
    if backend_name == "rustxes":
        return importlib.import_module("rustxes"), backend_name
    raise ImportError("Neither `r4pm` nor `rustxes` is installed.")
