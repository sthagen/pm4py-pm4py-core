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
from pm4py.util import exec_utils, constants, xes_constants
from typing import Optional, Dict, Any, List, Tuple
from pm4py.objects.conversion.log import converter as log_converter
import pandas as pd
from enum import Enum
from pm4py.algo.transformation.trace_encodings.util import similarity
from pm4py.algo.transformation.trace_encodings.util import trace_text


class Parameters(Enum):
    CASE_ID_KEY = constants.PARAMETER_CONSTANT_CASEID_KEY
    EMBEDDING_MODEL = "embedding_model"
    ATTRIBUTE_KEY = constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY
    EVENT_ATTRIBUTES = "event_attributes"
    TRACE_ATTRIBUTES = "trace_attributes"


def apply(log: pd.DataFrame, parameters: Optional[Dict[Any, Any]] = None) -> Tuple[List[str], List[List[float]]]:
    """
    Computes one text embedding per case.

    From an event-log point of view, each trace is converted to a sentence and
    then embedded by a sentence-transformers model. By default, the sentence is
    the sequence of activity names. Additional event attributes and trace
    attributes can be included to represent a richer perspective.

    Example with activity-only encoding:
        case 1: A, B, C -> "A B C"
        case 2: A, C    -> "A C"

    Example with event_attributes=["concept:name", "org:resource"]:
        event A by R1 becomes "concept:name=A|org:resource=R1"

    The output is a list of case identifiers and a list of dense embedding
    vectors, one vector per case.

    Parameters
    -----------------
    log
        Pandas dataframe
    parameters
        Parameters of the algorithm, including:
        - Parameters.CASE_ID_KEY => the case identifier column
        - Parameters.EMBEDDING_MODEL => the embedding to be used (default: all-MiniLM-L6-v2)
        - Parameters.ATTRIBUTE_KEY => the attribute to be used for the concatenation
        - Parameters.EVENT_ATTRIBUTES => event attributes to include in the case sentence. If omitted, ATTRIBUTE_KEY is used.
        - Parameters.TRACE_ATTRIBUTES => trace attributes to include as case context tokens.

    Returns
    ----------------
    cases_identifiers
        The list of all the case identifiers
    embeddings_list
        The list of embeddings for the considered cases
    """
    if parameters is None:
        parameters = {}

    case_id_key = exec_utils.get_param_value(Parameters.CASE_ID_KEY, parameters, constants.CASE_CONCEPT_NAME)
    attribute_key = exec_utils.get_param_value(Parameters.ATTRIBUTE_KEY, parameters, xes_constants.DEFAULT_NAME_KEY)
    embedding_model = exec_utils.get_param_value(Parameters.EMBEDDING_MODEL, parameters,
                                                 constants.DEFAULT_EMBEDDING_MODEL)

    cases_identifiers = []
    sentences = []

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(embedding_model)

    event_attributes = exec_utils.get_param_value(
        Parameters.EVENT_ATTRIBUTES, parameters, None
    )
    trace_attributes = exec_utils.get_param_value(
        Parameters.TRACE_ATTRIBUTES, parameters, []
    )

    if event_attributes is not None or trace_attributes:
        cases_identifiers, traces = trace_text.log_to_trace_tokens(
            log, parameters=parameters
        )
        sentences = [trace_text.tokens_to_sentence(x) for x in traces]
    else:
        log = log_converter.apply(log, variant=log_converter.Variants.TO_DATA_FRAME)
        cases = log.groupby(case_id_key)[attribute_key].agg(list)
        cases = cases.to_dict()

        for k, v in cases.items():
            cases_identifiers.append(k)
            sentences.append(" ".join(str(x) for x in v))

    embeddings_list = list(model.encode(sentences))

    return cases_identifiers, embeddings_list


def keep_top_k_per_similarity(log: pd.DataFrame, target_sentence: str, k: int, cases_identifiers: Optional[List[str]] = None, embeddings_list: Optional[List[List[float]]] = None, parameters: Optional[Dict[Any, Any]] = None) -> pd.DataFrame:
    """
    Keeps the top K cases by embedding similarity with the given sentence.

    For example, after encoding cases as activity sentences, the query
    "rejected cases" is embedded with the same model and compared with each
    case embedding using cosine similarity.

    Parameters
    ----------------
    log
        Pandas dataframe
    target_sentence
        Target sentence
    k
        Number of similar cases to retain
    cases_identifiers
        (Optional) the list of cases identifiers in the log, as returned by the 'apply' method
    embeddings_list
        (Optional) the list of embeddings for such cases, as returned by the 'apply' method
    parameters
        Other parameters of the method

    Returns
    -----------------
    filtered_log
        Event log filtered on the top K cases according to the similarity metric.
    """
    if parameters is None:
        parameters = {}

    case_id_key = exec_utils.get_param_value(Parameters.CASE_ID_KEY, parameters, constants.CASE_CONCEPT_NAME)

    if cases_identifiers is None or embeddings_list is None:
        cases_identifiers, embeddings_list = apply(log, parameters=parameters)

    sim = similarity.apply(target_sentence, embeddings_list)
    cases = [(cases_identifiers[i], sim[i]) for i in range(len(cases_identifiers))]
    cases.sort(key=lambda x: (x[1], x[0]), reverse=True)
    cases = cases[:k]
    cases = [x[0] for x in cases]

    log = log[log[case_id_key].isin(cases)]

    return log
