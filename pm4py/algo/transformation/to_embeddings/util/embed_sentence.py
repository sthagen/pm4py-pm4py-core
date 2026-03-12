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
from sentence_transformers import SentenceTransformer
from typing import List, Optional, Dict, Any
from enum import Enum
from pm4py.util import exec_utils, constants


class Parameters(Enum):
    EMBEDDING_MODEL = "embedding_model"


def apply(sentence: str, parameters: Optional[Dict[Any, Any]] = None) -> List[float]:
    """
    Encodes a sentence to embeddings

    Parameters
    ----------
    sentence
        Sentence to be encoded
    parameters
        Parameters of the method, including:
        - Parameters.EMBEDDING_MODEL => embedding model to be used (default: all-MiniLM-L6-v2)

    Returns
    -------
    embeddings
        List of numerical embeddings
    """
    if parameters is None:
        parameters = {}

    embedding_model = exec_utils.get_param_value(Parameters.EMBEDDING_MODEL, parameters,
                                                 constants.DEFAULT_EMBEDDING_MODEL)

    model = SentenceTransformer(embedding_model)

    return model.encode([sentence])[0]
