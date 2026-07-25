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
from typing import Optional, Dict, Any, Union

from pm4py.algo.conformance.alignments.edit_distance.variants import (
    edit_distance,
    approx_subset,
)
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.util import exec_utils
from pm4py.util import typing
import pandas as pd


class Variants(Enum):
    EDIT_DISTANCE = edit_distance
    APPROX_SUBSET = approx_subset


def apply(
    log1: Union[EventLog, pd.DataFrame],
    log2: Union[EventLog, pd.DataFrame, PetriNet],
    variant=Variants.EDIT_DISTANCE,
    parameters: Optional[Dict[Any, Any]] = None,
    initial_marking: Optional[Marking] = None,
    final_marking: Optional[Marking] = None,
) -> typing.ListAlignments:
    """
    Aligns each trace of the first log against the second log, or approximates
    Petri-net alignments from a representative subset.

    Parameters
    --------------
    log1
        First log
    log2
        Second log. For ``Variants.APPROX_SUBSET``, the accepting Petri net.
    variant
        Variant of the algorithm, possible values:
        - Variants.EDIT_DISTANCE: minimizes the edit distance
        - Variants.APPROX_SUBSET: selects representative model behavior and
          aligns remaining variants using insertion/deletion edit distance
    parameters
        Parameters of the algorithm

    Returns
    ---------------
    aligned_traces
        List that contains, for each trace of the first log, the corresponding alignment
    """
    selected_variant = exec_utils.get_variant(variant)
    if selected_variant is approx_subset:
        if not isinstance(log2, PetriNet):
            raise TypeError(
                "APPROX_SUBSET expects a PetriNet as the second argument"
            )
        if initial_marking is None:
            initial_marking = exec_utils.get_param_value(
                "initial_marking", parameters or {}, None
            )
        if final_marking is None:
            final_marking = exec_utils.get_param_value(
                "final_marking", parameters or {}, None
            )
        if initial_marking is None or final_marking is None:
            raise ValueError(
                "initial_marking and final_marking are required for APPROX_SUBSET"
            )
        return selected_variant.apply(
            log1,
            log2,
            initial_marking,
            final_marking,
            parameters=parameters,
        )
    return selected_variant.apply(log1, log2, parameters=parameters)


def apply_approximation(
    log: Union[EventLog, pd.DataFrame],
    petri_net: PetriNet,
    initial_marking: Marking,
    final_marking: Marking,
    parameters: Optional[Dict[Any, Any]] = None,
) -> typing.ListAlignments:
    """Convenience entry point for the subset/edit-distance variant."""
    return apply(
        log,
        petri_net,
        variant=Variants.APPROX_SUBSET,
        parameters=parameters,
        initial_marking=initial_marking,
        final_marking=final_marking,
    )


def apply_approximation_with_summary(
    log: Union[EventLog, pd.DataFrame],
    petri_net: PetriNet,
    initial_marking: Marking,
    final_marking: Marking,
    parameters: Optional[Dict[Any, Any]] = None,
) -> Dict[str, Any]:
    """Return subset/edit-distance alignments and aggregate fitness bounds."""
    return approx_subset.apply_with_summary(
        log,
        petri_net,
        initial_marking,
        final_marking,
        parameters=parameters,
    )
