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
"""Trace types used by the Split Miner phases."""
from typing import List

# A flat label trace consumed by the Split Miner pipeline. Split Miner
# 2.0 projects each trace onto its ``complete``-event labels and feeds
# the same flat representation through the shared machinery.
LabelTrace = List[str]

# Sentinel labels added to every trace so the resulting BPMN has a single
# start event and a single end event.
START_LABEL = "__start__"
END_LABEL = "__end__"
