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
"""Abstract base class for the BPMN-export phase."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.objects.bpmn.obj import BPMN


class BPMNExporter(ABC):
    """Convert the internal :class:`WorkingGraph` into a pm4py BPMN object."""

    @classmethod
    @abstractmethod
    def apply(
        cls,
        wg: WorkingGraph,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> BPMN:
        ...
