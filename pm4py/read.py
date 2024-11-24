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
from typing import Tuple, Dict, Optional

from pm4py.objects.bpmn.obj import BPMN
from pm4py.objects.log.obj import EventLog
from pm4py.objects.ocel.obj import OCEL
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.process_tree.obj import ProcessTree
from pm4py.util import constants

import os

from pandas import DataFrame
from typing import Union

INDEX_COLUMN = "@@index"

__doc__ = """
The `pm4py.read` module contains all functionality related to reading files and objects from disk.
"""


def read_xes(
    file_path: str,
    variant: Optional[str] = None,
    return_legacy_log_object: bool = constants.DEFAULT_READ_XES_LEGACY_OBJECT,
    encoding: str = constants.DEFAULT_ENCODING,
    **kwargs
) -> Union[DataFrame, EventLog]:
    """
    Reads an event log stored in XES format (see `xes-standard <https://xes-standard.org/>`_).
    Returns a table (`pandas.DataFrame`) view of the event log or an `EventLog` object.

    :param file_path: Path to the event log (`.xes` file) on disk.
    :param variant: Variant of the importer to use. Options include:
        - "iterparse" – traditional XML parser,
        - "line_by_line" – text-based line-by-line importer,
        - "chunk_regex" – chunk-of-bytes importer (default),
        - "iterparse20" – XES 2.0 importer,
        - "rustxes" – Rust-based importer.
    :param return_legacy_log_object: Boolean indicating whether to return a legacy `EventLog` object (default: `False`).
    :param encoding: Encoding to be used (default: `utf-8`).
    :param **kwargs: Additional parameters to pass to the importer.
    :rtype: `pandas.DataFrame` or `pm4py.objects.log.obj.EventLog`

    .. code-block:: python3

        import pm4py

        log = pm4py.read_xes("<path_to_xes_file>")
    """
    if not os.path.exists(file_path):
        raise Exception("File does not exist")

    if variant is None:
        variant = constants.DEFAULT_XES_PARSER

    from pm4py.objects.log.importer.xes import importer as xes_importer

    v = xes_importer.Variants.CHUNK_REGEX
    if variant == "iterparse_20":
        v = xes_importer.Variants.ITERPARSE_20
    elif variant == "iterparse":
        v = xes_importer.Variants.ITERPARSE
    elif variant == "lxml":
        v = xes_importer.Variants.ITERPARSE
    elif variant == "iterparse_mem_compressed":
        v = xes_importer.Variants.ITERPARSE_MEM_COMPRESSED
    elif variant == "line_by_line":
        v = xes_importer.Variants.LINE_BY_LINE
    elif variant == "chunk_regex":
        v = xes_importer.Variants.CHUNK_REGEX
    elif variant == "rustxes":
        v = xes_importer.Variants.RUSTXES

    from copy import copy
    parameters = copy(kwargs)
    parameters["encoding"] = encoding
    parameters["return_legacy_log_object"] = return_legacy_log_object

    log = xes_importer.apply(file_path, variant=v, parameters=parameters)

    if type(log) is EventLog and not return_legacy_log_object:
        from pm4py.objects.conversion.log import converter as log_converter
        log = log_converter.apply(log, variant=log_converter.Variants.TO_DATA_FRAME)

    return log


def read_pnml(
    file_path: str,
    auto_guess_final_marking: bool = False,
    encoding: str = constants.DEFAULT_ENCODING
) -> Tuple[PetriNet, Marking, Marking]:
    """
    Reads a Petri net object from a `.pnml` file.
    The returned Petri net object is a tuple containing:
    
    1. PetriNet object (`PetriNet`)
    2. Initial Marking (`Marking`)
    3. Final Marking (`Marking`)

    :param file_path: Path to the Petri net model (`.pnml` file) on disk.
    :param auto_guess_final_marking: Boolean indicating whether to automatically guess the final marking (default: `False`).
    :param encoding: Encoding to be used (default: `utf-8`).
    :rtype: `Tuple[PetriNet, Marking, Marking]`

    .. code-block:: python3

        import pm4py

        pn = pm4py.read_pnml("<path_to_pnml_file>")
    """
    if not os.path.exists(file_path):
        raise Exception("File does not exist")
    from pm4py.objects.petri_net.importer import importer as pnml_importer
    net, im, fm = pnml_importer.apply(
        file_path,
        parameters={
            "auto_guess_final_marking": auto_guess_final_marking,
            "encoding": encoding
        }
    )
    return net, im, fm


def read_ptml(file_path: str, encoding: str = constants.DEFAULT_ENCODING) -> ProcessTree:
    """
    Reads a process tree object from a `.ptml` file.

    :param file_path: Path to the process tree file on disk.
    :param encoding: Encoding to be used (default: `utf-8`).
    :rtype: `ProcessTree`

    .. code-block:: python3

        import pm4py

        process_tree = pm4py.read_ptml("<path_to_ptml_file>")
    """
    if not os.path.exists(file_path):
        raise Exception("File does not exist")
    from pm4py.objects.process_tree.importer import importer as tree_importer
    tree = tree_importer.apply(file_path, parameters={"encoding": encoding})
    return tree


def read_dfg(
    file_path: str,
    encoding: str = constants.DEFAULT_ENCODING
) -> Tuple[Dict[Tuple[str, str], int], Dict[str, int], Dict[str, int]]:
    """
    Reads a Directly-Follows Graph (DFG) from a `.dfg` file.
    The returned DFG object is a tuple containing:
    
    1. DFG (`Dict[Tuple[str, str], int]`): Maps pairs of activities to their occurrence count. 
       For example, `DFG[('a', 'b')] = k` indicates that activity `'a'` is directly followed by activity `'b'` a total of `k` times in the log.
    2. Start Activity Dictionary (`Dict[str, int]`): Maps activities to the number of traces they start. 
       For example, `S['a'] = k` implies that activity `'a'` starts `k` traces in the event log.
    3. End Activity Dictionary (`Dict[str, int]`): Maps activities to the number of traces they end. 
       For example, `E['z'] = k` implies that activity `'z'` ends `k` traces in the event log.

    :param file_path: Path to the DFG model file on disk.
    :param encoding: Encoding to be used (default: `utf-8`).
    :rtype: `Tuple[Dict[Tuple[str, str], int], Dict[str, int], Dict[str, int]]`

    .. code-block:: python3

        import pm4py

        dfg = pm4py.read_dfg("<path_to_dfg_file>")
    """
    if not os.path.exists(file_path):
        raise Exception("File does not exist")
    from pm4py.objects.dfg.importer import importer as dfg_importer
    dfg, start_activities, end_activities = dfg_importer.apply(
        file_path, parameters={"encoding": encoding}
    )
    return dfg, start_activities, end_activities


def read_bpmn(file_path: str, encoding: str = constants.DEFAULT_ENCODING) -> BPMN:
    """
    Reads a BPMN model from a `.bpmn` file.

    :param file_path: Path to the BPMN model file on disk.
    :param encoding: Encoding to be used (default: `utf-8`).
    :rtype: `BPMN`

    .. code-block:: python3

        import pm4py

        bpmn = pm4py.read_bpmn('<path_to_bpmn_file>')
    """
    if not os.path.exists(file_path):
        raise Exception("File does not exist")
    from pm4py.objects.bpmn.importer import importer as bpmn_importer
    bpmn_graph = bpmn_importer.apply(file_path, parameters={"encoding": encoding})
    return bpmn_graph


def read_ocel(
    file_path: str,
    objects_path: Optional[str] = None,
    encoding: str = constants.DEFAULT_ENCODING
) -> OCEL:
    """
    Reads an object-centric event log from a file (see: http://www.ocel-standard.org/).
    Returns an `OCEL` object.

    :param file_path: Path to the object-centric event log file.
    :param objects_path: [Optional] Path to the objects dataframe file.
    :param encoding: Encoding to be used (default: `utf-8`).
    :rtype: `OCEL`

    .. code-block:: python3

        import pm4py

        ocel = pm4py.read_ocel("<path_to_ocel_file>")
    """
    if not os.path.exists(file_path):
        raise Exception("File does not exist")
    if file_path.lower().endswith("csv"):
        return read_ocel_csv(file_path, objects_path, encoding=encoding)
    elif file_path.lower().endswith("jsonocel"):
        return read_ocel_json(file_path, encoding=encoding)
    elif file_path.lower().endswith("xmlocel"):
        return read_ocel_xml(file_path, encoding=encoding)
    elif file_path.lower().endswith(".sqlite"):
        return read_ocel_sqlite(file_path, encoding=encoding)
    raise Exception("Unsupported file format")


def read_ocel_csv(
    file_path: str,
    objects_path: Optional[str] = None,
    encoding: str = constants.DEFAULT_ENCODING
) -> OCEL:
    """
    Reads an object-centric event log from a CSV file (see: http://www.ocel-standard.org/).
    Returns an `OCEL` object.

    :param file_path: Path to the object-centric event log file (`.csv`).
    :param objects_path: [Optional] Path to the objects dataframe file.
    :param encoding: Encoding to be used (default: `utf-8`).
    :rtype: `OCEL`

    .. code-block:: python3

        import pm4py

        ocel = pm4py.read_ocel_csv("<path_to_ocel_file.csv>")
    """
    if not os.path.exists(file_path):
        raise Exception("File does not exist")

    from pm4py.objects.ocel.importer.csv import importer as csv_importer
    return csv_importer.apply(
        file_path,
        objects_path=objects_path,
        parameters={"encoding": encoding}
    )


def read_ocel_json(file_path: str, encoding: str = constants.DEFAULT_ENCODING) -> OCEL:
    """
    Reads an object-centric event log from a JSON-OCEL file (see: http://www.ocel-standard.org/).
    Returns an `OCEL` object.

    :param file_path: Path to the object-centric event log file (`.jsonocel`).
    :param encoding: Encoding to be used (default: `utf-8`).
    :rtype: `OCEL`

    .. code-block:: python3

        import pm4py

        ocel = pm4py.read_ocel_json("<path_to_ocel_file.jsonocel>")
    """
    if not os.path.exists(file_path):
        raise Exception("File does not exist")

    from pm4py.objects.ocel.importer.jsonocel import importer as jsonocel_importer
    return jsonocel_importer.apply(
        file_path,
        variant=jsonocel_importer.Variants.CLASSIC,
        parameters={"encoding": encoding}
    )


def read_ocel_xml(file_path: str, encoding: str = constants.DEFAULT_ENCODING) -> OCEL:
    """
    Reads an object-centric event log from an XML-OCEL file (see: http://www.ocel-standard.org/).
    Returns an `OCEL` object.

    :param file_path: Path to the object-centric event log file (`.xmlocel`).
    :param encoding: Encoding to be used (default: `utf-8`).
    :rtype: `OCEL`

    .. code-block:: python3

        import pm4py

        ocel = pm4py.read_ocel_xml("<path_to_ocel_file.xmlocel>")
    """
    if not os.path.exists(file_path):
        raise Exception("File does not exist")

    from pm4py.objects.ocel.importer.xmlocel import importer as xmlocel_importer
    return xmlocel_importer.apply(
        file_path,
        variant=xmlocel_importer.Variants.CLASSIC,
        parameters={"encoding": encoding}
    )


def read_ocel_sqlite(file_path: str, encoding: str = constants.DEFAULT_ENCODING) -> OCEL:
    """
    Reads an object-centric event log from a SQLite database (see: http://www.ocel-standard.org/).
    Returns an `OCEL` object.

    :param file_path: Path to the SQLite database file (`.sqlite`).
    :param encoding: Encoding to be used (default: `utf-8`).
    :rtype: `OCEL`

    .. code-block:: python3

        import pm4py

        ocel = pm4py.read_ocel_sqlite("<path_to_ocel_file.sqlite>")
    """
    if not os.path.exists(file_path):
        raise Exception("File does not exist")

    from pm4py.objects.ocel.importer.sqlite import importer as sqlite_importer
    return sqlite_importer.apply(
        file_path,
        variant=sqlite_importer.Variants.PANDAS_IMPORTER,
        parameters={"encoding": encoding}
    )


def read_ocel2(
    file_path: str,
    variant_str: Optional[str] = None,
    encoding: str = constants.DEFAULT_ENCODING
) -> OCEL:
    """
    Reads an OCEL 2.0 event log.

    :param file_path: Path to the OCEL 2.0 event log file.
    :param variant_str: [Optional] Specification of the importer variant to be used.
    :param encoding: Encoding to be used (default: `utf-8`).
    :rtype: `OCEL`

    Supported file formats based on extension:
        - `.sqlite` – SQLite database,
        - `.xml` or `.xmlocel` – XML file,
        - `.json` or `.jsonocel` – JSON file.

    .. code-block:: python3

        import pm4py

        ocel = pm4py.read_ocel2("<path_to_ocel_file>")
    """
    if not os.path.exists(file_path):
        raise Exception("File does not exist")

    if file_path.lower().endswith("sqlite"):
        return read_ocel2_sqlite(file_path, variant_str=variant_str, encoding=encoding)
    elif file_path.lower().endswith("xml") or file_path.lower().endswith("xmlocel"):
        return read_ocel2_xml(file_path, variant_str=variant_str, encoding=encoding)
    elif file_path.lower().endswith("json") or file_path.lower().endswith("jsonocel"):
        return read_ocel2_json(file_path, variant_str=variant_str, encoding=encoding)


def read_ocel2_json(
    file_path: str,
    variant_str: Optional[str] = None,
    encoding: str = constants.DEFAULT_ENCODING
) -> OCEL:
    """
    Reads an OCEL 2.0 event log from a JSON-OCEL2 file.

    :param file_path: Path to the JSON file (`.jsonocel`).
    :param variant_str: [Optional] Specification of the importer variant to be used.
    :param encoding: Encoding to be used (default: `utf-8`).
    :rtype: `OCEL`

    .. code-block:: python3

        import pm4py

        ocel = pm4py.read_ocel2_json("<path_to_ocel_file.jsonocel>")
    """
    if not os.path.exists(file_path):
        raise Exception("File does not exist")

    from pm4py.objects.ocel.importer.jsonocel import importer as jsonocel_importer
    variant = jsonocel_importer.Variants.OCEL20_STANDARD
    if variant_str == "ocel20_rustxes":
        variant = jsonocel_importer.Variants.OCEL20_RUSTXES

    return jsonocel_importer.apply(
        file_path,
        variant=variant,
        parameters={"encoding": encoding}
    )


def read_ocel2_sqlite(
    file_path: str,
    variant_str: Optional[str] = None,
    encoding: str = constants.DEFAULT_ENCODING
) -> OCEL:
    """
    Reads an OCEL 2.0 event log from a SQLite database.

    :param file_path: Path to the OCEL 2.0 SQLite database file (`.sqlite`).
    :param variant_str: [Optional] Specification of the importer variant to be used.
    :param encoding: Encoding to be used (default: `utf-8`).
    :rtype: `OCEL`

    .. code-block:: python3

        import pm4py

        ocel = pm4py.read_ocel2_sqlite("<path_to_ocel_file.sqlite>")
    """
    if not os.path.exists(file_path):
        raise Exception("File does not exist")

    from pm4py.objects.ocel.importer.sqlite import importer as sqlite_importer
    return sqlite_importer.apply(
        file_path,
        variant=sqlite_importer.Variants.OCEL20,
        parameters={"encoding": encoding}
    )


def read_ocel2_xml(
    file_path: str,
    variant_str: Optional[str] = None,
    encoding: str = constants.DEFAULT_ENCODING
) -> OCEL:
    """
    Reads an OCEL 2.0 event log from an XML file.

    :param file_path: Path to the OCEL 2.0 XML file (`.xmlocel`).
    :param variant_str: [Optional] Specification of the importer variant to be used.
    :param encoding: Encoding to be used (default: `utf-8`).
    :rtype: `OCEL`

    .. code-block:: python3

        import pm4py

        ocel = pm4py.read_ocel2_xml("<path_to_ocel_file.xmlocel>")
    """
    if not os.path.exists(file_path):
        raise Exception("File does not exist")

    from pm4py.objects.ocel.importer.xmlocel import importer as xml_importer
    variant = xml_importer.Variants.OCEL20
    if variant_str == "ocel20_rustxes":
        variant = xml_importer.Variants.OCEL20_RUSTXES

    return xml_importer.apply(
        file_path,
        variant=variant,
        parameters={"encoding": encoding}
    )
