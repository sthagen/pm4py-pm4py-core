'''
    PM4Py â€“ A Process Mining Library for Python
Copyright (C) 2024 Process Intelligence Solutions UG (haftungsbeschrÃ¤nkt)

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
from pm4py.algo.transformation.to_embeddings.variants import cases_transformers, events_transformers
from enum import Enum
from pm4py.util import exec_utils
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple


class Variants(Enum):
    CASES_TRANSFORMERS = cases_transformers
    EVENTS_TRANSFORMERS = events_transformers


def apply(log: pd.DataFrame, variant=Variants.CASES_TRANSFORMERS, parameters: Optional[Dict[Any, Any]] = None) -> Tuple[
    List[str], List[List[float]]]:
    """
    Computes the embeddings (case/event level, depending on the variant) of the provided dataframe.

    Parameters
    -----------------
    log
        Pandas dataframe
    variant
        Variant of the algorithm, including:
        - Variants.CASES_TRANSFORMERS => computes the embeddings at the case level
        - Variants.EVENTS_TRANSFORMERS => computes the embeddings at the event level
    parameters
        Variant-specific parameters

    Returns
    ----------------
    ids
        Identifiers of the considered events/cases
    embeddings_list
        List of embeddings for the considered events/cases
    """
    return exec_utils.get_variant(variant).apply(log, parameters=parameters)


def keep_top_k_per_similarity(log: pd.DataFrame, target_sentence: str, k: int, variant=Variants.CASES_TRANSFORMERS,
                              parameters: Optional[Dict[Any, Any]] = None) -> pd.DataFrame:
    """
    Keeps the top K events/cases per similarity

    Parameters
    ----------------
    log
        Pandas dataframe
    variant
        Variant of the algorithm, including:
        - Variants.CASES_TRANSFORMERS => computes the embeddings at the case level
        - Variants.EVENTS_TRANSFORMERS => computes the embeddings at the event level
    parameters
        Variant-specific parameters

    Returns
    -----------------
    filtered_log
        Filtered event log
    """
    return exec_utils.get_variant(variant).keep_top_k_per_similarity(log, target_sentence, k, parameters=parameters)
