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
"""Abstract base class for the DFG-discovery phase."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar

from pm4py.algo.discovery.split_miner.dtypes.dfg import DFG
from pm4py.algo.discovery.split_miner.dtypes.loops import LoopInfo


TraceT = TypeVar("TraceT")


class DFGDiscoverer(ABC, Generic[TraceT]):
    """Build a DFG and the corresponding ``LoopInfo`` from a list of traces."""

    @classmethod
    @abstractmethod
    def apply(
        cls,
        traces: List[TraceT],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[DFG, LoopInfo]:
        """Return the directly-follows graph and its self/short-loop summary."""
