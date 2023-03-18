'''
    This file is part of PM4Py (More Info: https://pm4py.fit.fraunhofer.de).

    PM4Py is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    PM4Py is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with PM4Py.  If not, see <https://www.gnu.org/licenses/>.
'''
__doc__ = """
The ``pm4py.discovery`` module contains the process discovery algorithms implemented in ``pm4py``
"""

import warnings
from typing import Tuple, Union, List, Dict, Any, Optional

import pandas as pd
from pandas import DataFrame

from pm4py.objects.bpmn.obj import BPMN
from pm4py.objects.dfg.obj import DFG
from pm4py.objects.heuristics_net.obj import HeuristicsNet
from pm4py.objects.transition_system.obj import TransitionSystem
from pm4py.objects.trie.obj import Trie
from pm4py.objects.log.obj import EventLog
from pm4py.objects.log.obj import EventStream
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.process_tree.obj import ProcessTree
from pm4py.util.pandas_utils import check_is_pandas_dataframe, check_pandas_dataframe_columns
from pm4py.utils import get_properties, xes_constants, __event_log_deprecation_warning
from pm4py.util import constants
import deprecation
import pkgutil


def discover_dfg(log: Union[EventLog, pd.DataFrame], activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> Tuple[dict, dict, dict]:
    """
    Discovers a Directly-Follows Graph (DFG) from a log.

    This method returns a dictionary with the couples of directly-following activities (in the log)
    as keys and the frequency of relation as value.

    :param log: event log / Pandas dataframe
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :rtype: ``Tuple[dict, dict, dict]``

    .. code-block:: python3

        import pm4py

        dfg, start_activities, end_activities = pm4py.discover_dfg(dataframe, case_id_key='case:concept:name', activity_key='concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    properties = get_properties(
        log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)
    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)
        from pm4py.util import constants

        from pm4py.algo.discovery.dfg.adapters.pandas.df_statistics import get_dfg_graph
        dfg = get_dfg_graph(log, activity_key=activity_key,
                            timestamp_key=timestamp_key,
                            case_id_glue=case_id_key)
        from pm4py.statistics.start_activities.pandas import get as start_activities_module
        from pm4py.statistics.end_activities.pandas import get as end_activities_module
        start_activities = start_activities_module.get_start_activities(
            log, parameters=properties)
        end_activities = end_activities_module.get_end_activities(
            log, parameters=properties)
    else:
        from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
        dfg = dfg_discovery.apply(log, parameters=properties)
        from pm4py.statistics.start_activities.log import get as start_activities_module
        from pm4py.statistics.end_activities.log import get as end_activities_module
        start_activities = start_activities_module.get_start_activities(
            log, parameters=properties)
        end_activities = end_activities_module.get_end_activities(
            log, parameters=properties)
    return dfg, start_activities, end_activities


def discover_directly_follows_graph(log: Union[EventLog, pd.DataFrame], activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> Tuple[dict, dict, dict]:
    if type(log) not in [pd.DataFrame, EventLog, EventStream]:
        raise Exception(
            "the method can be applied only to a traditional event log!")

    return discover_dfg(log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)


def discover_dfg_typed(log: pd.DataFrame, case_id_key: str = "case:concept:name", activity_key: str = "concept:name", timestamp_key: str = "time:timestamp") -> DFG:
    """
    Discovers a Directly-Follows Graph (DFG) from a log.

    This method returns a typed DFG object, i.e., as specified in ``pm4py.objects.dfg.obj.py`` (``DirectlyFollowsGraph`` Class)
    The DFG object describes a graph, start activities and end activities.
    The graph is a collection of triples of the form (a,b,f) representing an arc a->b with frequency f.
    The start activities are a collection of tuples of the form (a,f) representing that activity a starts f cases.
    The end activities are a collection of tuples of the form (a,f) representing that ativity a ends f cases.
    
    This method replaces ``pm4py.discover_dfg`` and ``pm4py.discover_directly_follows_graph``. In a future release, these functions will adopt the same behavior as this function.

    :param log: ``pandas.DataFrame``
    :param case_id_key: attribute to be used as case identifier
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    
    :rtype: ``DFG``

    .. code-block:: python3

        import pm4py

        dfg = pm4py.discover_dfg_typed(log, case_id_key='case:concept:name', activity_key='concept:name', timestamp_key='time:timestamp')
    """
    from pm4py.algo.discovery.dfg.variants import clean
    parameters = get_properties(
        log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)
    if type(log) is pd.DataFrame:
        return clean.apply(log, parameters)
    elif pkgutil.find_loader("polars"):
        import polars as pl
        if type(log) is pl.DataFrame:
            from pm4py.algo.discovery.dfg.variants import clean_polars
            return clean_polars.apply(log, parameters)
        else:
            raise TypeError('pm4py.discover_dfg_typed is only defined for pandas/polars DataFrames')
    else:
        raise TypeError('pm4py.discover_dfg_typed is only defined for pandas/polars DataFrames')
        

def discover_performance_dfg(log: Union[EventLog, pd.DataFrame], business_hours: bool = False, business_hour_slots=constants.DEFAULT_BUSINESS_HOUR_SLOTS, workcalendar=constants.DEFAULT_BUSINESS_HOURS_WORKCALENDAR, activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> Tuple[dict, dict, dict]:
    """
    Discovers a performance directly-follows graph from an event log.

    This method returns a dictionary with the couples of directly-following activities (in the log)
    as keys and the performance of relation as value.

    :param log: event log / Pandas dataframe
    :param business_hours: enables/disables the computation based on the business hours (default: False)
    :param business_hour_slots: work schedule of the company, provided as a list of tuples where each tuple represents one time slot of business hours. One slot i.e. one tuple consists of one start and one end time given in seconds since week start, e.g. [(7 * 60 * 60, 17 * 60 * 60), ((24 + 7) * 60 * 60, (24 + 12) * 60 * 60), ((24 + 13) * 60 * 60, (24 + 17) * 60 * 60),] meaning that business hours are Mondays 07:00 - 17:00 and Tuesdays 07:00 - 12:00 and 13:00 - 17:00
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :rtype: ``Tuple[dict, dict, dict]``

    .. code-block:: python3

        import pm4py

        performance_dfg, start_activities, end_activities = pm4py.discover_performance_dfg(dataframe, case_id_key='case:concept:name', activity_key='concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    properties = get_properties(
        log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)
        from pm4py.util import constants

        from pm4py.algo.discovery.dfg.adapters.pandas.df_statistics import get_dfg_graph
        dfg = get_dfg_graph(log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_glue=case_id_key, measure="performance", perf_aggregation_key="all",
                            business_hours=business_hours, business_hours_slot=business_hour_slots, workcalendar=workcalendar)
        from pm4py.statistics.start_activities.pandas import get as start_activities_module
        from pm4py.statistics.end_activities.pandas import get as end_activities_module
        start_activities = start_activities_module.get_start_activities(
            log, parameters=properties)
        end_activities = end_activities_module.get_end_activities(
            log, parameters=properties)
    else:
        from pm4py.algo.discovery.dfg.variants import performance as dfg_discovery
        properties[dfg_discovery.Parameters.AGGREGATION_MEASURE] = "all"
        properties[dfg_discovery.Parameters.BUSINESS_HOURS] = business_hours
        properties[dfg_discovery.Parameters.BUSINESS_HOUR_SLOTS] = business_hour_slots
        dfg = dfg_discovery.apply(log, parameters=properties)
        from pm4py.statistics.start_activities.log import get as start_activities_module
        from pm4py.statistics.end_activities.log import get as end_activities_module
        start_activities = start_activities_module.get_start_activities(
            log, parameters=properties)
        end_activities = end_activities_module.get_end_activities(
            log, parameters=properties)
    return dfg, start_activities, end_activities


def discover_petri_net_alpha(log: Union[EventLog, pd.DataFrame], activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> Tuple[PetriNet, Marking, Marking]:
    """
    Discovers a Petri net using the Alpha Miner.

    :param log: event log / Pandas dataframe
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :rtype: ``Tuple[PetriNet, Marking, Marking]``

    .. code-block:: python3

        import pm4py

        net, im, fm = pm4py.discover_petri_net_alpha(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    from pm4py.algo.discovery.alpha import algorithm as alpha_miner
    return alpha_miner.apply(log, variant=alpha_miner.Variants.ALPHA_VERSION_CLASSIC, parameters=get_properties(log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key))


def discover_petri_net_ilp(log: Union[EventLog, pd.DataFrame], alpha: float = 1.0, activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> Tuple[PetriNet, Marking, Marking]:
    """
    Discovers a Petri net using the ILP Miner.

    :param log: event log / Pandas dataframe
    :param alpha: noise threshold for the sequence encoding graph (1.0=no filtering, 0.0=greatest filtering)
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :rtype: ``Tuple[PetriNet, Marking, Marking]``

    .. code-block:: python3

        import pm4py

        net, im, fm = pm4py.discover_petri_net_ilp(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    parameters = get_properties(log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)
    parameters["alpha"] = alpha

    from pm4py.algo.discovery.ilp import algorithm as ilp_miner
    return ilp_miner.apply(log, variant=ilp_miner.Variants.CLASSIC, parameters=parameters)


@deprecation.deprecated(deprecated_in="2.3.0", removed_in="3.0.0", details="this method will be removed in a future release.")
def discover_petri_net_alpha_plus(log: Union[EventLog, pd.DataFrame], activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> Tuple[PetriNet, Marking, Marking]:
    """
    Discovers a Petri net using the Alpha+ algorithm

    :param log: event log / Pandas dataframe
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :rtype: ``Tuple[PetriNet, Marking, Marking]``

    .. code-block:: python3

        import pm4py

        net, im, fm = pm4py.discover_petri_net_alpha_plus(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    from pm4py.algo.discovery.alpha import algorithm as alpha_miner
    return alpha_miner.apply(log, variant=alpha_miner.Variants.ALPHA_VERSION_PLUS, parameters=get_properties(log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key))


def discover_petri_net_inductive(log: Union[EventLog, pd.DataFrame, DFG], multi_processing: bool = False, noise_threshold: float = 0.0, activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> Tuple[
        PetriNet, Marking, Marking]:
    """
    Discovers a Petri net using the inductive miner algorithm.

    The basic idea of Inductive Miner is about detecting a 'cut' in the log (e.g. sequential cut, parallel cut, concurrent cut and loop cut) and then recur on sublogs, which were found applying the cut, until a base case is found. The Directly-Follows variant avoids the recursion on the sublogs but uses the Directly Follows graph.

    Inductive miner models usually make extensive use of hidden transitions, especially for skipping/looping on a portion on the model. Furthermore, each visible transition has a unique label (there are no transitions in the model that share the same label).

    :param log: event log / Pandas dataframe / typed DFG
    :param noise_threshold: noise threshold (default: 0.0)
    :param multi_processing: boolean that enables/disables multiprocessing in inductive miner
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :rtype: ``Tuple[PetriNet, Marking, Marking]``

    .. code-block:: python3

        import pm4py

        net, im, fm = pm4py.discover_petri_net_inductive(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream, DFG]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    pt = discover_process_tree_inductive(
        log, noise_threshold, multi_processing=multi_processing, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)
    from pm4py.convert import convert_to_petri_net
    return convert_to_petri_net(pt)


def discover_petri_net_heuristics(log: Union[EventLog, pd.DataFrame], dependency_threshold: float = 0.5,
                                  and_threshold: float = 0.65,
                                  loop_two_threshold: float = 0.5, activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> Tuple[PetriNet, Marking, Marking]:
    """
    Discover a Petri net using the Heuristics Miner

    Heuristics Miner is an algorithm that acts on the Directly-Follows Graph, providing way to handle with noise and to find common constructs (dependency between two activities, AND). The output of the Heuristics Miner is an Heuristics Net, so an object that contains the activities and the relationships between them. The Heuristics Net can be then converted into a Petri net. The paper can be visited by clicking on the upcoming link: this link).

    :param log: event log / Pandas dataframe
    :param dependency_threshold: dependency threshold (default: 0.5)
    :param and_threshold: AND threshold (default: 0.65)
    :param loop_two_threshold: loop two threshold (default: 0.5)
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :rtype: ``Tuple[PetriNet, Marking, Marking]``

    .. code-block:: python3

        import pm4py

        net, im, fm = pm4py.discover_petri_net_heuristics(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    from pm4py.algo.discovery.heuristics.variants import classic as heuristics_miner
    heu_parameters = heuristics_miner.Parameters
    parameters = get_properties(
        log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)
    parameters[heu_parameters.DEPENDENCY_THRESH] = dependency_threshold
    parameters[heu_parameters.AND_MEASURE_THRESH] = and_threshold
    parameters[heu_parameters.LOOP_LENGTH_TWO_THRESH] = loop_two_threshold

    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)
        return heuristics_miner.apply_pandas(log, parameters=parameters)
    else:
        return heuristics_miner.apply(log, parameters=parameters)


def discover_process_tree_inductive(log: Union[EventLog, pd.DataFrame, DFG], noise_threshold: float = 0.0, multi_processing: bool = constants.ENABLE_MULTIPROCESSING_DEFAULT, activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> ProcessTree:
    """
    Discovers a process tree using the inductive miner algorithm

    The basic idea of Inductive Miner is about detecting a 'cut' in the log (e.g. sequential cut, parallel cut, concurrent cut and loop cut) and then recur on sublogs, which were found applying the cut, until a base case is found. The Directly-Follows variant avoids the recursion on the sublogs but uses the Directly Follows graph.

    Inductive miner models usually make extensive use of hidden transitions, especially for skipping/looping on a portion on the model. Furthermore, each visible transition has a unique label (there are no transitions in the model that share the same label).

    :param log: event log / Pandas dataframe / typed DFG
    :param noise_threshold: noise threshold (default: 0.0)
    :param activity_key: attribute to be used for the activity
    :param multi_processing: boolean that enables/disables multiprocessing in inductive miner
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :rtype: ``ProcessTree``

    .. code-block:: python3

        import pm4py

        process_tree = pm4py.discover_process_tree_inductive(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream, DFG]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    from pm4py.algo.discovery.inductive import algorithm as inductive_miner
    parameters = get_properties(
        log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)
    parameters["noise_threshold"] = noise_threshold
    parameters["multiprocessing"] = multi_processing

    variant = inductive_miner.Variants.IMf if noise_threshold > 0 else inductive_miner.Variants.IM

    if isinstance(log, DFG):
        variant = inductive_miner.Variants.IMd

    return inductive_miner.apply(log, variant=variant, parameters=parameters)


def discover_heuristics_net(log: Union[EventLog, pd.DataFrame], dependency_threshold: float = 0.5,
                            and_threshold: float = 0.65,
                            loop_two_threshold: float = 0.5, min_act_count: int = 1, min_dfg_occurrences: int = 1, activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name", decoration: str = "frequency") -> HeuristicsNet:
    """
    Discovers an heuristics net

    Heuristics Miner is an algorithm that acts on the Directly-Follows Graph, providing way to handle with noise and to find common constructs (dependency between two activities, AND). The output of the Heuristics Miner is an Heuristics Net, so an object that contains the activities and the relationships between them. The Heuristics Net can be then converted into a Petri net. The paper can be visited by clicking on the upcoming link: this link).

    :param log: event log / Pandas dataframe
    :param dependency_threshold: dependency threshold (default: 0.5)
    :param and_threshold: AND threshold (default: 0.65)
    :param loop_two_threshold: loop two threshold (default: 0.5)
    :param min_act_count: minimum number of occurrences per activity in order to be included in the discovery
    :param min_dfg_occurrences: minimum number of occurrences per arc in the DFG in order to be included in the discovery
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :param decoration: the decoration that should be used (frequency, performance)
    :rtype: ``HeuristicsNet``

    .. code-block:: python3

        import pm4py

        heu_net = pm4py.discover_heuristics_net(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    from pm4py.algo.discovery.heuristics.variants import classic as heuristics_miner
    heu_parameters = heuristics_miner.Parameters
    parameters = get_properties(
        log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)
    parameters[heu_parameters.DEPENDENCY_THRESH] = dependency_threshold
    parameters[heu_parameters.AND_MEASURE_THRESH] = and_threshold
    parameters[heu_parameters.LOOP_LENGTH_TWO_THRESH] = loop_two_threshold
    parameters[heu_parameters.MIN_ACT_COUNT] = min_act_count
    parameters[heu_parameters.MIN_DFG_OCCURRENCES] = min_dfg_occurrences
    parameters[heu_parameters.HEU_NET_DECORATION] = decoration
    
    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)
        return heuristics_miner.apply_heu_pandas(log, parameters=parameters)
    else:
        return heuristics_miner.apply_heu(log, parameters=parameters)


def derive_minimum_self_distance(log: Union[DataFrame, EventLog, EventStream], activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> Dict[str, int]:
    """
    This algorithm computes the minimum self-distance for each activity observed in an event log.
    The self distance of a in <a> is infinity, of a in <a,a> is 0, in <a,b,a> is 1, etc.
    The activity key 'concept:name' is used.

    :param log: event log / Pandas dataframe
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :rtype: ``Dict[str, int]``

    .. code-block:: python3

        import pm4py

        msd = pm4py.derive_minimum_self_distance(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    from pm4py.algo.discovery.minimum_self_distance import algorithm as msd
    return msd.apply(log, parameters=get_properties(log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key))


def discover_footprints(*args: Union[EventLog, Tuple[PetriNet, Marking, Marking], ProcessTree]) -> Union[
        List[Dict[str, Any]], Dict[str, Any]]:
    """
    Discovers the footprints out of the provided event log / process model

    :param args: event log / process model
    :rtype: ``Union[List[Dict[str, Any]], Dict[str, Any]]``

    .. code-block:: python3

        import pm4py

        footprints = pm4py.discover_footprints(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
    """
    from pm4py.algo.discovery.footprints import algorithm as fp_discovery
    return fp_discovery.apply(*args)


def discover_eventually_follows_graph(log: Union[EventLog, pd.DataFrame], activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> Dict[Tuple[str, str], int]:
    """
    Gets the eventually follows graph from a log object.

    The eventually follows graph is a dictionary associating to every
    couple of activities which are eventually following each other the
    number of occurrences of this relation.

    :param log: event log / Pandas dataframe
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :rtype: ``Dict[Tuple[str, str], int]``

    .. code-block:: python3

        import pm4py

        efg = pm4py.discover_eventually_follows_graph(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    properties = get_properties(
        log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)
        from pm4py.statistics.eventually_follows.pandas import get
        return get.apply(log, parameters=properties)
    else:
        from pm4py.statistics.eventually_follows.log import get
        return get.apply(log, parameters=properties)


def discover_bpmn_inductive(log: Union[EventLog, pd.DataFrame, DFG], noise_threshold: float = 0.0, multi_processing: bool = constants.ENABLE_MULTIPROCESSING_DEFAULT, activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> BPMN:
    """
    Discovers a BPMN using the Inductive Miner algorithm

    The basic idea of Inductive Miner is about detecting a 'cut' in the log (e.g. sequential cut, parallel cut, concurrent cut and loop cut) and then recur on sublogs, which were found applying the cut, until a base case is found. The Directly-Follows variant avoids the recursion on the sublogs but uses the Directly Follows graph.

    Inductive miner models usually make extensive use of hidden transitions, especially for skipping/looping on a portion on the model. Furthermore, each visible transition has a unique label (there are no transitions in the model that share the same label).

    :param log: event log / Pandas dataframe / typed DFG
    :param noise_threshold: noise threshold (default: 0.0)
    :param multi_processing: boolean that enables/disables multiprocessing in inductive miner
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :rtype: ``BPMN``

    .. code-block:: python3

        import pm4py

        bpmn_graph = pm4py.discover_bpmn_inductive(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream, DFG]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    pt = discover_process_tree_inductive(
        log, noise_threshold, multi_processing=multi_processing, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)
    from pm4py.convert import convert_to_bpmn
    return convert_to_bpmn(pt)


def discover_transition_system(log: Union[EventLog, pd.DataFrame], direction: str = "forward", window: int = 2, view: str = "sequence", activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> TransitionSystem:
    """
    Discovers a transition system as described in the process mining book
    "Process Mining: Data Science in Action"

    :param log: event log / Pandas dataframe
    :param direction: direction in which the transition system is built (forward, backward)
    :param window: window (2, 3, ...)
    :param view: view to use in the construction of the states (sequence, set, multiset)
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :rtype: ``TransitionSystem``

    .. code-block:: python3

        import pm4py

        transition_system = pm4py.discover_transition_system(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    properties = get_properties(
        log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)
    properties["direction"] = direction
    properties["window"] = window
    properties["view"] = view

    from pm4py.algo.discovery.transition_system import algorithm as ts_discovery
    return ts_discovery.apply(log, parameters=properties)


def discover_prefix_tree(log: Union[EventLog, pd.DataFrame], activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> Trie:
    """
    Discovers a prefix tree from the provided log object.

    :param log: event log / Pandas dataframe
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :rtype: ``Trie``

    .. code-block:: python3

        import pm4py

        prefix_tree = pm4py.discover_prefix_tree(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    properties = get_properties(
        log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    from pm4py.algo.transformation.log_to_trie import algorithm as trie_discovery
    return trie_discovery.apply(log, parameters=properties)


def discover_temporal_profile(log: Union[EventLog, pd.DataFrame], activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> Dict[Tuple[str, str], Tuple[float, float]]:
    """
    Discovers a temporal profile from a log object.

    Implements the approach described in:
    Stertz, Florian, Jürgen Mangler, and Stefanie Rinderle-Ma. "Temporal Conformance Checking at Runtime based on Time-infused Process Models." arXiv preprint arXiv:2008.07262 (2020).

    The output is a dictionary containing, for every couple of activities eventually following in at least a case of the log,
    the average and the standard deviation of the difference of the timestamps.

    E.g. if the log has two cases:

    A (timestamp: 1980-01)   B (timestamp: 1980-03)    C (timestamp: 1980-06)
    A (timestamp: 1990-01)   B (timestamp: 1990-02)    D (timestamp: 1990-03)

    The returned dictionary will contain:
    {('A', 'B'): (1.5 months, 0.5 months), ('A', 'C'): (5 months, 0), ('A', 'D'): (2 months, 0)}

    :param log: event log / Pandas dataframe
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :rtype: ``Dict[Tuple[str, str], Tuple[float, float]]``

    .. code-block:: python3

        import pm4py

        temporal_profile = pm4py.discover_temporal_profile(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    properties = get_properties(
        log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    from pm4py.algo.discovery.temporal_profile import algorithm as temporal_profile_discovery
    return temporal_profile_discovery.apply(log, parameters=properties)


def discover_log_skeleton(log: Union[EventLog, pd.DataFrame], noise_threshold: float = 0.0, activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name") -> Dict[str, Any]:
    """
    Discovers a log skeleton from an event log.

    A log skeleton is a declarative model which consists of six different constraints:
    - "directly_follows": specifies for some activities some strict bounds on the activities directly-following. For example,
                        'A should be directly followed by B' and 'B should be directly followed by C'.
    - "always_before": specifies that some activities may be executed only if some other activities are executed somewhen before
                        in the history of the case.
                        For example, 'C should always be preceded by A'
    - "always_after": specifies that some activities should always trigger the execution of some other activities
                        in the future history of the case.
                        For example, 'A should always be followed by C'
    - "equivalence": specifies that a given couple of activities should happen with the same number of occurrences inside
                        a case.
                        For example, 'B and C should always happen the same number of times'.
    - "never_together": specifies that a given couple of activities should never happen together in the history of the case.
                        For example, 'there should be no case containing both C and D'.
    - "activ_occurrences": specifies the allowed number of occurrences per activity:
                        E.g. A is allowed to be executed 1 or 2 times, B is allowed to be executed 1 or 2 or 3 or 4 times.

    Reference paper:
    Verbeek, H. M. W., and R. Medeiros de Carvalho. "Log skeletons: A classification approach to process discovery." arXiv preprint arXiv:1806.08247 (2018).

    :param log: event log / Pandas dataframe
    :param noise_threshold: noise threshold, acting as described in the paper.
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :rtype: ``Dict[str, Any]``

    .. code-block:: python3

        import pm4py

        log_skeleton = pm4py.discover_log_skeleton(dataframe, noise_threshold=0.1, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    properties = get_properties(
        log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)
    properties["noise_threshold"] = noise_threshold

    from pm4py.algo.discovery.log_skeleton import algorithm as log_skeleton_discovery
    return log_skeleton_discovery.apply(log, parameters=properties)


def discover_batches(log: Union[EventLog, pd.DataFrame], merge_distance: int = 15 * 60, min_batch_size: int = 2, activity_key: str = "concept:name", timestamp_key: str = "time:timestamp", case_id_key: str = "case:concept:name", resource_key: str = "org:resource") -> List[
        Tuple[Tuple[str, str], int, Dict[str, Any]]]:
    """
    Discover batches from the provided log object

    We say that an activity is executed in batches by a given resource when the resource executes several times the same activity in a short period of time.

    Identifying such activities may identify points of the process that can be automated, since the activity of the person may be repetitive.

    The following categories of batches are detected:
    - Simultaneous (all the events in the batch have identical start and end timestamps)
    - Batching at start (all the events in the batch have identical start timestamp)
    - Batching at end (all the events in the batch have identical end timestamp)
    - Sequential batching (for all the consecutive events, the end of the first is equal to the start of the second)
    - Concurrent batching (for all the consecutive events that are not sequentially matched)

    The approach has been described in the following paper:
    Martin, N., Swennen, M., Depaire, B., Jans, M., Caris, A., & Vanhoof, K. (2015, December). Batch Processing:
    Definition and Event Log Identification. In SIMPDA (pp. 137-140).

    The output is a (sorted) list containing tuples. Each tuple contain:
        - Index 0: the activity-resource for which at least one batch has been detected
        - Index 1: the number of batches for the given activity-resource
        - Index 2: a list containing all the batches. Each batch is described by:
            # The start timestamp of the batch
            # The complete timestamp of the batch
            # The list of events that are executed in the batch

    :param log: event log / Pandas dataframe
    :param merge_distance: the maximum time distance between non-overlapping intervals in order for them to be considered belonging to the same batch (default: 15*60   15 minutes)
    :param min_batch_size: the minimum number of events for a batch to be considered (default: 2)
    :param activity_key: attribute to be used for the activity
    :param timestamp_key: attribute to be used for the timestamp
    :param case_id_key: attribute to be used as case identifier
    :param resource_key: attribute to be used as resource
    :rtype: ``List[Tuple[Tuple[str, str], int, Dict[str, Any]]]``

    .. code-block:: python3

        import pm4py

        batches = pm4py.discover_log_skeleton(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp', resource_key='org:resource')
    """
    if type(log) not in [pd.DataFrame, EventLog, EventStream]:
        raise Exception(
            "the method can be applied only to a traditional event log!")
    __event_log_deprecation_warning(log)

    if check_is_pandas_dataframe(log):
        check_pandas_dataframe_columns(
            log, activity_key=activity_key, timestamp_key=timestamp_key, case_id_key=case_id_key)

    properties = get_properties(log, activity_key=activity_key, timestamp_key=timestamp_key,
                                case_id_key=case_id_key, resource_key=resource_key)
    properties["merge_distance"] = merge_distance
    properties["min_batch_size"] = min_batch_size

    from pm4py.algo.discovery.batches import algorithm as batches_discovery
    return batches_discovery.apply(log, parameters=properties)
