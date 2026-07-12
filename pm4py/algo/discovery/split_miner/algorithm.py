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
* :data:`SM2` — Split Miner 2.0: the same machinery driven by a
  lifecycle-aware ``complete``-event DFG, an overlap-based concurrency
  oracle for genuine lifecycle logs, a fixed frequency threshold
  (``eta = 1.0``), inclusive joins left in place (``replaceIORs = false``)
  plus the OR-split heuristic, and compact (marked) self-loops.

Both variants return a :class:`pm4py.objects.bpmn.obj.BPMN`.

Faithfulness and validation
---------------------------
Every stage (DFG filtering, concurrency oracle, Oracle split discovery,
RPST-based SESE join discovery, OR-join replacement, gateway collapse)
is a port of the reference Java Split Miner, intended to reproduce its
output exactly rather than the idealised figures in the papers. The
ports were validated against the original Java tools on the SM-Experiment
corpus: classic Split Miner is byte-identical (isomorphic, same gateway
labels) to ``splitminer.jar`` on the deterministic real-life logs, and
SM2 is byte-identical to ``sm2.jar`` (``MineWithSMTC``) on 9 of 10
reference logs (the tenth is non-deterministic in the Java tool itself).
Because the target is the *tool*, not the papers, some hand-computed
gateway counts from earlier tests changed: e.g. on the Augusto et al.
(2019) running example the tool yields 2 AND-splits / 4 XOR-splits, not
the 1 / 3 from the paper.
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
        ``sm2.Parameters`` for the supported keys. The classic variant
        honors ``EPSILON``, ``ETA``, ``OR_MINIMISE`` and
        ``ACTIVITY_KEY``; the SM2 variant honors ``EPSILON``,
        ``ACTIVITY_KEY`` and ``TIMESTAMP_KEY`` and ignores ``ETA`` and
        ``OR_MINIMISE`` (pinned to the reference tool's fixed values).
    variant
        Either :data:`CLASSIC` (default) or :data:`SM2`.
    """
    return exec_utils.get_variant(variant).apply(log, parameters=parameters)
