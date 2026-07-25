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
from enum import Enum
from typing import Optional, Dict, Any, Union, Tuple, List

import pandas as pd

from pm4py import ProcessTree
from pm4py.algo.discovery.local_process_models.metrics.quality_metrics import LocalProcessModelStats
from pm4py.algo.discovery.local_process_models.variants import classic
from pm4py.objects.log.obj import EventLog
from pm4py.util import exec_utils


class Variants(Enum):
    CLASSIC = classic


def find_local_process_models(
    log: Union[EventLog, pd.DataFrame],
    selected_activities: Union[None, list] = None,
    variant=Variants.CLASSIC,
    parameters: Optional[Dict[Any, Any]] = None,
) -> List[Tuple[ProcessTree, LocalProcessModelStats]]:
    return exec_utils.get_variant(variant).apply(log, selected_activities, parameters)

