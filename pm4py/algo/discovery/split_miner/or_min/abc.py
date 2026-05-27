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
"""Abstract base class for the OR-join minimisation phase."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph


class OrJoinMinimizer(ABC):
    """Replace trivial OR-joins by their XOR or AND equivalent."""

    @classmethod
    @abstractmethod
    def apply(
        cls,
        wg: WorkingGraph,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mutate ``wg`` in-place."""
