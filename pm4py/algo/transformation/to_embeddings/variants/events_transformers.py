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
from pm4py.algo.transformation.to_embeddings.util import similarity
from sentence_transformers import SentenceTransformer


class Parameters(Enum):
    EVENT_ID_KEY = "event_id_key"
    CASE_ID_KEY = constants.PARAMETER_CONSTANT_CASEID_KEY
    EMBEDDING_MODEL = "embedding_model"
    ATTRIBUTE_KEY = constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY
    KEEP_CASES = "keep_cases"


def apply(log: pd.DataFrame, parameters: Optional[Dict[Any, Any]] = None) -> Tuple[List[str], List[List[float]]]:
    """
    Computes the embeddings of events considering a specific attribute

    Parameters
    -----------------
    log
        Pandas dataframe
    Parameters
        Parameters of the algorithm, including:
        - Parameters.EVENT_ID_KEY => an attribute unique per event
        - Parameters.EMBEDDING_MODEL => the embedding to be used (default: all-MiniLM-L6-v2)
        - Parameters.ATTRIBUTE_KEY => the attribute to be used

    Returns
    ----------------
    event_identifiers
        The list of all the event identifiers
    embeddings_list
        The list of embeddings for the considered events
    """
    if parameters is None:
        parameters = {}

    event_id_key = exec_utils.get_param_value(Parameters.EVENT_ID_KEY, parameters, constants.DEFAULT_INDEX_KEY)
    attribute_key = exec_utils.get_param_value(Parameters.ATTRIBUTE_KEY, parameters, xes_constants.DEFAULT_NAME_KEY)
    embedding_model = exec_utils.get_param_value(Parameters.EMBEDDING_MODEL, parameters,
                                                 constants.DEFAULT_EMBEDDING_MODEL)

    log = log_converter.apply(log, variant=log_converter.Variants.TO_DATA_FRAME)

    event_identifiers = []
    sentences = []

    model = SentenceTransformer(embedding_model)

    log = log[[event_id_key, attribute_key]].to_dict("records")

    for entry in log:
        event_identifiers.append(entry[event_id_key])
        sentences.append(entry[attribute_key])

    embeddings_list = list(model.encode(sentences))

    return event_identifiers, embeddings_list


def keep_top_k_per_similarity(log: pd.DataFrame, target_sentence: str, k: int,
                              event_identifiers: Optional[List[str]] = None,
                              embeddings_list: Optional[List[List[float]]] = None,
                              parameters: Optional[Dict[Any, Any]] = None) -> pd.DataFrame:
    """
    Keeps the top K events for (embedding-based) similarity with the given sentence

    Parameters
    ----------------
    log
        Pandas dataframe
    target_sentence
        Target sentence
    k
        Number of similar events to retain
    event_identifiers
        (Optional) the list of event identifiers in the log, as returned by the 'apply' method
    embeddings_list
        (Optional) the list of embeddings for such events, as returned by the 'apply' method
    parameters
        Other parameters of the method:
        - Parameters.KEEP_CASES => If True, keep the cases containing such events, instead of the events themselves (default: False)

    Returns
    -----------------
    filtered_log
        Event log filtered on the top K events (or cases) according to the similarity metric.
    """
    if parameters is None:
        parameters = {}

    event_id_key = exec_utils.get_param_value(Parameters.EVENT_ID_KEY, parameters, constants.DEFAULT_INDEX_KEY)
    keep_cases = exec_utils.get_param_value(Parameters.KEEP_CASES, parameters, False)

    if event_identifiers is None or embeddings_list is None:
        event_identifiers, embeddings_list = apply(log, parameters=parameters)

    sim = similarity.apply(target_sentence, embeddings_list)
    events = [(event_identifiers[i], sim[i]) for i in range(len(event_identifiers))]
    events.sort(key=lambda x: (x[1], x[0]), reverse=True)
    events = events[:k]
    events = [x[0] for x in events]

    filt_log = log[log[event_id_key].isin(events)]

    if keep_cases:
        case_id_key = exec_utils.get_param_value(Parameters.CASE_ID_KEY, parameters, constants.CASE_CONCEPT_NAME)
        filt_log2 = log[log[case_id_key].isin(filt_log[case_id_key])]
        return filt_log2

    return filt_log
