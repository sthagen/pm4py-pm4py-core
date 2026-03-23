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
from pm4py.algo.discovery.declare.templates import *
import pandas as pd
from typing import Union, Dict, Optional, Any, Tuple, Collection, Set, List
from typing import Counter as TCounter
from pm4py.util import exec_utils, constants, xes_constants, pandas_utils
from collections import Counter
import numpy as np


class Parameters(Enum):
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY
    CASE_ID_KEY = constants.PARAMETER_CONSTANT_CASEID_KEY
    CONSIDERED_ACTIVITIES = "considered_activities"
    MIN_SUPPORT_RATIO = "min_support_ratio"
    MIN_CONFIDENCE_RATIO = "min_confidence_ratio"
    AUTO_SELECTION_MULTIPLIER = "auto_selection_multiplier"
    ALLOWED_TEMPLATES = "allowed_templates"


def __rule_existence_column(act: str) -> Tuple[str, str]:
    return (EXISTENCE, act)


def __rule_exactly_one_column(act: str) -> Tuple[str, str]:
    return (EXACTLY_ONE, act)


def __rule_init_column(act: str) -> Tuple[str, str]:
    return (INIT, act)


def __rule_responded_existence_column(act: str, act2: str) -> Tuple[str, str, str]:
    return (RESPONDED_EXISTENCE, act, act2)


def __rule_response(act: str, act2: str) -> Tuple[str, str, str]:
    return (RESPONSE, act, act2)


def __rule_precedence(act: str, act2: str) -> Tuple[str, str, str]:
    return (PRECEDENCE, act, act2)


def __rule_succession(act: str, act2: str) -> Tuple[str, str, str]:
    return (SUCCESSION, act, act2)


def __rule_alternate_response(act: str, act2: str) -> Tuple[str, str, str]:
    return (ALTRESPONSE, act, act2)


def __rule_alternate_precedence(act: str, act2: str) -> Tuple[str, str, str]:
    return (ALTPRECEDENCE, act, act2)


def __rule_alternate_succession(act: str, act2: str) -> Tuple[str, str, str]:
    return (ALTSUCCESSION, act, act2)


def __rule_chain_response(act: str, act2: str) -> Tuple[str, str, str]:
    return (CHAINRESPONSE, act, act2)


def __rule_chain_precedence(act: str, act2: str) -> Tuple[str, str, str]:
    return (CHAINPRECEDENCE, act, act2)


def __rule_chain_succession(act: str, act2: str) -> Tuple[str, str, str]:
    return (CHAINSUCCESSION, act, act2)


def __rule_absence_act(act: str) -> Tuple[str, str]:
    return (ABSENCE, act)


def __rule_coexistence(act: str, act2: str) -> Tuple[str, str, str]:
    return (COEXISTENCE, act, act2)


def __rule_non_coexistence(act: str, act2: str) -> Tuple[str, str, str]:
    return (NONCOEXISTENCE, act, act2)


def __rule_non_succession(act: str, act2: str) -> Tuple[str, str, str]:
    return (NONSUCCESSION, act, act2)


def __rule_non_chain_succession(act: str, act2: str) -> Tuple[str, str, str]:
    return (NONCHAINSUCCESSION, act, act2)


def __col_to_dict_rule(
    col_name: Union[Tuple[str, str], Tuple[str, str, str]]
) -> Tuple[str, Any]:
    if len(col_name) == 2:
        return col_name[0], col_name[1]
    else:
        if col_name[2] is None or pd.isna(col_name[2]) or not col_name[2]:
            return col_name[0], col_name[1]
        return col_name[0], (col_name[1], col_name[2])


def __table_nrows(table: Dict[Any, Any]) -> int:
    if not table:
        return 0
    return int(len(next(iter(table.values()))))


def __is_alternate_response_satisfied(
    trace_len: int, act_idxs: Dict[str, List[int]], act: str, act2: str
) -> bool:
    """
    Alternate response(act, act2):
      for each occurrence of act, there exists an occurrence of act2 AFTER it,
      and BEFORE the next occurrence of act (if any).
    Extra act2 occurrences are allowed.
    """
    a_idxs = act_idxs.get(act, [])
    if not a_idxs:
        return True  # vacuous (not activated)
    b_idxs = act_idxs.get(act2, [])
    if not b_idxs:
        return False

    b_ptr = 0
    for i, a in enumerate(a_idxs):
        next_a = a_idxs[i + 1] if i + 1 < len(a_idxs) else trace_len
        while b_ptr < len(b_idxs) and b_idxs[b_ptr] <= a:
            b_ptr += 1
        if b_ptr >= len(b_idxs) or b_idxs[b_ptr] >= next_a:
            return False
    return True


def __is_chain_response_satisfied(
    trace: Collection[str], act_idxs: Dict[str, List[int]], act: str, act2: str
) -> bool:
    """
    Chain response(act, act2):
      for each occurrence of act, act2 occurs IMMEDIATELY after.
    Extra act2 occurrences are allowed.
    """
    a_idxs = act_idxs.get(act, [])
    if not a_idxs:
        return True  # vacuous (not activated)

    trace_list = list(trace)
    n = len(trace_list)
    for a in a_idxs:
        if a + 1 >= n or trace_list[a + 1] != act2:
            return False
    return True


def __is_alternate_precedence_satisfied(
    act_idxs: Dict[str, List[int]], act: str, act2: str
) -> bool:
    """
    Alternate precedence(act, act2):
      for each occurrence of act2, there exists an occurrence of act BEFORE it,
      and AFTER the previous occurrence of act2 (if any).
    Extra act occurrences are allowed.
    """
    b_idxs = act_idxs.get(act2, [])
    if not b_idxs:
        return True  # vacuous (not activated)
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
    trace: Collection[str], act_idxs: Dict[str, List[int]], act: str, act2: str
) -> bool:
    """
    Chain precedence(act, act2):
      for each occurrence of act2, act occurs IMMEDIATELY before.
    Extra act occurrences are allowed.
    """
    b_idxs = act_idxs.get(act2, [])
    if not b_idxs:
        return True  # vacuous (not activated)

    trace_list = list(trace)
    for b in b_idxs:
        if b == 0 or trace_list[b - 1] != act:
            return False
    return True


def existence_template_step1(
    rules: Dict[Union[Tuple[str, str], Tuple[str, str, str]], int],
    trace: Collection[str],
    activities: Set[str],
    act_counter: TCounter[str],
    act_idxs: Dict[str, List[int]],
    allowed_templates: Collection[str],
):
    if EXISTENCE in allowed_templates:
        for act in activities:
            if act in act_counter:
                rules[__rule_existence_column(act)] = 1
            else:
                rules[__rule_existence_column(act)] = -1


def exactly_one_template_step1(
    rules: Dict[Union[Tuple[str, str], Tuple[str, str, str]], int],
    trace: Collection[str],
    activities: Set[str],
    act_counter: TCounter[str],
    act_idxs: Dict[str, List[int]],
    allowed_templates: Collection[str],
):
    # BUGFIX: previously did not mark absence as a violation and could leave 0 values
    # (i.e., "not activated"), which is wrong for a unary constraint like EXACTLY_ONE.
    if EXACTLY_ONE in allowed_templates:
        for act in activities:
            if act_counter.get(act, 0) == 1:
                rules[__rule_exactly_one_column(act)] = 1
            else:
                rules[__rule_exactly_one_column(act)] = -1


def init_template_step1(
    rules: Dict[Union[Tuple[str, str], Tuple[str, str, str]], int],
    trace: Collection[str],
    activities: Set[str],
    act_counter: TCounter[str],
    act_idxs: Dict[str, List[int]],
    allowed_templates: Collection[str],
):
    # BUGFIX: handle empty traces safely
    if INIT in allowed_templates:
        trace_list = list(trace)
        first = trace_list[0] if trace_list else None
        for act in activities:
            if first is not None and act == first:
                rules[__rule_init_column(act)] = 1
            else:
                rules[__rule_init_column(act)] = -1


def responded_existence_template_step1(
    rules: Dict[Union[Tuple[str, str], Tuple[str, str, str]], int],
    trace: Collection[str],
    activities: Set[str],
    act_counter: TCounter[str],
    act_idxs: Dict[str, List[int]],
    allowed_templates: Collection[str],
):
    if RESPONDED_EXISTENCE in allowed_templates:
        for act in act_counter:
            for act2 in activities:
                if act2 != act:
                    if act2 not in act_counter:
                        rules[__rule_responded_existence_column(act, act2)] = -1
                    else:
                        rules[__rule_responded_existence_column(act, act2)] = 1


def response_template_step1(
    rules: Dict[Union[Tuple[str, str], Tuple[str, str, str]], int],
    trace: Collection[str],
    activities: Set[str],
    act_counter: TCounter[str],
    act_idxs: Dict[str, List[int]],
    allowed_templates: Collection[str],
):
    if RESPONSE in allowed_templates:
        for act in act_counter:
            for act2 in activities:
                if act2 != act:
                    if act2 not in act_counter:
                        rules[__rule_response(act, act2)] = -1
                    else:
                        if act_idxs[act][-1] < act_idxs[act2][-1]:
                            rules[__rule_response(act, act2)] = 1
                        else:
                            rules[__rule_response(act, act2)] = -1


def precedence_template_step1(
    rules: Dict[Union[Tuple[str, str], Tuple[str, str, str]], int],
    trace: Collection[str],
    activities: Set[str],
    act_counter: TCounter[str],
    act_idxs: Dict[str, List[int]],
    allowed_templates: Collection[str],
):
    # BUGFIX: previously "pass" when the precedent activity was missing, producing 0
    # and inflating confidence/support in discovery. If B occurs and A is missing,
    # precedence(A,B) is violated.
    if PRECEDENCE in allowed_templates:
        for b in act_counter:  # activation on the consequent (B)
            for a in activities:
                if a != b:
                    if a not in act_counter:
                        rules[__rule_precedence(a, b)] = -1
                    else:
                        rules[__rule_precedence(a, b)] = (
                            1 if act_idxs[a][0] < act_idxs[b][0] else -1
                        )


def altresponse_template_step1(
    rules: Dict[Union[Tuple[str, str], Tuple[str, str, str]], int],
    trace: Collection[str],
    activities: Set[str],
    act_counter: TCounter[str],
    act_idxs: Dict[str, List[int]],
    allowed_templates: Collection[str],
):
    # BUGFIX: previous implementation wrongly required |A| == |B| and penalized extra B's
    if ALTRESPONSE in allowed_templates:
        trace_len = len(list(trace))
        for act in act_counter:  # activation on A
            for act2 in activities:
                if act2 != act:
                    ok = __is_alternate_response_satisfied(trace_len, act_idxs, act, act2)
                    rules[__rule_alternate_response(act, act2)] = 1 if ok else -1


def chainresponse_template_step1(
    rules: Dict[Union[Tuple[str, str], Tuple[str, str, str]], int],
    trace: Collection[str],
    activities: Set[str],
    act_counter: TCounter[str],
    act_idxs: Dict[str, List[int]],
    allowed_templates: Collection[str],
):
    # BUGFIX: previous implementation wrongly required |A| == |B| and penalized extra B's
    if CHAINRESPONSE in allowed_templates:
        trace_list = list(trace)
        for act in act_counter:  # activation on A
            for act2 in activities:
                if act2 != act:
                    ok = __is_chain_response_satisfied(trace_list, act_idxs, act, act2)
                    rules[__rule_chain_response(act, act2)] = 1 if ok else -1


def altprecedence_template_step1(
    rules: Dict[Union[Tuple[str, str], Tuple[str, str, str]], int],
    trace: Collection[str],
    activities: Set[str],
    act_counter: TCounter[str],
    act_idxs: Dict[str, List[int]],
    allowed_templates: Collection[str],
):
    # BUGFIX: previous implementation wrongly required |A| == |B| and penalized extra A's
    # (e.g., A after last B). Alternate precedence is activated by B and only constrains B's.
    if ALTPRECEDENCE in allowed_templates:
        for b in act_counter:  # activation on B
            for a in activities:
                if a != b:
                    ok = __is_alternate_precedence_satisfied(act_idxs, a, b)
                    rules[__rule_alternate_precedence(a, b)] = 1 if ok else -1


def chainprecedence_template_step1(
    rules: Dict[Union[Tuple[str, str], Tuple[str, str, str]], int],
    trace: Collection[str],
    activities: Set[str],
    act_counter: TCounter[str],
    act_idxs: Dict[str, List[int]],
    allowed_templates: Collection[str],
):
    # BUGFIX: previous implementation penalized extra A's (e.g., A after last B).
    # Chain precedence is activated by B and only constrains B's.
    if CHAINPRECEDENCE in allowed_templates:
        trace_list = list(trace)
        for b in act_counter:  # activation on B
            for a in activities:
                if a != b:
                    ok = __is_chain_precedence_satisfied(trace_list, act_idxs, a, b)
                    rules[__rule_chain_precedence(a, b)] = 1 if ok else -1


def absence_template(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if not table:
        return table
    if ABSENCE in allowed_templates and EXISTENCE in allowed_templates:
        for act in activities:
            if __rule_existence_column(act) in table:
                table[__rule_absence_act(act)] = -1 * table[__rule_existence_column(act)]
    return table


def exactly_one_template_step2(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if EXACTLY_ONE in allowed_templates:
        n = __table_nrows(table)
        for act in activities:
            if __rule_exactly_one_column(act) not in table:
                table[__rule_exactly_one_column(act)] = np.zeros(n, dtype=int)
    return table


def responded_existence_template_step2(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if RESPONDED_EXISTENCE in allowed_templates:
        n = __table_nrows(table)
        for act in activities:
            for act2 in activities:
                if act2 != act:
                    if __rule_responded_existence_column(act, act2) not in table:
                        table[__rule_responded_existence_column(act, act2)] = np.zeros(
                            n, dtype=int
                        )
    return table


def response_template_step2(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if RESPONSE in allowed_templates:
        n = __table_nrows(table)
        for act in activities:
            for act2 in activities:
                if act2 != act:
                    if __rule_response(act, act2) not in table:
                        table[__rule_response(act, act2)] = np.zeros(n, dtype=int)
    return table


def precedence_template_step2(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if PRECEDENCE in allowed_templates:
        n = __table_nrows(table)
        for act in activities:
            for act2 in activities:
                if act2 != act:
                    if __rule_precedence(act, act2) not in table:
                        table[__rule_precedence(act, act2)] = np.zeros(n, dtype=int)
    return table


def altresponse_template_step2(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if ALTRESPONSE in allowed_templates:
        n = __table_nrows(table)
        for act in activities:
            for act2 in activities:
                if act2 != act:
                    if __rule_alternate_response(act, act2) not in table:
                        table[__rule_alternate_response(act, act2)] = np.zeros(
                            n, dtype=int
                        )
    return table


def chainresponse_template_step2(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if CHAINRESPONSE in allowed_templates:
        n = __table_nrows(table)
        for act in activities:
            for act2 in activities:
                if act2 != act:
                    if __rule_chain_response(act, act2) not in table:
                        table[__rule_chain_response(act, act2)] = np.zeros(n, dtype=int)
    return table


def altprecedence_template_step2(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if ALTPRECEDENCE in allowed_templates:
        n = __table_nrows(table)
        for act in activities:
            for act2 in activities:
                if act2 != act:
                    if __rule_alternate_precedence(act, act2) not in table:
                        table[__rule_alternate_precedence(act, act2)] = np.zeros(
                            n, dtype=int
                        )
    return table


def chainprecedence_template_step2(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if CHAINPRECEDENCE in allowed_templates:
        n = __table_nrows(table)
        for act in activities:
            for act2 in activities:
                if act2 != act:
                    if __rule_chain_precedence(act, act2) not in table:
                        table[__rule_chain_precedence(act, act2)] = np.zeros(
                            n, dtype=int
                        )
    return table


def succession_template(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if not table:
        return table
    if (
        SUCCESSION in allowed_templates
        and RESPONSE in allowed_templates
        and PRECEDENCE in allowed_templates
    ):
        for act in activities:
            for act2 in activities:
                if act2 != act:
                    table[__rule_succession(act, act2)] = np.minimum(
                        table[__rule_response(act, act2)],
                        table[__rule_precedence(act, act2)],
                    )
    return table


def altsuccession_template(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if not table:
        return table
    if (
        ALTSUCCESSION in allowed_templates
        and ALTRESPONSE in allowed_templates
        and ALTPRECEDENCE in allowed_templates
    ):
        for act in activities:
            for act2 in activities:
                if act2 != act:
                    table[__rule_alternate_succession(act, act2)] = np.minimum(
                        table[__rule_alternate_response(act, act2)],
                        table[__rule_alternate_precedence(act, act2)],
                    )
    return table


def chainsuccession_template(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if not table:
        return table
    if (
        CHAINSUCCESSION in allowed_templates
        and CHAINRESPONSE in allowed_templates
        and CHAINPRECEDENCE in allowed_templates
    ):
        for act in activities:
            for act2 in activities:
                if act2 != act:
                    table[__rule_chain_succession(act, act2)] = np.minimum(
                        table[__rule_chain_response(act, act2)],
                        table[__rule_chain_precedence(act, act2)],
                    )
    return table


def coexistence_template(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if not table:
        return table
    if COEXISTENCE in allowed_templates and RESPONDED_EXISTENCE in allowed_templates:
        for act in activities:
            for act2 in activities:
                if act2 != act:
                    table[__rule_coexistence(act, act2)] = np.minimum(
                        table[__rule_responded_existence_column(act, act2)],
                        table[__rule_responded_existence_column(act2, act)],
                    )
    return table


def noncoexistence_template(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if not table:
        return table
    if (
        NONCOEXISTENCE in allowed_templates
        and COEXISTENCE in allowed_templates
        and RESPONDED_EXISTENCE in allowed_templates
    ):
        for act in activities:
            for act2 in activities:
                if act2 != act:
                    table[__rule_non_coexistence(act, act2)] = -1 * table[
                        __rule_coexistence(act, act2)
                    ]
    return table


def nonsuccession_template(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if not table:
        return table
    if (
        NONSUCCESSION in allowed_templates
        and SUCCESSION in allowed_templates
        and RESPONSE in allowed_templates
        and PRECEDENCE in allowed_templates
    ):
        for act in activities:
            for act2 in activities:
                if act2 != act:
                    table[__rule_non_succession(act, act2)] = -1 * table[
                        __rule_succession(act, act2)
                    ]
    return table


def nonchainsuccession_template(
    table,
    columns: Collection[str],
    activities: Set[str],
    allowed_templates: Collection[str],
) -> pd.DataFrame:
    if not table:
        return table
    if (
        NONCHAINSUCCESSION in allowed_templates
        and CHAINSUCCESSION in allowed_templates
        and CHAINRESPONSE in allowed_templates
        and CHAINPRECEDENCE in allowed_templates
    ):
        for act in activities:
            for act2 in activities:
                if act2 != act:
                    table[__rule_non_chain_succession(act, act2)] = -1 * table[
                        __rule_chain_succession(act, act2)
                    ]
    return table


def form_rules_table(
    log: Union[EventLog, pd.DataFrame],
    parameters: Optional[Dict[Any, Any]] = None,
) -> pd.DataFrame:
    if parameters is None:
        parameters = {}

    activity_key = exec_utils.get_param_value(
        Parameters.ACTIVITY_KEY, parameters, xes_constants.DEFAULT_NAME_KEY
    )
    case_id_key = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, constants.CASE_CONCEPT_NAME
    )

    allowed_templates = exec_utils.get_param_value(
        Parameters.ALLOWED_TEMPLATES, parameters, None
    )

    if allowed_templates is None:
        # BUGFIX: include negative templates as documented/implemented
        allowed_templates = {
            EXISTENCE,
            EXACTLY_ONE,
            INIT,
            RESPONDED_EXISTENCE,
            RESPONSE,
            PRECEDENCE,
            SUCCESSION,
            ALTRESPONSE,
            ALTPRECEDENCE,
            ALTSUCCESSION,
            CHAINRESPONSE,
            CHAINPRECEDENCE,
            CHAINSUCCESSION,
            ABSENCE,
            COEXISTENCE,
            NONCOEXISTENCE,
            NONSUCCESSION,
            NONCHAINSUCCESSION,
        }

    import pm4py

    projected_log = pm4py.project_on_event_attribute(
        log, activity_key, case_id_key=case_id_key
    )
    activities = exec_utils.get_param_value(
        Parameters.CONSIDERED_ACTIVITIES, parameters, None
    )

    if activities is None:
        activities = set(y for x in projected_log for y in x)

    allowed_templates = set(allowed_templates)
    activities = set(activities)

    # If there are no considered activities or no traces, return an empty dataframe safely.
    if not activities or projected_log is None or len(projected_log) == 0:
        return pandas_utils.instantiate_dataframe({})

    vars = Counter([tuple([y for y in x if y in activities]) for x in projected_log])
    table = []

    for trace, occs in vars.items():
        act_counter = Counter(trace)
        act_idxs = {x: [] for x in set(trace)}

        for idx, act in enumerate(trace):
            act_idxs[act].append(idx)

        rules = {}

        existence_template_step1(
            rules, trace, activities, act_counter, act_idxs, allowed_templates
        )
        exactly_one_template_step1(
            rules, trace, activities, act_counter, act_idxs, allowed_templates
        )
        init_template_step1(rules, trace, activities, act_counter, act_idxs, allowed_templates)
        responded_existence_template_step1(
            rules, trace, activities, act_counter, act_idxs, allowed_templates
        )
        response_template_step1(
            rules, trace, activities, act_counter, act_idxs, allowed_templates
        )
        precedence_template_step1(
            rules, trace, activities, act_counter, act_idxs, allowed_templates
        )
        altresponse_template_step1(
            rules, trace, activities, act_counter, act_idxs, allowed_templates
        )
        chainresponse_template_step1(
            rules, trace, activities, act_counter, act_idxs, allowed_templates
        )
        altprecedence_template_step1(
            rules, trace, activities, act_counter, act_idxs, allowed_templates
        )
        chainprecedence_template_step1(
            rules, trace, activities, act_counter, act_idxs, allowed_templates
        )

        for _ in range(occs):
            table.append(rules)

    if not table:
        return pandas_utils.instantiate_dataframe({})

    columns = set(y for x in table for y in x.keys())
    table2 = {c: [] for c in columns}
    for i in range(len(table)):
        trace = table[i]
        for c in columns:
            table2[c].append(trace.get(c, 0))

    for c in table2:
        table2[c] = np.array(table2[c], dtype=int)

    table2 = absence_template(table2, columns, activities, allowed_templates)
    table2 = exactly_one_template_step2(table2, columns, activities, allowed_templates)
    table2 = responded_existence_template_step2(
        table2, columns, activities, allowed_templates
    )
    table2 = response_template_step2(table2, columns, activities, allowed_templates)
    table2 = precedence_template_step2(table2, columns, activities, allowed_templates)
    table2 = altresponse_template_step2(table2, columns, activities, allowed_templates)
    table2 = chainresponse_template_step2(table2, columns, activities, allowed_templates)
    table2 = altprecedence_template_step2(table2, columns, activities, allowed_templates)
    table2 = chainprecedence_template_step2(table2, columns, activities, allowed_templates)

    table2 = succession_template(table2, columns, activities, allowed_templates)
    table2 = altsuccession_template(table2, columns, activities, allowed_templates)
    table2 = chainsuccession_template(table2, columns, activities, allowed_templates)
    table2 = coexistence_template(table2, columns, activities, allowed_templates)
    table2 = noncoexistence_template(table2, columns, activities, allowed_templates)
    table2 = nonsuccession_template(table2, columns, activities, allowed_templates)
    table2 = nonchainsuccession_template(table2, columns, activities, allowed_templates)

    return pandas_utils.instantiate_dataframe(table2)


def get_rules_from_rules_df(
    rules_df, parameters: Optional[Dict[Any, Any]] = None
) -> Dict[str, Dict[Any, Dict[str, int]]]:
    if parameters is None:
        parameters = {}

    # BUGFIX: handle empty / None dataframes safely and handle partial threshold specification
    if rules_df is None or len(rules_df) == 0:
        return {}

    min_support_ratio = exec_utils.get_param_value(
        Parameters.MIN_SUPPORT_RATIO, parameters, None
    )
    min_confidence_ratio = exec_utils.get_param_value(
        Parameters.MIN_CONFIDENCE_RATIO, parameters, None
    )
    rules = {}

    if min_support_ratio is None and min_confidence_ratio is None:
        # auto determine the minimum support and confidence ratio by
        # identifying the values for the best feature
        auto_selection_multiplier = exec_utils.get_param_value(
            Parameters.AUTO_SELECTION_MULTIPLIER, parameters, 0.8
        )
        cols_prod = []
        for col_name in rules_df:
            col = rules_df[col_name]
            supp = len(col[col != 0])
            supp_ratio = float(supp) / float(len(rules_df)) if len(rules_df) > 0 else 0.0
            if supp_ratio > 0:
                conf_ratio = float(len(col[col == 1])) / float(supp)
                prod = supp_ratio * conf_ratio
                cols_prod.append((col_name, prod))
        if not cols_prod:
            return {}
        cols_prod = sorted(cols_prod, key=lambda x: (x[1], x[0]), reverse=True)
        col = rules_df[cols_prod[0][0]]
        supp = len(col[col != 0])
        min_support_ratio = float(supp) / float(len(rules_df)) * auto_selection_multiplier
        min_confidence_ratio = (
            float(len(col[col == 1])) / float(supp) * auto_selection_multiplier
            if supp > 0
            else 1.0
        )

    # If one of the two is provided and the other is not, interpret missing as "no filter"
    if min_support_ratio is None:
        min_support_ratio = 0.0
    if min_confidence_ratio is None:
        min_confidence_ratio = 0.0

    for col_name in rules_df:
        col = rules_df[col_name]
        supp = len(col[col != 0])

        if supp >= len(rules_df) * float(min_support_ratio):
            conf = len(col[col == 1])

            if supp == 0:
                continue
            if conf >= supp * float(min_confidence_ratio):
                rule, key = __col_to_dict_rule(col_name)
                if rule not in rules:
                    rules[rule] = {}
                rules[rule][key] = {"support": supp, "confidence": conf}

    return rules


def apply(
    log: Union[EventLog, pd.DataFrame],
    parameters: Optional[Dict[Any, Any]] = None,
) -> Dict[str, Dict[Any, Dict[str, int]]]:
    """
    Discovers a DECLARE model from the provided event log.

    Paper:
    F. M. Maggi, A. J. Mooij and W. M. P. van der Aalst, "User-guided discovery of declarative process models," 2011 IEEE Symposium on Computational Intelligence and Data Mining (CIDM), Paris, France, 2011, pp. 192-199, doi: 10.1109/CIDM.2011.5949297.

    Parameters
    ----------
    log
        Log object (EventLog, Pandas table)
    parameters
        Possible parameters of the algorithm, including:

        - Parameters.ACTIVITY_KEY
        - Parameters.CONSIDERED_ACTIVITIES
        - Parameters.MIN_SUPPORT_RATIO
        - Parameters.MIN_CONFIDENCE_RATIO
        - Parameters.AUTO_SELECTION_MULTIPLIER
        - Parameters.ALLOWED_TEMPLATES: collection of templates to consider, including:

          * existence
          * exactly_one
          * init
          * responded_existence
          * response
          * precedence
          * succession
          * altresponse
          * altprecedence
          * altsuccession
          * chainresponse
          * chainprecedence
          * chainsuccession
          * absence
          * coexistence
          * noncoexistence
          * nonsuccession
          * nonchainsuccession

    Returns
    -------
    declare_model
        DECLARE model (as Python dictionary), where each template is associated with its own rules
    """
    if parameters is None:
        parameters = {}

    rules_df = form_rules_table(log, parameters=parameters)
    rules = get_rules_from_rules_df(rules_df, parameters=parameters)
    return rules
