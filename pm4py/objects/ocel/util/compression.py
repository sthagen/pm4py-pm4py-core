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
import gzip
import os
import shutil
import tempfile
from contextlib import contextmanager


def is_gzip_path(file_path: str) -> bool:
    return str(file_path).lower().endswith(".gz")


def open_text(file_path: str, mode: str, encoding: str):
    if is_gzip_path(file_path):
        return gzip.open(file_path, mode=mode, encoding=encoding)
    return open(file_path, mode=mode, encoding=encoding)


def open_binary(file_path: str, mode: str):
    if is_gzip_path(file_path):
        return gzip.open(file_path, mode=mode)
    return open(file_path, mode=mode)


def get_uncompressed_suffix(file_path: str) -> str:
    path = str(file_path)
    if is_gzip_path(path):
        path = path[:-3]
    _, suffix = os.path.splitext(path)
    return suffix or ".tmp"


@contextmanager
def decompressed_path(file_path: str):
    if not is_gzip_path(file_path):
        yield file_path
        return

    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=get_uncompressed_suffix(file_path)
    )
    tmp.close()

    try:
        with gzip.open(file_path, "rb") as source:
            with open(tmp.name, "wb") as target:
                shutil.copyfileobj(source, target)
        yield tmp.name
    finally:
        os.remove(tmp.name)
