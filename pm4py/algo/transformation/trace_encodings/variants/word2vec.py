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
Trace-level Word2Vec encoding.

From an event-log point of view, each case is treated as a short sentence and
each event token is treated as a word. A Word2Vec model learns a vector for
each token from the neighboring tokens observed in the traces. A trace vector
is then obtained by aggregating the token vectors in that trace.

Example with activity tokens:
    case 1: A, B, C
    case 2: A, B, D

Word2Vec learns vectors for A, B, C, and D from their contexts. The trace
vector for case 1 is, by default, the mean of vectors A, B, and C.

Reference:
Tavares, G. M., Oyamada, R. S., Barbon Junior, S., and Ceravolo, P.
"Trace encoding in process mining: A survey and benchmarking."
Engineering Applications of Artificial Intelligence, 126, 107028, 2023.
https://doi.org/10.1016/j.engappai.2023.107028

This variant delegates model training/inference to gensim's maintained
Word2Vec implementation.
"""

from enum import Enum
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

from pm4py.objects.log.obj import EventLog, EventStream
from pm4py.algo.transformation.trace_encodings.util import trace_text
from pm4py.util import exec_utils


class Parameters(Enum):
    EVENT_ATTRIBUTES = "event_attributes"
    TRACE_ATTRIBUTES = "trace_attributes"
    MODEL = "model"
    VECTOR_SIZE = "vector_size"
    WINDOW = "window"
    MIN_COUNT = "min_count"
    WORKERS = "workers"
    EPOCHS = "epochs"
    SG = "sg"
    AGGREGATION = "aggregation"


def _aggregate(vectors, vector_size, aggregation):
    if not vectors:
        return [0.0] * vector_size

    matrix = np.asarray(vectors, dtype=float)
    if aggregation == "sum":
        return matrix.sum(axis=0).tolist()
    return matrix.mean(axis=0).tolist()


def apply(
    log: Union[EventLog, EventStream, pd.DataFrame],
    parameters: Optional[Dict[Any, Any]] = None,
):
    """
    Encodes each trace by aggregating gensim Word2Vec token vectors.

    Parameters
    ----------
    log
        Event log, event stream, or dataframe containing traces.
    parameters
        Parameters of the encoding. Common options:
        - EVENT_ATTRIBUTES: event attributes used to form tokens. Defaults to
          the activity attribute.
        - TRACE_ATTRIBUTES: case attributes added as context tokens.
        - MODEL: pre-trained gensim Word2Vec model. If omitted, a model is
          trained on the provided log.
        - VECTOR_SIZE, WINDOW, MIN_COUNT, WORKERS, EPOCHS, SG: gensim Word2Vec
          training parameters.
        - AGGREGATION: "mean" or "sum" token-vector aggregation.

    Returns
    -------
    data
        One row per trace, containing the aggregated Word2Vec dimensions.
    feature_names
        Dimension names corresponding to the columns of data.
    """
    if parameters is None:
        parameters = {}

    try:
        from gensim.models import Word2Vec
    except ImportError as exc:
        raise ImportError(
            "The WORD2VEC trace encoding uses gensim. Please install gensim "
            "to use this variant."
        ) from exc

    _, traces = trace_text.log_to_trace_tokens(log, parameters=parameters)
    vector_size = exec_utils.get_param_value(
        Parameters.VECTOR_SIZE, parameters, 100
    )
    model = exec_utils.get_param_value(Parameters.MODEL, parameters, None)
    aggregation = exec_utils.get_param_value(
        Parameters.AGGREGATION, parameters, "mean"
    )

    if model is None:
        model = Word2Vec(
            sentences=traces,
            vector_size=vector_size,
            window=exec_utils.get_param_value(Parameters.WINDOW, parameters, 5),
            min_count=exec_utils.get_param_value(Parameters.MIN_COUNT, parameters, 1),
            workers=exec_utils.get_param_value(Parameters.WORKERS, parameters, 1),
            sg=exec_utils.get_param_value(Parameters.SG, parameters, 1),
            epochs=exec_utils.get_param_value(Parameters.EPOCHS, parameters, 10),
        )
    else:
        vector_size = int(model.vector_size)

    data = []
    for trace in traces:
        vectors = [model.wv[token] for token in trace if token in model.wv]
        data.append(_aggregate(vectors, vector_size, aggregation))

    feature_names = ["@@word2vec_dim_" + str(i) for i in range(vector_size)]
    return data, feature_names
