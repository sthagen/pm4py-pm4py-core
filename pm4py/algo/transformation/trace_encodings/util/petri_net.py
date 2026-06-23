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
from typing import Any, Dict, Optional, Tuple, Union

import pandas as pd

from pm4py.objects.conversion.log import converter as log_converter
from pm4py.objects.log.obj import EventLog, EventStream
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.util import constants, exec_utils, xes_constants


class Parameters(Enum):
    NET = "net"
    PETRI_NET = "petri_net"
    INITIAL_MARKING = "initial_marking"
    FINAL_MARKING = "final_marking"
    DISCOVER_MODEL = "discover_model"
    DISCOVERY_VARIANT = "discovery_variant"
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY
    TIMESTAMP_KEY = constants.PARAMETER_CONSTANT_TIMESTAMP_KEY
    CASE_ID_KEY = constants.PARAMETER_CONSTANT_CASEID_KEY


def get_log_and_model(
    log: Union[EventLog, EventStream, pd.DataFrame],
    parameters: Optional[Dict[Any, Any]] = None,
) -> Tuple[EventLog, PetriNet, Marking, Marking]:
    """
    Resolves an EventLog and Petri net for PM-based trace encodings.
    """
    if parameters is None:
        parameters = {}

    event_log = log_converter.apply(
        log, variant=log_converter.Variants.TO_EVENT_LOG, parameters=parameters
    )

    net = exec_utils.get_param_value(Parameters.NET, parameters, None)
    if net is None:
        net = exec_utils.get_param_value(Parameters.PETRI_NET, parameters, None)
    initial_marking = exec_utils.get_param_value(
        Parameters.INITIAL_MARKING, parameters, None
    )
    final_marking = exec_utils.get_param_value(
        Parameters.FINAL_MARKING, parameters, None
    )

    if net is not None and initial_marking is not None and final_marking is not None:
        return event_log, net, initial_marking, final_marking

    discover_model = exec_utils.get_param_value(
        Parameters.DISCOVER_MODEL, parameters, True
    )
    if not discover_model:
        raise ValueError(
            "PM-based trace encodings require net, initial_marking, and "
            "final_marking when discover_model is False."
        )

    from pm4py.algo.discovery.inductive import algorithm as inductive_miner
    from pm4py.objects.conversion.process_tree import converter as pt_converter

    activity_key = exec_utils.get_param_value(
        Parameters.ACTIVITY_KEY, parameters, xes_constants.DEFAULT_NAME_KEY
    )
    timestamp_key = exec_utils.get_param_value(
        Parameters.TIMESTAMP_KEY, parameters, xes_constants.DEFAULT_TIMESTAMP_KEY
    )
    case_id_key = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, constants.CASE_CONCEPT_NAME
    )
    discovery_variant = exec_utils.get_param_value(
        Parameters.DISCOVERY_VARIANT, parameters, inductive_miner.Variants.IM
    )

    discovery_parameters = dict(parameters)
    discovery_parameters[Parameters.ACTIVITY_KEY] = activity_key
    discovery_parameters[Parameters.TIMESTAMP_KEY] = timestamp_key
    discovery_parameters[Parameters.CASE_ID_KEY] = case_id_key

    process_tree = inductive_miner.apply(
        event_log, parameters=discovery_parameters, variant=discovery_variant
    )
    net, initial_marking, final_marking = pt_converter.apply(process_tree)

    return event_log, net, initial_marking, final_marking
