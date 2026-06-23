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
Token-replay trace encoding.

From an event-log point of view, each trace is replayed on a Petri net and
the replay diagnostics become the trace vector. The vector contains:
is-fit, fitness, missing tokens, consumed tokens, remaining tokens, and
produced tokens.

Example with a model A -> B -> C:
    case 1: A, B, C
    case 2: A, C

case 1 can be replayed without adding or leaving tokens, so it receives a
fit vector such as [1, 1.0, 0, consumed, 0, produced]. case 2 skips B, so
token replay has to add or compensate for tokens and the missing-token
count and fitness reflect that deviation.

The Petri net can be passed with net, initial_marking, and final_marking. If
no model is passed, the variant discovers one from the log using PM4Py's
Inductive Miner.

Reference:
Tavares, G. M., Oyamada, R. S., Barbon Junior, S., and Ceravolo, P.
"Trace encoding in process mining: A survey and benchmarking."
Engineering Applications of Artificial Intelligence, 126, 107028, 2023.
https://doi.org/10.1016/j.engappai.2023.107028

The survey lists token-replay as a PM-based encoding and points to PM4Py as
the maintained implementation. This variant delegates replay computation to
PM4Py's token replay and exposes per-trace replay diagnostics as vectors.
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
    TOKEN_REPLAY_VARIANT = "token_replay_variant"


FEATURE_NAMES = [
    "@@token_replay_is_fit",
    "@@token_replay_fitness",
    "@@token_replay_missing_tokens",
    "@@token_replay_consumed_tokens",
    "@@token_replay_remaining_tokens",
    "@@token_replay_produced_tokens",
]


def apply(
    log: Union[EventLog, EventStream, pd.DataFrame],
    parameters: Optional[Dict[Any, Any]] = None,
):
    """
    Encodes each trace with token-replay conformance diagnostics.

    Parameters
    ----------
    log
        Event log, event stream, or dataframe containing traces.
    parameters
        Parameters of the encoding. Common options:
        - NET/PETRI_NET, INITIAL_MARKING, FINAL_MARKING: existing Petri net
          model to replay on.
        - DISCOVER_MODEL: if True, discover a Petri net when no model is
          supplied.
        - TOKEN_REPLAY_VARIANT: PM4Py token replay variant.

    Returns
    -------
    data
        One row per trace with token-replay diagnostics.
    feature_names
        Diagnostic names corresponding to the columns of data.
    """
    if parameters is None:
        parameters = {}

    from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
    from pm4py.util import exec_utils

    event_log, net, initial_marking, final_marking = petri_net.get_log_and_model(
        log, parameters=parameters
    )
    variant = exec_utils.get_param_value(
        Parameters.TOKEN_REPLAY_VARIANT,
        parameters,
        token_replay.DEFAULT_VARIANT,
    )

    replayed_traces = token_replay.apply(
        event_log,
        net,
        initial_marking,
        final_marking,
        parameters=parameters,
        variant=variant,
    )

    data = []
    for replayed_trace in replayed_traces:
        data.append(
            [
                1.0 if replayed_trace.get("trace_is_fit", False) else 0.0,
                float(replayed_trace.get("trace_fitness", 0.0)),
                float(replayed_trace.get("missing_tokens", 0.0)),
                float(replayed_trace.get("consumed_tokens", 0.0)),
                float(replayed_trace.get("remaining_tokens", 0.0)),
                float(replayed_trace.get("produced_tokens", 0.0)),
            ]
        )

    return data, FEATURE_NAMES
