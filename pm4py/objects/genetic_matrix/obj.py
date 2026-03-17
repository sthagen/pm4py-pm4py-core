'''
    PM4Py – A Process Mining Library for Python
Copyright (C) 2026 Process Intelligence Solutions UG (haftungsbeschränkt)

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
# Author: Maximilian Josef Frank (https://orcid.org/0000-0002-0714-7748)

from typing import Dict, FrozenSet, List

class GeneticMatrix:
    def __init__(
        self,
        input_map: Dict[str, List[FrozenSet[str]]],
        output_map: Dict[str, List[FrozenSet[str]]],
        transitions: List[str],
    ):
        """
        Initialize a Genetic matrix

        Reference paper:
        Maximilian Josef Frank. "Optimising and Implementing the Genetic Miner in PM4Py" (2026).

        Parameters
        -------------
        input_map
            Input map for each node
        output_map
            Output map for each node
        transitions
            List of transitions
        """
        self.input_map = input_map
        self.output_map = output_map
        self.transitions = transitions

    def __repr__(self):
        return str({
            "I": self.input_map,
            "O": self.output_map,
            "T": self.transitions
        })

    def __str__(self):
        return self.__repr__()
