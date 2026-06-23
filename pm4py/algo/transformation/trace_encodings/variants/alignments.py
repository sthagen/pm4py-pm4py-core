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
"""
Alignment-based trace encoding.

From an event-log point of view, each trace is aligned with a Petri net. The
alignment finds a least-cost explanation of how the trace can be matched to
the model through synchronous moves, log moves, and model moves. The
alignment diagnostics become the trace vector: is-fit, fitness, cost,
best-worst cost, visited states, queued states, and traversed arcs.

Example with a model A -> B -> C:
    case 1: A, B, C
    case 2: A, C

case 1 aligns synchronously with the model and receives zero alignment cost.
case 2 needs a model move for B or a related deviation, so its cost is
greater than zero and its fitness is lower.

The Petri net can be passed with net, initial_marking, and final_marking. If
no model is passed, the variant discovers one from the log using PM4Py's
Inductive Miner.

Reference:
Tavares, G. M., Oyamada, R. S., Barbon Junior, S., and Ceravolo, P.
"Trace encoding in process mining: A survey and benchmarking."
Engineering Applications of Artificial Intelligence, 126, 107028, 2023.
https://doi.org/10.1016/j.engappai.2023.107028

The survey lists alignments as a PM-based encoding and points to PM4Py as the
maintained implementation. This variant delegates alignment computation to
PM4Py's Petri-net alignments and exposes per-trace diagnostics as vectors.
"""

from enum import Enum
from typing import Any, Dict, Optional, Union

import pandas as pd

from pm4py.objects.log.obj import EventLog, EventStream
from pm4py.algo.transformation.trace_encodings.util import petri_net


class Parameters(Enum):
    NET = "net"
    PETRI_NET = "petri_net"
    INITIAL_MARKING = "initial_marking"
    FINAL_MARKING = "final_marking"
    DISCOVER_MODEL = "discover_model"
    ALIGNMENT_VARIANT = "alignment_variant"


FEATURE_NAMES = [
    "@@alignment_is_fit",
    "@@alignment_fitness",
    "@@alignment_cost",
    "@@alignment_bwc",
    "@@alignment_visited_states",
    "@@alignment_queued_states",
    "@@alignment_traversed_arcs",
]


def apply(
    log: Union[EventLog, EventStream, pd.DataFrame],
    parameters: Optional[Dict[Any, Any]] = None,
):
    """
    Encodes each trace with alignment conformance diagnostics.

    Parameters
    ----------
    log
        Event log, event stream, or dataframe containing traces.
    parameters
        Parameters of the encoding. Common options:
        - NET/PETRI_NET, INITIAL_MARKING, FINAL_MARKING: existing Petri net
          model to align against.
        - DISCOVER_MODEL: if True, discover a Petri net when no model is
          supplied.
        - ALIGNMENT_VARIANT: PM4Py Petri-net alignment variant.

    Returns
    -------
    data
        One row per trace with alignment diagnostics.
    feature_names
        Diagnostic names corresponding to the columns of data.
    """
    if parameters is None:
        parameters = {}

    from pm4py.algo.conformance.alignments.petri_net import (
        algorithm as alignments,
    )
    from pm4py.util import exec_utils

    event_log, net, initial_marking, final_marking = petri_net.get_log_and_model(
        log, parameters=parameters
    )
    variant = exec_utils.get_param_value(
        Parameters.ALIGNMENT_VARIANT,
        parameters,
        alignments.DEFAULT_VARIANT,
    )

    alignment_results = alignments.apply(
        event_log,
        net,
        initial_marking,
        final_marking,
        parameters=parameters,
        variant=variant,
    )

    data = []
    for alignment in alignment_results:
        if alignment is None:
            data.append([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        else:
            fitness = float(alignment.get("fitness", 0.0))
            data.append(
                [
                    1.0 if fitness == 1.0 else 0.0,
                    fitness,
                    float(alignment.get("cost", 0.0)),
                    float(alignment.get("bwc", 0.0)),
                    float(alignment.get("visited_states", 0.0)),
                    float(alignment.get("queued_states", 0.0)),
                    float(alignment.get("traversed_arcs", 0.0)),
                ]
            )

    return data, FEATURE_NAMES
