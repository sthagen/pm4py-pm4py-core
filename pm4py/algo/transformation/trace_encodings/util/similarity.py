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
import numpy as np
from typing import List, Union, Optional, Dict, Any
from pm4py.algo.transformation.trace_encodings.util import embed_sentence


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def apply(target_embedding: Union[str, List[float]], embeddings_list: List[List[float]], parameters: Optional[Dict[Any, Any]] = None) -> List[float]:
    """
    Computes the cosine similarity between the embeddings of a target sentence and a list of embeddings
    (at the case or event level)

    Parameters
    -----------------
    target_embedding
        Target sentence (embeddings)
    embeddings_list
        List of embeddings (at the case or event level)
    parameters
        Parameters of the method

    Returns
    ------------------
    similarity_list
        List containing the cosine similarities between each entry and the target sentence
    """
    if parameters is None:
        parameters = {}

    if isinstance(target_embedding, str):
        target_embedding = embed_sentence.apply(target_embedding, parameters=parameters)

    similarity_list = [cosine_similarity(target_embedding, emb) for emb in embeddings_list]

    return similarity_list
