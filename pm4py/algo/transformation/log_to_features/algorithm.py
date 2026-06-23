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
import warnings
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from pm4py.algo.transformation.trace_encodings import algorithm as trace_encodings
from pm4py.algo.transformation.trace_encodings.variants import (
    event_based,
    temporal,
    temporal_lazy,
    trace_based,
)
from pm4py.objects.log.obj import EventLog, EventStream


class Variants(Enum):
    EVENT_BASED = event_based
    TRACE_BASED = trace_based
    TEMPORAL = temporal
    TEMPORAL_LAZY = temporal_lazy


def apply(
    log: Union[EventLog, pd.DataFrame, EventStream],
    variant: Any = Variants.TRACE_BASED,
    parameters: Optional[Dict[Any, Any]] = None,
) -> Tuple[Any, List[str]]:
    warnings.warn(
        "pm4py.algo.transformation.log_to_features.apply is deprecated; use "
        "pm4py.algo.transformation.trace_encodings.apply instead.",
        FutureWarning,
        stacklevel=2,
    )
    return trace_encodings.apply(log, variant=variant, parameters=parameters)
