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
"""Removed module — compatibility shim.

``pm4py.algo.discovery.split_miner.heuristics`` (``OrSplitHeuristic``,
``ImproperCompletionHeuristic``) belonged to an earlier, approximate
Split Miner 2.0 and was removed when the variant was reworked to
reproduce the reference Java implementation (``MineWithSMTC``) exactly.

* The OR-split heuristic is now an intrinsic stage of the faithful SM2
  pipeline (``pm4py.algo.discovery.split_miner.or_min.or_split``); it
  runs automatically for ``variant='sm2'``.
* The improper-completion heuristic was an approximation with no
  equivalent in the reference tool and has been dropped.

Use the public API instead::

    pm4py.discover_bpmn_split_miner(log, variant='sm2')
"""
raise ImportError(
    "pm4py.algo.discovery.split_miner.heuristics was removed when Split "
    "Miner 2.0 was reworked to faithfully match the reference Java tool. "
    "The OR-split heuristic now runs automatically for variant='sm2'; the "
    "improper-completion heuristic was an approximation and was dropped. "
    "Use pm4py.discover_bpmn_split_miner(log, variant='sm2')."
)
