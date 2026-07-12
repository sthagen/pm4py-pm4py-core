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
"""OR-join minimisation.

Replace every inclusive (OR) join with the behaviourally equivalent
exclusive (XOR) or parallel (AND) join, following the reference Split
Miner ``replaceIORs`` step. The heavy lifting lives in
:mod:`pm4py.algo.discovery.split_miner.dtypes.gateway_map`, which builds
a gateway map, walks each OR-join back to its dominator and decides
between XOR and AND (inserting token-generator gateways for the parallel
case so the join can always synchronise).
"""
from typing import Any, Dict, Optional

from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.algo.discovery.split_miner.or_min.abc import OrJoinMinimizer
from pm4py.algo.discovery.split_miner.dtypes.gateway_map import (
    replace_inclusive_joins,
)


class ClassicOrJoinMinimizer(OrJoinMinimizer):
    """Replace every inclusive (OR) join with an XOR or AND join."""

    @classmethod
    def apply(
        cls,
        wg: WorkingGraph,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        replace_inclusive_joins(wg, apply_hagen=True)
