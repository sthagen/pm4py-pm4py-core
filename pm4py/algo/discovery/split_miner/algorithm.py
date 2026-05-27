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
"""Top-level dispatcher for Split Miner.

Two variants are exposed:

* :data:`CLASSIC` — the classic Split Miner pipeline.
* :data:`SM2` — Split Miner 2.0, with a lifecycle-aware refined DFG,
  a lifecycle-overlap concurrency oracle, and two heuristics for
  improper-completion repair and OR-split identification.

Both variants return a :class:`pm4py.objects.bpmn.obj.BPMN`.
"""
from enum import Enum
from typing import Any, Dict, Optional, Tuple, Union

import pandas as pd

from pm4py.algo.discovery.split_miner.variants import classic, sm2
from pm4py.objects.bpmn.obj import BPMN
from pm4py.objects.log.obj import EventLog, EventStream
from pm4py.util import exec_utils


class Variants(Enum):
    CLASSIC = classic
    SM2 = sm2


CLASSIC = Variants.CLASSIC
SM2 = Variants.SM2
DEFAULT_VARIANT = CLASSIC

VERSIONS = {CLASSIC, SM2}


def apply(
    log: Union[
        EventLog, EventStream, pd.DataFrame, Dict[Tuple[str, str], int]
    ],
    parameters: Optional[Dict[Any, Any]] = None,
    variant: Variants = DEFAULT_VARIANT,
) -> BPMN:
    """Discover a BPMN model from a log using Split Miner.

    Parameters
    ----------
    log
        Event log (``EventLog`` / ``EventStream`` / ``pandas.DataFrame``)
        or a precomputed DFG (only accepted by the classic variant).
    parameters
        Variant-specific parameters; see ``classic.Parameters`` and
        ``sm2.Parameters`` for the supported keys (``EPSILON``, ``ETA``,
        ``OR_MINIMISE``, ``ACTIVITY_KEY``, …).
    variant
        Either :data:`CLASSIC` (default) or :data:`SM2`.
    """
    return exec_utils.get_variant(variant).apply(log, parameters=parameters)
