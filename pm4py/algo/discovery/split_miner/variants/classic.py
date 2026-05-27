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
"""Classic Split Miner.

Inherits the full default pipeline from :class:`SplitMinerFramework`
without further overrides — every default ``do_*`` method already
implements the classic behaviour.
"""
from enum import Enum
from typing import Any, Dict, Optional, Union

import pandas as pd

from pm4py.algo.discovery.split_miner.concurrency.classic import (
    Parameters as ConcParameters,
)
from pm4py.algo.discovery.split_miner.dtypes.dfg import DFG
from pm4py.algo.discovery.split_miner.filtering.max_min import (
    Parameters as FilterParameters,
)
from pm4py.algo.discovery.split_miner.variants.abc import (
    Parameters as FrameworkParameters,
    SplitMinerFramework,
)
from pm4py.objects.bpmn.obj import BPMN
from pm4py.objects.log.obj import EventLog, EventStream
from pm4py.util import constants


class Parameters(Enum):
    EPSILON = ConcParameters.EPSILON.value
    ETA = FilterParameters.ETA.value
    OR_MINIMISE = FrameworkParameters.OR_MINIMISE.value
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY


class ClassicSplitMiner(SplitMinerFramework):
    """Classic Split Miner — default pipeline."""


def apply(
    log: Union[EventLog, EventStream, pd.DataFrame, DFG],
    parameters: Optional[Dict[str, Any]] = None,
) -> BPMN:
    """Discover a BPMN model using classic Split Miner."""
    return ClassicSplitMiner().apply(log, parameters)
