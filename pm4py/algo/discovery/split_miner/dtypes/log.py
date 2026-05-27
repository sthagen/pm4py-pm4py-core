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
from typing import Any, List, Tuple

# A flat label trace consumed by the classic Split Miner pipeline.
LabelTrace = List[str]
LabelLog = List[LabelTrace]

# A refined event keeps the activity label, the lifecycle phase
# (``start`` or ``end``) and the timestamp. The lifecycle-aware variant
# of the pipeline operates on lists of these.
RefinedEvent = Tuple[str, str, Any]
RefinedTrace = List[RefinedEvent]
RefinedLog = List[RefinedTrace]

# Sentinel labels added to every trace so the resulting BPMN has a single
# start event and a single end event.
START_LABEL = "__start__"
END_LABEL = "__end__"
