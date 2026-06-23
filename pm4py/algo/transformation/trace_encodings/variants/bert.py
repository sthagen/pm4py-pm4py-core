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
Trace-level BERT-style sentence embedding.

From an event-log point of view, each case is converted to a sentence and
then embedded by a transformer model. By default, the sentence is the
activity sequence, but additional event and trace attributes can be included
to embed a richer perspective.

Example with activity-only encoding:
    case 1: A, B, C -> "A B C"
    case 2: A, C    -> "A C"

A BERT/sentence-transformer model maps each sentence to a dense vector. The
output has one row per trace and one column per embedding dimension.

Reference:
Tavares, G. M., Oyamada, R. S., Barbon Junior, S., and Ceravolo, P.
"Trace encoding in process mining: A survey and benchmarking."
Engineering Applications of Artificial Intelligence, 126, 107028, 2023.
https://doi.org/10.1016/j.engappai.2023.107028

This variant delegates embedding computation to sentence-transformers. The
default model name is intentionally configurable because model availability is
environment-specific.
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
    BERT_MODEL = "bert_model"
    EMBEDDING_MODEL = "embedding_model"


def apply(
    log: Union[EventLog, EventStream, pd.DataFrame],
    parameters: Optional[Dict[Any, Any]] = None,
):
    """
    Encodes each trace as a dense transformer/BERT-style sentence vector.

    Parameters
    ----------
    log
        Event log, event stream, or dataframe containing traces.
    parameters
        Parameters of the encoding. Common options:
        - EVENT_ATTRIBUTES: event attributes used to form tokens. Defaults to
          the activity attribute.
        - TRACE_ATTRIBUTES: case attributes added as context tokens.
        - BERT_MODEL/EMBEDDING_MODEL: sentence-transformers model name or path.

    Returns
    -------
    data
        One row per trace, containing transformer embedding dimensions.
    feature_names
        Dimension names corresponding to the columns of data.
    """
    if parameters is None:
        parameters = {}

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ImportError(
            "The BERT trace encoding uses sentence-transformers. Please "
            "install sentence-transformers to use this variant."
        ) from exc

    model_name = exec_utils.get_param_value(
        Parameters.BERT_MODEL,
        parameters,
        exec_utils.get_param_value(
            Parameters.EMBEDDING_MODEL, parameters, "bert-base-nli-mean-tokens"
        ),
    )

    _, traces = trace_text.log_to_trace_tokens(log, parameters=parameters)
    sentences = [trace_text.tokens_to_sentence(trace) for trace in traces]
    model = SentenceTransformer(model_name)
    embeddings = model.encode(sentences)
    data = [embedding.tolist() for embedding in embeddings]

    vector_size = len(data[0]) if data else 0
    feature_names = ["@@bert_dim_" + str(i) for i in range(vector_size)]
    return data, feature_names
