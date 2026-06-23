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
from enum import Enum
from typing import Any, Optional, Dict, Union, List, Tuple

import pandas as pd

from pm4py.objects.log.obj import EventLog, EventStream
from pm4py.util import exec_utils
from pm4py.algo.transformation.trace_encodings.variants import (
    alignments,
    bert,
    cases_transformers,
    count2vec,
    doc2vec,
    event_based,
    events_transformers,
    n_grams,
    one_hot,
    trace_based,
    temporal,
    temporal_lazy,
    tf_idf,
    token_replay,
    word2vec,
)


class Variants(Enum):
    ALIGNMENTS = alignments
    BERT = bert
    COUNT2VEC = count2vec
    DOC2VEC = doc2vec
    EVENT_BASED = event_based
    CASES_TRANSFORMERS = cases_transformers
    EVENTS_TRANSFORMERS = events_transformers
    N_GRAMS = n_grams
    ONE_HOT = one_hot
    TRACE_BASED = trace_based
    TEMPORAL = temporal
    TEMPORAL_LAZY = temporal_lazy
    TF_IDF = tf_idf
    TOKEN_REPLAY = token_replay
    WORD2VEC = word2vec


def apply(
    log: Union[EventLog, pd.DataFrame, EventStream],
    variant: Any = Variants.TRACE_BASED,
    parameters: Optional[Dict[Any, Any]] = None,
) -> Tuple[Any, List[str]]:
    """
    Encodes traces from a log object.

    Parameters
    ---------------
    log
        Event log
    variant
        Variant of the feature extraction to use:

        - Variants.ALIGNMENTS => encodes Petri-net alignment diagnostics
        - Variants.BERT => embeds trace sentences using sentence-transformers
        - Variants.COUNT2VEC => counts trace token occurrences using scikit-learn
        - Variants.DOC2VEC => embeds traces as gensim Doc2Vec document vectors
        - Variants.EVENT_BASED => extracts, for each trace, a list of numerical vectors containing for each event the corresponding features
        - Variants.CASES_TRANSFORMERS => computes sentence-transformer embeddings at the case level
        - Variants.EVENTS_TRANSFORMERS => computes sentence-transformer embeddings at the event level
        - Variants.N_GRAMS => counts contiguous trace token n-grams using scikit-learn
        - Variants.ONE_HOT => extracts binary trace token occurrence vectors using scikit-learn
        - Variants.TRACE_BASED => extracts for each trace a single numerical vector containing the features of the trace
        - Variants.TEMPORAL => extracts temporal features from the traditional event log
        - Variants.TEMPORAL_LAZY => extracts temporal features from a Polars LazyFrame
        - Variants.TF_IDF => weights trace tokens/n-grams using scikit-learn TF-IDF
        - Variants.TOKEN_REPLAY => encodes token-replay diagnostics
        - Variants.WORD2VEC => aggregates gensim Word2Vec token vectors per trace

    Returns
    ---------------
    data
        Data to provide for decision tree learning
    feature_names
        Names of the features, in order
    """
    if parameters is None:
        parameters = {}

    return exec_utils.get_variant(variant).apply(log, parameters=parameters)


def keep_top_k_per_similarity(
    log: pd.DataFrame,
    target_sentence: str,
    k: int,
    variant=Variants.CASES_TRANSFORMERS,
    parameters: Optional[Dict[Any, Any]] = None,
) -> pd.DataFrame:
    """
    Keeps the top K events/cases per embedding similarity.
    """
    return exec_utils.get_variant(variant).keep_top_k_per_similarity(
        log, target_sentence, k, parameters=parameters
    )
