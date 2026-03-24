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
    CASE_ID_KEY = constants.PARAMETER_CONSTANT_CASEID_KEY
    EMBEDDING_MODEL = "embedding_model"
    ATTRIBUTE_KEY = constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY


def apply(log: pd.DataFrame, parameters: Optional[Dict[Any, Any]] = None) -> Tuple[List[str], List[List[float]]]:
    """
    Computes the embeddings of cases, concatenating all the values of a specified attribute for the events of the case.

    Parameters
    -----------------
    log
        Pandas dataframe
    parameters
        Parameters of the algorithm, including:
        - Parameters.CASE_ID_KEY => the case identifier column
        - Parameters.EMBEDDING_MODEL => the embedding to be used (default: all-MiniLM-L6-v2)
        - Parameters.ATTRIBUTE_KEY => the attribute to be used for the concatenation

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

    log = log_converter.apply(log, variant=log_converter.Variants.TO_DATA_FRAME)

    cases_identifiers = []
    sentences = []

    model = SentenceTransformer(embedding_model)

    cases = log.groupby(case_id_key)[attribute_key].agg(list)
    cases = cases.to_dict()

    for k, v in cases.items():
        cases_identifiers.append(k)
        sentences.append(" ".join(v))

    embeddings_list = list(model.encode(sentences))

    return cases_identifiers, embeddings_list


def keep_top_k_per_similarity(log: pd.DataFrame, target_sentence: str, k: int, cases_identifiers: Optional[List[str]] = None, embeddings_list: Optional[List[List[float]]] = None, parameters: Optional[Dict[Any, Any]] = None) -> pd.DataFrame:
    """
    Keeps the top K cases for (embedding-based) similarity with the given sentence

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
