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
Trace-level Doc2Vec encoding.

From an event-log point of view, each case is treated as one document and
each event token is treated as one word in that document. A Doc2Vec model
learns a dense vector directly for each trace/document.

Example with activity tokens:
    case 1: A, B, C
    case 2: A, B, D

Doc2Vec learns one vector for "A B C" and one vector for "A B D". Unlike
Word2Vec, no explicit mean over event-token vectors is needed because the
document vector is trained directly.

Reference:
Tavares, G. M., Oyamada, R. S., Barbon Junior, S., and Ceravolo, P.
"Trace encoding in process mining: A survey and benchmarking."
Engineering Applications of Artificial Intelligence, 126, 107028, 2023.
https://doi.org/10.1016/j.engappai.2023.107028

This variant delegates model training/inference to gensim's maintained
Doc2Vec implementation.
"""

from enum import Enum
from typing import Any, Dict, Optional, Union

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
    DM = "dm"


def apply(
    log: Union[EventLog, EventStream, pd.DataFrame],
    parameters: Optional[Dict[Any, Any]] = None,
):
    """
    Encodes each trace as a gensim Doc2Vec document vector.

    Parameters
    ----------
    log
        Event log, event stream, or dataframe containing traces.
    parameters
        Parameters of the encoding. Common options:
        - EVENT_ATTRIBUTES: event attributes used to form tokens. Defaults to
          the activity attribute.
        - TRACE_ATTRIBUTES: case attributes added as context tokens.
        - MODEL: pre-trained gensim Doc2Vec model. If omitted, a model is
          trained on the provided log.
        - VECTOR_SIZE, WINDOW, MIN_COUNT, WORKERS, EPOCHS, DM: gensim Doc2Vec
          training parameters.

    Returns
    -------
    data
        One row per trace, containing Doc2Vec dimensions.
    feature_names
        Dimension names corresponding to the columns of data.
    """
    if parameters is None:
        parameters = {}

    try:
        from gensim.models.doc2vec import Doc2Vec, TaggedDocument
    except ImportError as exc:
        raise ImportError(
            "The DOC2VEC trace encoding uses gensim. Please install gensim "
            "to use this variant."
        ) from exc

    _, traces = trace_text.log_to_trace_tokens(log, parameters=parameters)
    vector_size = exec_utils.get_param_value(
        Parameters.VECTOR_SIZE, parameters, 100
    )
    epochs = exec_utils.get_param_value(Parameters.EPOCHS, parameters, 20)
    model = exec_utils.get_param_value(Parameters.MODEL, parameters, None)

    if model is None:
        documents = [
            TaggedDocument(words=trace, tags=[str(index)])
            for index, trace in enumerate(traces)
        ]
        model = Doc2Vec(
            documents=documents,
            vector_size=vector_size,
            window=exec_utils.get_param_value(Parameters.WINDOW, parameters, 5),
            min_count=exec_utils.get_param_value(Parameters.MIN_COUNT, parameters, 1),
            workers=exec_utils.get_param_value(Parameters.WORKERS, parameters, 1),
            dm=exec_utils.get_param_value(Parameters.DM, parameters, 1),
            epochs=epochs,
        )
        data = [model.dv[str(index)].tolist() for index in range(len(traces))]
    else:
        vector_size = int(model.vector_size)
        data = [
            model.infer_vector(trace, epochs=epochs).tolist()
            for trace in traces
        ]

    feature_names = ["@@doc2vec_dim_" + str(i) for i in range(vector_size)]
    return data, feature_names
