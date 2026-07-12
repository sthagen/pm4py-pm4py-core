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

``concurrency.refined.RefinedConcurrencyOracle`` was the
approximate lifecycle-overlap oracle of the earlier Split Miner 2.0. It
was replaced by the faithful overlap oracle in
``pm4py.algo.discovery.split_miner.concurrency.lifecycle``
(``apply_overlap_concurrency``), which the SM2 variant selects
automatically for genuine lifecycle logs.

Use the public API instead::

    pm4py.discover_bpmn_split_miner(log, variant='sm2')
"""
raise ImportError(
    "pm4py.algo.discovery.split_miner.concurrency.refined was removed. The "
    "faithful lifecycle-overlap oracle now lives in "
    "pm4py.algo.discovery.split_miner.concurrency.lifecycle and is used "
    "automatically for variant='sm2'. "
    "Use pm4py.discover_bpmn_split_miner(log, variant='sm2')."
)
