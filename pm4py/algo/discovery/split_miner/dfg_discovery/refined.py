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

``dfg_discovery.refined.RefinedDFGDiscoverer`` was the approximate
lifecycle DFG of the earlier Split Miner 2.0. The faithful variant now
builds the directly-follows graph from ``complete`` events via
``pm4py.algo.discovery.split_miner.dtypes.complex_log.parse_complex_log``
(the ``getComplexLog`` port) and reuses the classic DFG discoverer; the
SM2 variant wires this automatically.

Use the public API instead::

    pm4py.discover_bpmn_split_miner(log, variant='sm2')
"""
raise ImportError(
    "pm4py.algo.discovery.split_miner.dfg_discovery.refined was removed. The "
    "faithful SM2 directly-follows graph is now built by "
    "pm4py.algo.discovery.split_miner.dtypes.complex_log.parse_complex_log "
    "and used automatically for variant='sm2'. "
    "Use pm4py.discover_bpmn_split_miner(log, variant='sm2')."
)
