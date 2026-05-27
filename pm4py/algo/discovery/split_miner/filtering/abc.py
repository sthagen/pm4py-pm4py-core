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
"""Abstract base class for the PDFG filtering phase."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pm4py.algo.discovery.split_miner.dtypes.dfg import DFG
from pm4py.algo.discovery.split_miner.dtypes.filtering import FilterResult


class Filterer(ABC):
    """Reduce a pruned DFG to a sound, low-complexity edge set."""

    @classmethod
    @abstractmethod
    def apply(
        cls,
        pdfg: DFG,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> FilterResult:
        """Return the source/sink and the kept edges."""
