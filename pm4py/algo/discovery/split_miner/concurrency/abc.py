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
"""Abstract base class for the concurrency-discovery phase.

A :class:`ConcurrencyOracle` takes a DFG (and, optionally, the underlying
trace list) and returns both the set of unordered concurrent pairs and
the *pruned* DFG with the concurrent arcs removed.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar

from pm4py.algo.discovery.split_miner.dtypes.concurrency import (
    ConcurrencyResult,
)
from pm4py.algo.discovery.split_miner.dtypes.dfg import DFG
from pm4py.algo.discovery.split_miner.dtypes.loops import LoopInfo


TraceT = TypeVar("TraceT")


class ConcurrencyOracle(ABC):
    """Detect concurrent activity pairs and prune the DFG accordingly."""

    @classmethod
    @abstractmethod
    def apply(
        cls,
        dfg: DFG,
        traces: Optional[List[TraceT]],
        loops: LoopInfo,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ConcurrencyResult:
        """Return the pruned DFG together with the concurrency relation."""
