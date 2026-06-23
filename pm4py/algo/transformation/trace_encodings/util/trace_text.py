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
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from pm4py.objects.conversion.log import converter as log_converter
from pm4py.objects.log.obj import EventLog, EventStream, Trace, Event
from pm4py.util import constants, exec_utils, xes_constants


class Parameters(Enum):
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY
    ATTRIBUTE_KEY = constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY
    CASE_ID_KEY = constants.PARAMETER_CONSTANT_CASEID_KEY
    EVENT_ATTRIBUTES = "event_attributes"
    TRACE_ATTRIBUTES = "trace_attributes"
    INCLUDE_ATTRIBUTE_NAMES = "include_attribute_names"
    COMBINE_EVENT_ATTRIBUTES = "combine_event_attributes"
    MISSING_VALUE = "missing_value"


def get_event_attributes(
    parameters: Optional[Dict[Any, Any]] = None,
) -> List[str]:
    """
    Gets the event attributes used to build each event token.
    """
    if parameters is None:
        parameters = {}

    activity_key = exec_utils.get_param_value(
        Parameters.ACTIVITY_KEY, parameters, xes_constants.DEFAULT_NAME_KEY
    )
    attribute_key = exec_utils.get_param_value(
        Parameters.ATTRIBUTE_KEY, parameters, activity_key
    )
    event_attributes = exec_utils.get_param_value(
        Parameters.EVENT_ATTRIBUTES, parameters, None
    )

    if event_attributes is None:
        event_attributes = [attribute_key]
    elif isinstance(event_attributes, str):
        event_attributes = [event_attributes]
    else:
        event_attributes = list(event_attributes)

    return event_attributes


def get_trace_attributes(
    parameters: Optional[Dict[Any, Any]] = None,
) -> List[str]:
    """
    Gets trace-level attributes to add as case context tokens.
    """
    if parameters is None:
        parameters = {}

    trace_attributes = exec_utils.get_param_value(
        Parameters.TRACE_ATTRIBUTES, parameters, []
    )
    if isinstance(trace_attributes, str):
        trace_attributes = [trace_attributes]

    return list(trace_attributes)


def format_event_tokens(
    event: Event,
    event_attributes: List[str],
    parameters: Optional[Dict[Any, Any]] = None,
) -> List[str]:
    """
    Formats one event as one or more textual tokens.
    """
    if parameters is None:
        parameters = {}

    include_attribute_names = exec_utils.get_param_value(
        Parameters.INCLUDE_ATTRIBUTE_NAMES, parameters, len(event_attributes) > 1
    )
    combine_event_attributes = exec_utils.get_param_value(
        Parameters.COMBINE_EVENT_ATTRIBUTES, parameters, True
    )
    missing_value = exec_utils.get_param_value(
        Parameters.MISSING_VALUE, parameters, "UNDEFINED"
    )

    tokens = []
    for attr in event_attributes:
        value = event[attr] if attr in event else missing_value
        if include_attribute_names:
            tokens.append(str(attr) + "=" + str(value))
        else:
            tokens.append(str(value))

    if combine_event_attributes:
        return ["|".join(tokens)]
    return tokens


def trace_to_tokens(
    trace: Trace,
    parameters: Optional[Dict[Any, Any]] = None,
) -> List[str]:
    """
    Converts a trace to a sequence of tokens.
    """
    if parameters is None:
        parameters = {}

    event_attributes = get_event_attributes(parameters)
    trace_attributes = get_trace_attributes(parameters)
    missing_value = exec_utils.get_param_value(
        Parameters.MISSING_VALUE, parameters, "UNDEFINED"
    )

    tokens = []
    for attr in trace_attributes:
        if attr in trace.attributes:
            value = trace.attributes[attr]
        elif attr.startswith(constants.CASE_ATTRIBUTE_PREFIX) and attr[
            len(constants.CASE_ATTRIBUTE_PREFIX) :
        ] in trace.attributes:
            value = trace.attributes[
                attr[len(constants.CASE_ATTRIBUTE_PREFIX) :]
            ]
        else:
            value = missing_value
        tokens.append("trace:" + str(attr) + "=" + str(value))

    for event in trace:
        tokens.extend(format_event_tokens(event, event_attributes, parameters))

    return tokens


def log_to_trace_tokens(
    log: Union[EventLog, EventStream, pd.DataFrame],
    parameters: Optional[Dict[Any, Any]] = None,
) -> Tuple[List[Any], List[List[str]]]:
    """
    Converts a log to case identifiers and trace token sequences.
    """
    if parameters is None:
        parameters = {}

    case_id_key = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, xes_constants.DEFAULT_TRACEID_KEY
    )

    log = log_converter.apply(
        log, variant=log_converter.Variants.TO_EVENT_LOG, parameters=parameters
    )

    case_ids = []
    trace_tokens = []
    for index, trace in enumerate(log):
        case_id = trace.attributes.get(case_id_key, None)
        if case_id is None and str(case_id_key).startswith(
            constants.CASE_ATTRIBUTE_PREFIX
        ):
            case_id = trace.attributes.get(
                str(case_id_key)[len(constants.CASE_ATTRIBUTE_PREFIX) :],
                None,
            )
        if case_id is None:
            case_id = trace.attributes.get(xes_constants.DEFAULT_TRACEID_KEY, index)
        case_ids.append(case_id)
        trace_tokens.append(trace_to_tokens(trace, parameters=parameters))

    return case_ids, trace_tokens


def tokens_to_sentence(tokens: List[str]) -> str:
    """
    Converts trace tokens to a sentence consumed by text embedding models.
    """
    return " ".join(tokens)
