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
Trace-level n-gram encoding.

From an event-log point of view, each case is read as an ordered sequence of
tokens. By default, the token of an event is its activity name. The output
has one row per trace and one column per contiguous token pattern of length n.
The cell is the number of times that pattern appears in the trace.

Example with ngram_range=(2, 2):
    case 1: A, B, A
    case 2: A, C

The 2-gram vocabulary is [A >> B, A >> C, B >> A], and the encoded matrix is:
    case 1 -> [1, 0, 1]
    case 2 -> [0, 1, 0]

With ngram_range=(1, 2), the vocabulary includes both single activities and
directly-follows pairs.

Reference:
Tavares, G. M., Oyamada, R. S., Barbon Junior, S., and Ceravolo, P.
"Trace encoding in process mining: A survey and benchmarking."
Engineering Applications of Artificial Intelligence, 126, 107028, 2023.
https://doi.org/10.1016/j.engappai.2023.107028

The survey lists n-grams as a baseline encoding and points to maintained text
tooling for implementation. This variant delegates vector construction to
scikit-learn's CountVectorizer with a trace-token n-gram analyzer.
"""

from enum import Enum
from typing import Any, Dict, Optional, Union

import pandas as pd

from pm4py.objects.log.obj import EventLog, EventStream
from pm4py.algo.transformation.trace_encodings.util import sklearn_vectorization


class Parameters(Enum):
    EVENT_ATTRIBUTES = "event_attributes"
    TRACE_ATTRIBUTES = "trace_attributes"
    NGRAM_RANGE = "ngram_range"
    RETURN_SPARSE = "return_sparse"
    VECTORIZER = "vectorizer"
    FIT_VECTORIZER = "fit_vectorizer"


def apply(
    log: Union[EventLog, EventStream, pd.DataFrame],
    parameters: Optional[Dict[Any, Any]] = None,
):
    """
    Encodes each trace as frequency counts of contiguous token n-grams.

    Parameters
    ----------
    log
        Event log, event stream, or dataframe containing traces.
    parameters
        Parameters of the encoding. Common options:
        - EVENT_ATTRIBUTES: event attributes used to form tokens. Defaults to
          the activity attribute.
        - TRACE_ATTRIBUTES: case attributes added as context tokens.
        - NGRAM_RANGE: tuple such as (2, 2) or (1, 3).
        - RETURN_SPARSE: if True, returns the sklearn sparse matrix.

    Returns
    -------
    data
        One row per trace, one count per discovered n-gram.
    feature_names
        N-gram names corresponding to the columns of data.
    """
    return sklearn_vectorization.apply(
        log, binary=False, ngram_range=(2, 2), parameters=parameters
    )
