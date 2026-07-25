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

import copy
import importlib.util
import time
from enum import Enum
from typing import Tuple, List, Union, Dict, Any, Optional
import importlib.util
import multiprocessing as mp
import pandas as pd

from pm4py import util as pmutil, ProcessTree
from pm4py.algo.discovery.local_process_models.metrics.quality_metrics import evaluate_tree, LocalProcessModelStats
from pm4py.objects.log.obj import EventLog
from pm4py.objects.process_tree.obj import Operator
from pm4py.stats import get_event_attribute_values
from pm4py.util import constants
from pm4py.util import exec_utils
from pm4py.util import xes_constants as xes_util


class Parameters(Enum):
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY
    TIMESTAMP_KEY = constants.PARAMETER_CONSTANT_TIMESTAMP_KEY
    CASE_ID_KEY = constants.PARAMETER_CONSTANT_CASEID_KEY

    FREQUENCY_THRESHOLD = "lpm_frequency_threshold"
    DETERMINISM_THRESHOLD = "lpm_determinism_threshold"

    CONFIDENCE_THRESHOLD = "lpm_confidence_threshold"
    LANGUAGE_FIT_THRESHOLD = "lpm_language_fit_threshold"
    COVERAGE_THRESHOLD = "lpm_coverage_threshold"

    MAX_ITERATIONS = "max_iterations"
    MAX_NUMBER_OF_MODELS = "max_number_of_models"
    TIME_LIMIT = "time_limit"

    MULTI_PROCESSING = "multi_processing"
    PROGRESS_BAR_TYPE = "progress_bar_type"

def apply(
        log: Union[EventLog, pd.DataFrame],
        selected_activities: Union[None, list],
        parameters: Optional[Dict[Any, Any]]
) -> List[Tuple[ProcessTree, LocalProcessModelStats]]:
    """
    Discovers Local Process Models with the algorithm described in [1]_.

    Local Process Models aim to find frequent and recurring patterns
    describing parts the event log, usually focusing on a subset of activities.

    In contrast to episode and sequential pattern mining, Local Process Models
    are represented by Process Trees and can therefore model loops and
    exclusive choices alongside sequences and concurrency which the Episode Miner
    can find as well [2]_.

    The algorithm returns multiple Local Process Models that can be evaluated
    based on the five quality metrics introduced in the paper.
    The values of all five metrics are between 0 and 1.
    Here, instead of relying on the support metric, which scales the
    frequency to [0, 1), we instead directly expose the frequency.

    - **Frequency**: Measures how often a Local Process Model is executed in the event log. Note that per trace the model can be executed multiple times.
    - **Confidence**: Measures, per activity in the model, the ratio of events which are part of model executions. The harmonic mean over all activities in the model in returned.
    - **Language fit**: Describes the precision of the model by calculating how many of the allowed traces in the Local Process Model are actually executed.
    - **Determinism**: Measures the amount of choices in the state space of the model. Fewer choices lead to higher determinism values.
    - **Coverage**: The ratio of events in the log that stem from activities used in the model.

    Notes
    -----

    Evaluating a large amount of these process models is costly.
    Limiting the allowed activities in the Local Process Models leads to a smaller search space and
    can lead to better performance.
    Additionally, the search space can be pruned based on support and determinism.
    Increasing the thresholds for these values can speed up the algorithm.
    Moreover, the maximum number of Local Process Models to be returned can be
    specified, providing a cut-off for the algorithm.

    The unpruned search space 's' in iteration 'i' grows polynomially in the number of selected activities 'a'
    (to the power of i) and exponentially in the iteration 'i': :math:`s = a^i 6^{i-1} (i-1)!`



    Parameters
    ----------
    log: :class:`pm4py.log.log.EventLog`
        Event log to use
    selected_activities: list
        Activities to consider when building Local Process Models, default is None, in which case all activities are used.
    parameters:
        Parameters of the algorithm, including:

        - CASE_ID_KEY : str, optional
            Key used to correlate events into cases.
            By default, the value 'case:concept:name' is used.
        - ACTIVITY_KEY : str, optional
            Key to use within events to identify the underlying activity.
            By default, the value 'concept:name' is used.
        - FREQUENCY_THRESHOLD : int, optional
            Positive integer frequency threshold, default is 20.
        - CONFIDENCE_THRESHOLD : float, optional
            Confidence threshold between 0 and 1, default is 0.7.
        - DETERMINISM_THRESHOLD : float, optional
            Determinism threshold between 0 and 1, default is 0.5.
        - LANGUAGE_FIT_THRESHOLD : float, optional
            Language fit threshold between 0 and 1, default is 0.3.
        - COVERAGE_THRESHOLD : float, optional
            Coverage threshold between 0 and 1, default is 0.
        - MAX_ITERATIONS : int, optional
            Maximum number of iterations of the search algorithm. In each iteration 'i' Process Trees with exactly 'i' activities are considered, default is 3
        - MAX_NUMBER_OF_MODELS : int, optional
            The maximum number of models to be returned. Can be used to restrict the solve time. Default is None.
        - MULTI_PROCESSING : boolean, optional
            Whether to use multiprocessing, default is False.
        - TIME_LIMIT : float, optional
            Time limit for the computation, default is None. This is not a hard limit. The evaluation of the current model is finished or if multiprocessing
            is enabled the evaluation of the current batch is finished before the time limit stops the process.
        - PROGRESS_BAR_TYPE : string, optional
            Default value `explored_lpms` shows the number of explored LPMs in each iteration.
            Use `found_lpms` to show a progress bar for the number of LPMs found so far in relation to MAX_NUMBER_OF_MODELS.
            Otherwise, use None to hide the progress bar.

    Returns
    -------
    lpms : list of tuple
        A list of tuples, where each tuple contains a
        ``pm4py.objects.process_tree.obj.ProcessTree`` and its corresponding
        ``pm4py.algo.discovery.local_process_models.metrics.quality_metrics.LocalProcessModelStats``.

    References
    ----------
    .. [1] Tax, N., Sidorova, N., Haakma, R., & van der Aalst, W. M. (2016).
       Mining local process models. Journal of Innovation in Digital Ecosystems, 3(2), 183-196.

    .. [2] Leemans, M., & van der Aalst, W. M. (2014, November). Discovery of frequent episodes in event logs.
       In International symposium on data-driven process discovery and analysis (pp. 1-31). Cham: Springer International Publishing.

    """

    if parameters is None:
        parameters = {}
    case_id_glue = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, pmutil.constants.CASE_CONCEPT_NAME
    )
    activity_key = exec_utils.get_param_value(
        Parameters.ACTIVITY_KEY, parameters, xes_util.DEFAULT_NAME_KEY
    )
    timestamp_key = exec_utils.get_param_value(
        Parameters.TIMESTAMP_KEY, parameters, xes_util.DEFAULT_TIMESTAMP_KEY
    )

    activity_counts = get_event_attribute_values(log, activity_key)
    log_activities = list(activity_counts.keys())
    if selected_activities is None:
        selected_activities = log_activities
    elif not set(selected_activities).issubset(set(log_activities)):
        raise ValueError(f"Not all selected activities are present in the log.\n"
                        f"Activities in log: {log_activities}.\n"
                        f"Selected activities: {selected_activities}")

    frequency_threshold = exec_utils.get_param_value(
        Parameters.FREQUENCY_THRESHOLD, parameters, 20
    )

    determinism_threshold = exec_utils.get_param_value(
        Parameters.DETERMINISM_THRESHOLD, parameters, 0.5
    )

    confidence_threshold = exec_utils.get_param_value(
        Parameters.CONFIDENCE_THRESHOLD, parameters, 0.7
    )

    language_fit_threshold = exec_utils.get_param_value(
        Parameters.LANGUAGE_FIT_THRESHOLD, parameters, 0.3
    )

    coverage_threshold = exec_utils.get_param_value(
        Parameters.COVERAGE_THRESHOLD, parameters, 0
    )

    max_iterations = exec_utils.get_param_value(
        Parameters.MAX_ITERATIONS, parameters, 3
    )

    max_number_of_models = exec_utils.get_param_value(
        Parameters.MAX_NUMBER_OF_MODELS, parameters, None
    )

    multi_processing = exec_utils.get_param_value(
        Parameters.MULTI_PROCESSING, parameters, False
    )

    time_limit = exec_utils.get_param_value(
        Parameters.TIME_LIMIT, parameters, None
    )

    progress_bar_type = exec_utils.get_param_value(
        Parameters.PROGRESS_BAR_TYPE, parameters, "explored_lpms"
    )

    start_time = time.time()
    return_lpms = []
    trees_to_expand = []
    projected_log_cache = dict()
    i = 1
    while i <= max_iterations:
        if i == 1:
            candidates = __generate_initial_trees(selected_activities)
        else:
            candidates = __expand_trees(trees_to_expand, selected_activities, i == 2)

        trees_to_expand = __evaluate_trees(log,
                                           candidates,
                                           activity_key,
                                           timestamp_key,
                                           case_id_glue,
                                           i,
                                           frequency_threshold,
                                           confidence_threshold,
                                           determinism_threshold,
                                           language_fit_threshold,
                                           coverage_threshold,
                                           progress_bar_type,
                                           multi_processing,
                                           max_number_of_models,
                                           projected_log_cache,
                                           start_time,
                                           time_limit,
                                           return_lpms)

        if not len(trees_to_expand):
            return return_lpms

        i += 1

    return return_lpms


def __generate_initial_trees(selected_activities):
    return [(ProcessTree(operator=None, parent=None, label=activity), {activity}) for activity in selected_activities]


def __expand_trees(base_trees, selected_activities, is_first_expansion):
    expanded_trees = []
    for tree, used_activities in base_trees:
        current = [(0, tree)]
        while len(current) > 0:
            idx, node = current.pop()
            if len(node.children) == 0:
                for activity in selected_activities: # paper suggests that we iterate over all activities, including ones already used in the pattern
                    parent_operator = node.parent.operator if node.parent else None
                    __add_expanded_tree_variants(expanded_trees, tree, used_activities, node.label, activity, parent_operator, idx, is_first_expansion)
            else:
                current.extend(enumerate(node.children))

    return expanded_trees


def __add_expanded_tree_variants(expanded_trees, tree, used_activities, existing_activity, new_activity, parent_operator, child_index, is_first_expansion):
    new_used_activities = used_activities.union({new_activity})
    if parent_operator is not Operator.SEQUENCE or child_index == 0: # symmetry pruning not mentioned in paper
        seq1 = _get_expanded_tree_variant(tree, existing_activity,
                                          Operator.SEQUENCE, existing_activity, new_activity)
        expanded_trees.append((seq1, new_used_activities))

    if existing_activity != new_activity and not is_first_expansion:
        seq2 = _get_expanded_tree_variant(tree, existing_activity,
                                          Operator.SEQUENCE, new_activity, existing_activity)
        expanded_trees.append((seq2, new_used_activities))

    if existing_activity != new_activity and (not is_first_expansion and hash(existing_activity) < hash(new_activity)):

        # symmetry pruning: if parent operator is equal to this operator only extend first child
        if parent_operator is not Operator.XOR or child_index == 0:
            xor = _get_expanded_tree_variant(tree, existing_activity,
                                             Operator.XOR, existing_activity, new_activity)
            expanded_trees.append((xor, new_used_activities))

        # symmetry pruning: if parent operator is equal to this operator only extend first child
        if parent_operator is not Operator.PARALLEL or child_index == 0:
            parallel = _get_expanded_tree_variant(tree, existing_activity,
                                                  Operator.PARALLEL, existing_activity, new_activity)
            expanded_trees.append((parallel, new_used_activities))

    loop1 = _get_expanded_tree_variant(tree, existing_activity,
                                       Operator.LOOP, existing_activity, new_activity)
    expanded_trees.append((loop1, new_used_activities))

    if existing_activity != new_activity and not is_first_expansion:
        loop2 = _get_expanded_tree_variant(tree, existing_activity,
                                           Operator.LOOP, new_activity, existing_activity)
        expanded_trees.append((loop2, new_used_activities))


def _get_expanded_tree_variant(original_tree, leaf_activity_name, operator, activity1, activity2):
    copied_tree, leaf_node = __deep_copy_and_get_leaf_ref_by_activity(original_tree, leaf_activity_name)
    parent = leaf_node.parent
    new_operator_node = ProcessTree(operator=operator, parent=parent)
    new_leaves = [ProcessTree(operator=None, parent=new_operator_node, label=activity1),
                  ProcessTree(operator=None, parent=new_operator_node, label=activity2)]
    new_operator_node.children = new_leaves

    if parent is not None:
        parent.children.remove(leaf_node)
        parent.children.append(new_operator_node)
    else:
        copied_tree = new_operator_node

    del leaf_node
    return copied_tree


def __deep_copy_and_get_leaf_ref_by_activity(tree_node, activity):
    cloned_node = ProcessTree(
        operator=tree_node.operator,
        label=tree_node.label
    )

    cloned_node._properties = copy.deepcopy(tree_node._properties)

    activity_leaf_node = None
    if not tree_node.children:
        if tree_node.label == activity:
            activity_leaf_node = cloned_node
    else:
        cloned_children = []
        for child in tree_node.children:
            cloned_child, maybe_leaf_node = __deep_copy_and_get_leaf_ref_by_activity(child, activity)

            cloned_child.parent = cloned_node
            cloned_children.append(cloned_child)

            if maybe_leaf_node is not None:
                activity_leaf_node = maybe_leaf_node

        cloned_node.children = cloned_children

    return cloned_node, activity_leaf_node


_lpm_worker_state = {}
def __init_worker(log, projected_log_cache, activity_key, timestamp_key, case_id_key, iteration,
                  frequency_threshold, confidence_threshold, determinism_threshold,
                  language_fit_threshold, coverage_threshold):
    global _lpm_worker_state
    _lpm_worker_state['log'] = log
    _lpm_worker_state['projected_log_cache'] = projected_log_cache
    _lpm_worker_state['activity_key'] = activity_key
    _lpm_worker_state['timestamp_key'] = timestamp_key
    _lpm_worker_state['case_id_key'] = case_id_key
    _lpm_worker_state['iteration'] = iteration
    _lpm_worker_state['frequency_threshold'] = frequency_threshold
    _lpm_worker_state['confidence_threshold'] = confidence_threshold
    _lpm_worker_state['determinism_threshold'] = determinism_threshold
    _lpm_worker_state['language_fit_threshold'] = language_fit_threshold
    _lpm_worker_state['coverage_threshold'] = coverage_threshold


def __mp_evaluate_tree_worker(candidate):
    tree, used_activities = candidate
    args = _lpm_worker_state
    local_return_lpms = []

    expand_tree = evaluate_tree(
        args['log'], tree, used_activities, args['projected_log_cache'],
        args['activity_key'], args['timestamp_key'], args['case_id_key'],
        args['iteration'], args['frequency_threshold'], args['confidence_threshold'],
        args['determinism_threshold'], args['language_fit_threshold'],
        args['coverage_threshold'], local_return_lpms
    )

    return tree, used_activities, expand_tree, local_return_lpms


def __evaluate_trees(log, candidates, activity_key, timestamp_key, case_id_key, iteration,
                     frequency_threshold, confidence_threshold, determinism_threshold,
                     language_fit_threshold, coverage_threshold, progress_bar_type, multi_processing,
                     max_number_of_models, projected_log_cache, start_time, time_limit, return_lpms):
    trees_to_expand = []
    progress = __get_progress_bar(len(candidates), max_number_of_models, iteration, progress_bar_type)
    __update_progress(progress, progress_bar_type, return_lpms) # makes sure the bar starts at the correct value when process bar type is "found_lpms"

    if multi_processing and len(candidates) > 200:
        init_args = (
            log, projected_log_cache, activity_key, timestamp_key, case_id_key, iteration,
            frequency_threshold, confidence_threshold, determinism_threshold,
            language_fit_threshold, coverage_threshold
        )

        chunk_size = 50
        num_cores = mp.cpu_count()
        with mp.Pool(processes=num_cores, initializer=__init_worker, initargs=init_args) as pool: # 69

            candidate_iterator = iter(candidates)
            for tree, used_activities, expand_tree, local_lpms in pool.imap_unordered(
                    __mp_evaluate_tree_worker,
                    candidate_iterator,
                    chunksize=chunk_size
            ):

                return_lpms.extend(local_lpms)

                if expand_tree:
                    trees_to_expand.append((tree, used_activities))

                __update_progress(progress, progress_bar_type, return_lpms)

                if max_number_of_models and len(return_lpms) >= max_number_of_models:
                    del return_lpms[max_number_of_models:] # due to multiprocessing we might have found too many lmps
                    pool.terminate()
                    __close_progress_bar(progress)
                    return []

                elapsed_time = time.time() - start_time
                if time_limit is not None and elapsed_time > time_limit:
                    if max_number_of_models and len(return_lpms) > max_number_of_models:
                        del return_lpms[max_number_of_models:]
                    pool.terminate()
                    __close_progress_bar(progress)
                    return []
    else:
        for tree, used_activities in candidates:
            expand_tree = evaluate_tree(log,
                                        tree,
                                        used_activities,
                                        projected_log_cache,
                                        activity_key,
                                        timestamp_key,
                                        case_id_key,
                                        iteration,
                                        frequency_threshold,
                                        confidence_threshold,
                                        determinism_threshold,
                                        language_fit_threshold,
                                        coverage_threshold,
                                        return_lpms)

            if expand_tree:
                trees_to_expand.append((tree, used_activities))

            __update_progress(progress, progress_bar_type, return_lpms)

            if max_number_of_models and len(return_lpms) >= max_number_of_models:
                __close_progress_bar(progress)
                return []

            elapsed_time = time.time() - start_time
            if time_limit is not None and elapsed_time > time_limit:
                __close_progress_bar(progress)
                return []

    __close_progress_bar(progress)

    return trees_to_expand


def __get_progress_bar(num_candidates, max_num_lpms, iteration, progress_bar_type):
    progress = None

    if (
        importlib.util.find_spec("tqdm")
    ):
        if progress_bar_type == "found_lpms" and max_num_lpms is not None and max_num_lpms > 0:
            from tqdm.auto import tqdm
            progress = tqdm(
                total=max_num_lpms, desc=f"Iteration {iteration} Total Discovered LPMs :: "
            )
        elif progress_bar_type == "explored_lpms" and num_candidates > 0:
            from tqdm.auto import tqdm
            progress = tqdm(
                total=num_candidates, desc=f"Iteration {iteration} Checking LPM Candidates :: "
            )

    return progress


def __update_progress(progress, progress_bar_type, return_lpms):
    if progress is not None:
        if progress_bar_type == "found_lpms":
            progress.n = len(return_lpms)
            progress.refresh()
        elif progress_bar_type == "explored_lpms":
            progress.update()

def __close_progress_bar(progress):
    if progress is not None:
        progress.close()
    del progress

