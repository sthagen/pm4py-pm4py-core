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
"""Streaming approximate alignment factory."""

from enum import Enum

from pm4py.streaming.algo.conformance.alignments.variants import approx_iws
from pm4py.util import exec_utils


class Variants(Enum):
    APPROX_IWS = approx_iws


DEFAULT_VARIANT = Variants.APPROX_IWS


def apply(net, im, fm, variant=DEFAULT_VARIANT, parameters=None):
    """Create a streaming alignment object.

    The returned object accepts events through ``receive`` and exposes prefix
    alignments through ``get``.  Call ``finish(case_id)`` when a case ends to
    obtain a complete alignment.
    """
    return exec_utils.get_variant(variant).apply(
        net, im, fm, parameters=parameters
    )
