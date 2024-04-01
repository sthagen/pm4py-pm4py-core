from pm4py.util import exec_utils
from enum import Enum
from typing import Optional, Dict, Any, Tuple


class Parameters(Enum):
    INCLUDE_HEADER = "include_header"


def get_model_description():
    description = "The temporal profile is a model describing the average and the standard deviation of the times between couples of activities eventually (not only directly) following each other in at least a process execution (so in a trace <A,B,C,D> the couples (A,B) (A,C) (A,D) (B,C) (B,D) (C,D) shall be considered). Given a positive value ZETA, a deviation occurs in a process execution when the time between two activities is lower than AVG - ZETA * STDEV or greater than AVG + ZETA * STDEV.\n"
    return description


def get_model_implementation():
    implementation = "The temporal profile is expressed as a Python dictionary associating to some couples of activities the average and the standard deviation of the times. Example: {('A', 'B'): (86400, 3600), ('B', 'C'): (3600, 3600)} indicates that the average time between A and B is 1 day, while the standard deviation is 1 hour. On the other hand, the average time between B and C is 1 hour, while the standard deviation is 1 hour."
    return implementation


def apply(temporal_profile: Dict[Tuple[str, str], Tuple[float, float]],
          parameters: Optional[Dict[Any, Any]] = None) -> str:
    """
    Abstracts a temporal profile model to a string.

    Parameters
    ----------------
    temporal_profile
        Temporal profile
    parameters
        Parameters of the method, including:
        - Parameters.INCLUDE_HEADER => includes the header in the response

    Returns
    ----------------
    text_abstr
        Textual abstraction of the log skeleton
    """
    if parameters is None:
        parameters = {}

    include_header = exec_utils.get_param_value(Parameters.INCLUDE_HEADER, parameters, True)

    ret = ["\n"]

    if include_header:
        ret.append(get_model_description() + "For this process, the model is:\n")

    for act_couple, agg in temporal_profile.items():
        ret.append("%s -> %s :  AVG: %.2f s  STD: %.2f s" % (act_couple[0], act_couple[1], agg[0], agg[1]))

    return "\n".join(ret)
