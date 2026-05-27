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
"""Classic Split Miner concurrency oracle.

Two activities are flagged as concurrent when they appear as ``a -> b``
and ``b -> a`` in the DFG with roughly balanced frequencies, are not a
short-loop pair, and neither is a self-loop. Imbalanced bidirectional
pairs keep only the more frequent direction.
"""
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from pm4py.algo.discovery.split_miner.concurrency.abc import ConcurrencyOracle
from pm4py.algo.discovery.split_miner.dtypes.concurrency import (
    ConcurrencyResult,
)
from pm4py.algo.discovery.split_miner.dtypes.dfg import DFG
from pm4py.algo.discovery.split_miner.dtypes.loops import LoopInfo
from pm4py.util import exec_utils


class Parameters(Enum):
    EPSILON = "split_miner_epsilon"


DEFAULT_EPSILON = 0.1


class ClassicConcurrencyOracle(ConcurrencyOracle):
    """Three-condition test on directly-follows frequencies.

    The imbalance condition uses ``<= eps`` rather than ``< eps`` to
    mirror the Java reference implementation; with strict ``<`` the
    boundary case at exactly ``eps`` is missed.
    """

    @classmethod
    def apply(
            cls,
            dfg: DFG,
            traces: Optional[List[Any]],  # unused (kept to share signature)
            loops: LoopInfo,
            parameters: Optional[Dict[str, Any]] = None,
    ) -> ConcurrencyResult:
        eps = exec_utils.get_param_value(
            Parameters.EPSILON, parameters or {}, DEFAULT_EPSILON
        )

        concurrent: Set[FrozenSet[str]] = set()
        drop_infrequent: Set[Tuple[str, str]] = set()
        seen: Set[FrozenSet[str]] = set()

        for (a, b), f_ab in list(dfg.items()):
            if a == b:
                continue
            pair = frozenset((a, b))
            if pair in seen:
                continue
            seen.add(pair)

            f_ba = dfg.get((b, a), 0)
            if f_ab <= 0 or f_ba <= 0:
                continue
            if pair in loops.short_loops:
                continue

            denom = f_ab + f_ba
            if denom == 0:
                continue
            imbalance = abs(f_ab - f_ba) / denom

            if imbalance <= eps:
                concurrent.add(pair)
            else:
                if f_ab < f_ba:
                    drop_infrequent.add((a, b))
                else:
                    drop_infrequent.add((b, a))

        pdfg: DFG = {}
        for (a, b), f in dfg.items():
            if frozenset((a, b)) in concurrent:
                continue
            if (a, b) in drop_infrequent:
                continue
            pdfg[(a, b)] = f
        return ConcurrencyResult(pdfg=pdfg, concurrent_pairs=concurrent)
