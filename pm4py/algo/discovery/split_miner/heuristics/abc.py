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
"""Abstract base class for working-graph heuristics."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pm4py.algo.discovery.split_miner.dtypes.log import RefinedTrace
from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph


class Heuristic(ABC):
    """A post-processing pass that mutates the working graph in-place.

    Heuristics may inspect the refined log (lifecycle-aware trace list)
    to decide what to change.
    """

    @classmethod
    @abstractmethod
    def apply(
        cls,
        wg: WorkingGraph,
        refined_traces: Optional[List[RefinedTrace]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        ...
