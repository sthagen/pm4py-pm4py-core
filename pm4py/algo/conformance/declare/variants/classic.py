'''
    PM4Py – A Process Mining Library for Python
Copyright (C) 2024 Process Intelligence Solutions UG (haftungsbeschränkt)

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
from pm4py.objects.log.obj import EventLog
import pandas as pd
from typing import Union, Dict, Optional, Any, List
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.algo.discovery.declare.templates import *
from pm4py.util import exec_utils, constants, xes_constants, pandas_utils
from collections import Counter


class Parameters(Enum):
    CASE_ID_KEY = constants.PARAMETER_CONSTANT_CASEID_KEY
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY


def __is_alt_response_satisfied(
    trace: List[str], act_idxs: Dict[str, List[int]], act: str, act2: str
) -> bool:
    """
    Alternate response(act, act2):
      for each occurrence of act, there exists an occurrence of act2 AFTER it,
      and BEFORE the next occurrence of act (if any).
    Vacuously satisfied if act does not occur.
    """
    a_idxs = act_idxs.get(act, [])
    if not a_idxs:
        return True
    b_idxs = act_idxs.get(act2, [])
    if not b_idxs:
        return False

    b_ptr = 0
    n = len(trace)
    for i, a in enumerate(a_idxs):
        next_a = a_idxs[i + 1] if i + 1 < len(a_idxs) else n
        while b_ptr < len(b_idxs) and b_idxs[b_ptr] <= a:
            b_ptr += 1
        if b_ptr >= len(b_idxs) or b_idxs[b_ptr] >= next_a:
            return False
    return True


def __is_chain_response_satisfied(
    trace: List[str], act_idxs: Dict[str, List[int]], act: str, act2: str
) -> bool:
    """
    Chain response(act, act2):
      for each occurrence of act, act2 occurs immediately after.
    Vacuously satisfied if act does not occur.
    """
    a_idxs = act_idxs.get(act, [])
    if not a_idxs:
        return True
    n = len(trace)
    for a in a_idxs:
        if a + 1 >= n or trace[a + 1] != act2:
            return False
    return True


def __is_alt_precedence_satisfied(
    trace: List[str], act_idxs: Dict[str, List[int]], act: str, act2: str
) -> bool:
    """
    Alternate precedence(act, act2):
      for each occurrence of act2, there exists an occurrence of act BEFORE it,
      and AFTER the previous occurrence of act2 (if any).
    Vacuously satisfied if act2 does not occur.
    """
    b_idxs = act_idxs.get(act2, [])
    if not b_idxs:
        return True
    a_idxs = act_idxs.get(act, [])
    if not a_idxs:
        return False

    a_ptr = 0
    prev_b = -1
    for b in b_idxs:
        while a_ptr < len(a_idxs) and a_idxs[a_ptr] <= prev_b:
            a_ptr += 1
        if a_ptr >= len(a_idxs) or a_idxs[a_ptr] >= b:
            return False
        prev_b = b
    return True


def __is_chain_precedence_satisfied(
    trace: List[str], act_idxs: Dict[str, List[int]], act: str, act2: str
) -> bool:
    """
    Chain precedence(act, act2):
      for each occurrence of act2, act occurs immediately before.
    Vacuously satisfied if act2 does not occur.
    """
    b_idxs = act_idxs.get(act2, [])
    if not b_idxs:
        return True
    for b in b_idxs:
        if b == 0 or trace[b - 1] != act:
            return False
    return True


def __check_existence(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if EXISTENCE in model:
        for act in model[EXISTENCE]:
            if act not in trace:
                trace_dict["deviations"].append([EXISTENCE, act])


def __check_absence(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if ABSENCE in model:
        for act in model[ABSENCE]:
            if act in trace:
                trace_dict["deviations"].append([ABSENCE, act])


def __check_exactly_one(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if EXACTLY_ONE in model:
        trace_counter = Counter(trace)
        for act in model[EXACTLY_ONE]:
            if trace_counter[act] != 1:
                trace_dict["deviations"].append([EXACTLY_ONE, act])


def __check_init(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if INIT in model:
        for act in model[INIT]:
            if len(trace) == 0 or trace[0] != act:
                trace_dict["deviations"].append([INIT, act])


def __check_responded_existence(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if RESPONDED_EXISTENCE in model:
        for act_couple in model[RESPONDED_EXISTENCE]:
            if act_couple[0] in trace and act_couple[1] not in trace:
                trace_dict["deviations"].append([RESPONDED_EXISTENCE, act_couple])


def __check_coexistence(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if COEXISTENCE in model:
        for act_couple in model[COEXISTENCE]:
            if (act_couple[0] in trace and act_couple[1] not in trace) or (
                act_couple[1] in trace and act_couple[0] not in trace
            ):
                trace_dict["deviations"].append([COEXISTENCE, act_couple])


def __check_non_coexistence(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if NONCOEXISTENCE in model:
        for act_couple in model[NONCOEXISTENCE]:
            if act_couple[0] in trace and act_couple[1] in trace:
                trace_dict["deviations"].append([NONCOEXISTENCE, act_couple])


def __check_response(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    act_idxs: Dict[str, List[int]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if RESPONSE in model:
        for act_couple in model[RESPONSE]:
            if act_couple[0] in act_idxs:
                if (act_couple[1] not in act_idxs) or max(
                    act_idxs[act_couple[0]]
                ) > max(act_idxs[act_couple[1]]):
                    trace_dict["deviations"].append([RESPONSE, act_couple])


def __check_precedence(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    act_idxs: Dict[str, List[int]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if PRECEDENCE in model:
        for act_couple in model[PRECEDENCE]:
            if act_couple[1] in act_idxs:
                if (act_couple[0] not in act_idxs) or min(
                    act_idxs[act_couple[0]]
                ) > min(act_idxs[act_couple[1]]):
                    trace_dict["deviations"].append([PRECEDENCE, act_couple])


def __check_succession(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    act_idxs: Dict[str, List[int]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    # Do not report deviations when BOTH activities are absent (classic "inactive" case)
    if SUCCESSION in model:
        for act_couple in model[SUCCESSION]:
            a_in = act_couple[0] in act_idxs
            b_in = act_couple[1] in act_idxs

            if not a_in and not b_in:
                continue

            if (not a_in) or (not b_in):
                trace_dict["deviations"].append([SUCCESSION, act_couple])
                continue

            if min(act_idxs[act_couple[0]]) > min(act_idxs[act_couple[1]]) or max(
                act_idxs[act_couple[0]]
            ) > max(act_idxs[act_couple[1]]):
                trace_dict["deviations"].append([SUCCESSION, act_couple])


def __check_alt_response(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    act_idxs: Dict[str, List[int]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if ALTRESPONSE in model:
        for act_couple in model[ALTRESPONSE]:
            if not __is_alt_response_satisfied(
                trace, act_idxs, act_couple[0], act_couple[1]
            ):
                trace_dict["deviations"].append([ALTRESPONSE, act_couple])


def __check_chain_response(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    act_idxs: Dict[str, List[int]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if CHAINRESPONSE in model:
        for act_couple in model[CHAINRESPONSE]:
            if not __is_chain_response_satisfied(
                trace, act_idxs, act_couple[0], act_couple[1]
            ):
                trace_dict["deviations"].append([CHAINRESPONSE, act_couple])


def __check_alt_precedence(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    act_idxs: Dict[str, List[int]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if ALTPRECEDENCE in model:
        for act_couple in model[ALTPRECEDENCE]:
            if not __is_alt_precedence_satisfied(
                trace, act_idxs, act_couple[0], act_couple[1]
            ):
                trace_dict["deviations"].append([ALTPRECEDENCE, act_couple])


def __check_chain_precedence(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    act_idxs: Dict[str, List[int]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if CHAINPRECEDENCE in model:
        for act_couple in model[CHAINPRECEDENCE]:
            if not __is_chain_precedence_satisfied(
                trace, act_idxs, act_couple[0], act_couple[1]
            ):
                trace_dict["deviations"].append([CHAINPRECEDENCE, act_couple])


def __check_alt_succession(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    act_idxs: Dict[str, List[int]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if ALTSUCCESSION in model:
        for act_couple in model[ALTSUCCESSION]:
            ok = __is_alt_response_satisfied(
                trace, act_idxs, act_couple[0], act_couple[1]
            ) and __is_alt_precedence_satisfied(
                trace, act_idxs, act_couple[0], act_couple[1]
            )
            if not ok:
                trace_dict["deviations"].append([ALTSUCCESSION, act_couple])


def __check_chain_succession(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    act_idxs: Dict[str, List[int]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if CHAINSUCCESSION in model:
        for act_couple in model[CHAINSUCCESSION]:
            ok = __is_chain_response_satisfied(
                trace, act_idxs, act_couple[0], act_couple[1]
            ) and __is_chain_precedence_satisfied(
                trace, act_idxs, act_couple[0], act_couple[1]
            )
            if not ok:
                trace_dict["deviations"].append([CHAINSUCCESSION, act_couple])


# =========================
# FIXED: NONSUCCESSION / NONCHAINSUCCESSION
# Align conformance with classic discovery, where they are computed as:
#   nonsuccession = -succession
#   nonchainsuccession = -chainsuccession
# =========================

def __check_non_succession(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    act_idxs: Dict[str, List[int]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if NONSUCCESSION in model:
        for act_couple in model[NONSUCCESSION]:
            a, b = act_couple
            a_in = a in act_idxs
            b_in = b in act_idxs

            # in classic discovery: succession(a,b)=0 only when both are absent => nonsuccession(a,b)=0
            if not a_in and not b_in:
                continue

            # nonsuccession(a,b) is violated iff succession(a,b) is satisfied
            # succession satisfied iff both present AND precedence satisfied AND response satisfied
            if a_in and b_in:
                precedence_ok = min(act_idxs[a]) < min(act_idxs[b])
                response_ok = max(act_idxs[a]) < max(act_idxs[b])
                if precedence_ok and response_ok:
                    trace_dict["deviations"].append([NONSUCCESSION, act_couple])


def __check_non_chain_succession(
    trace: List[str],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    trace_dict: Dict[str, List[Any]],
    act_idxs: Dict[str, List[int]],
    parameters: Optional[Dict[Any, Any]] = None,
):
    if NONCHAINSUCCESSION in model:
        for act_couple in model[NONCHAINSUCCESSION]:
            a, b = act_couple
            a_in = a in act_idxs
            b_in = b in act_idxs

            # inactive case (classic discovery yields 0)
            if not a_in and not b_in:
                continue

            # nonchainsuccession(a,b) is violated iff chainsuccession(a,b) is satisfied.
            # chainsuccession satisfied requires BOTH activities to occur and:
            #   chainresponse(a,b) satisfied AND chainprecedence(a,b) satisfied
            if a_in and b_in:
                if __is_chain_response_satisfied(trace, act_idxs, a, b) and __is_chain_precedence_satisfied(
                    trace, act_idxs, a, b
                ):
                    trace_dict["deviations"].append([NONCHAINSUCCESSION, act_couple])


def apply_list(
    projected_log: List[List[str]],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    parameters: Optional[Dict[Any, Any]] = None,
) -> List[Dict[str, Any]]:
    if parameters is None:
        parameters = {}

    conf_cases = []

    total_num_constraints = 0
    for k in model:
        total_num_constraints += len(model[k])

    for trace in projected_log:
        act_idxs: Dict[str, List[int]] = {}
        for i in range(len(trace)):
            act_idxs.setdefault(trace[i], []).append(i)

        ret: Dict[str, Any] = {}
        ret["no_constr_total"] = total_num_constraints
        ret["deviations"] = []

        __check_existence(trace, model, ret, parameters)
        __check_exactly_one(trace, model, ret, parameters)
        __check_init(trace, model, ret, parameters)
        __check_responded_existence(trace, model, ret, parameters)
        __check_coexistence(trace, model, ret, parameters)
        __check_non_coexistence(trace, model, ret, parameters)
        __check_response(trace, model, ret, act_idxs, parameters)
        __check_precedence(trace, model, ret, act_idxs, parameters)
        __check_succession(trace, model, ret, act_idxs, parameters)
        __check_alt_response(trace, model, ret, act_idxs, parameters)
        __check_chain_response(trace, model, ret, act_idxs, parameters)
        __check_alt_precedence(trace, model, ret, act_idxs, parameters)
        __check_chain_precedence(trace, model, ret, act_idxs, parameters)
        __check_alt_succession(trace, model, ret, act_idxs, parameters)
        __check_chain_succession(trace, model, ret, act_idxs, parameters)
        __check_absence(trace, model, ret, parameters)

        # Fixed + aligned with discovery:
        __check_non_succession(trace, model, ret, act_idxs, parameters)
        __check_non_chain_succession(trace, model, ret, act_idxs, parameters)

        ret["no_dev_total"] = len(ret["deviations"])
        ret["dev_fitness"] = (
            1.0 - ret["no_dev_total"] / ret["no_constr_total"]
            if ret["no_constr_total"] > 0
            else 1.0
        )
        ret["is_fit"] = ret["no_dev_total"] == 0

        conf_cases.append(ret)

    return conf_cases


def apply(
    log: Union[EventLog, pd.DataFrame],
    model: Dict[str, Dict[Any, Dict[str, int]]],
    parameters: Optional[Dict[Any, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Applies conformance checking against a DECLARE model.
    """
    if parameters is None:
        parameters = {}

    activity_key = exec_utils.get_param_value(
        Parameters.ACTIVITY_KEY, parameters, xes_constants.DEFAULT_NAME_KEY
    )
    case_id_key = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, constants.CASE_CONCEPT_NAME
    )

    import pm4py

    projected_log = pm4py.project_on_event_attribute(
        log, activity_key, case_id_key=case_id_key
    )

    ret = apply_list(projected_log, model, parameters=parameters)
    return ret


def get_diagnostics_dataframe(log, conf_result, parameters=None) -> pd.DataFrame:
    """
    Gets the diagnostics dataframe from a log and the results
    of DECLARE-based conformance checking
    """
    if parameters is None:
        parameters = {}

    case_id_key = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, xes_constants.DEFAULT_TRACEID_KEY
    )

    log = log_converter.apply(
        log, variant=log_converter.Variants.TO_EVENT_LOG, parameters=parameters
    )

    diagn_stream = []

    for index in range(len(log)):
        case_id = log[index].attributes[case_id_key]

        no_dev_total = conf_result[index]["no_dev_total"]
        no_constr_total = conf_result[index]["no_constr_total"]
        dev_fitness = conf_result[index]["dev_fitness"]

        diagn_stream.append(
            {
                "case_id": case_id,
                "no_dev_total": no_dev_total,
                "no_constr_total": no_constr_total,
                "dev_fitness": dev_fitness,
            }
        )

    return pandas_utils.instantiate_dataframe(diagn_stream)
