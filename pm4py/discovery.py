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
import warnings
from typing import Tuple

import deprecation

from pm4py.objects.heuristics_net.net import HeuristicsNet
from pm4py.objects.log.log import EventLog
from pm4py.objects.petri.petrinet import PetriNet, Marking
from pm4py.objects.process_tree.process_tree import ProcessTree


def discover_dfg(log: EventLog) -> Tuple[dict, dict, dict]:
    """
    Discovers a DFG from a log

    Parameters
    --------------
    log
        Event log

    Returns
    --------------
    dfg
        DFG
    start_activities
        Start activities
    end_activities
        End activities
    """
    from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
    dfg = dfg_discovery.apply(log)
    from pm4py.statistics.start_activities.log import get as start_activities_module
    from pm4py.statistics.end_activities.log import get as end_activities_module
    start_activities = start_activities_module.get_start_activities(log)
    end_activities = end_activities_module.get_end_activities(log)
    return dfg, start_activities, end_activities


def discover_petri_net_alpha(log: EventLog) -> Tuple[PetriNet, Marking, Marking]:
    """
    Discovers a Petri net using the Alpha Miner

    Parameters
    --------------
    log
        Event log

    Returns
    --------------
    petri_net
        Petri net
    initial_marking
        Initial marking
    final_marking
        Final marking
    """
    from pm4py.algo.discovery.alpha import algorithm as alpha_miner
    return alpha_miner.apply(log, variant=alpha_miner.Variants.ALPHA_VERSION_CLASSIC)


def discover_petri_net_alpha_plus(log: EventLog) -> Tuple[PetriNet, Marking, Marking]:
    """
    Discovers a Petri net using the Alpha+ algorithm

    Parameters
    --------------
    log
        Event log

    Returns
    --------------
    petri_net
        Petri net
    initial_marking
        Initial marking
    final_marking
        Final marking
    """
    from pm4py.algo.discovery.alpha import algorithm as alpha_miner
    return alpha_miner.apply(log, variant=alpha_miner.Variants.ALPHA_VERSION_PLUS)


def discover_petri_net_inductive(log: EventLog, noise_threshold: float = 0.0) -> Tuple[PetriNet, Marking, Marking]:
    """
    Discovers a Petri net using the IMDFc algorithm

    Parameters
    --------------
    log
        Event log
    noise_threshold
        Noise threshold (default: 0.0)

    Returns
    --------------
    petri_net
        Petri net
    initial_marking
        Initial marking
    final_marking
        Final marking
    """
    from pm4py.algo.discovery.inductive import algorithm as inductive_miner
    if noise_threshold > 0.0:
        return inductive_miner.apply(log, variant=inductive_miner.Variants.IMf, parameters={
            inductive_miner.Variants.IMf.value.Parameters.NOISE_THRESHOLD: noise_threshold})
    else:
        return inductive_miner.apply(log, variant=inductive_miner.Variants.IM, parameters={
            inductive_miner.Variants.IM.value.Parameters.NOISE_THRESHOLD: noise_threshold})


def discover_petri_net_heuristics(log: EventLog, dependency_threshold: float = 0.5, and_threshold: float = 0.65,
                                  loop_two_threshold: float = 0.5) -> Tuple[PetriNet, Marking, Marking]:
    """
    Discover a Petri net using the Heuristics Miner

    Parameters
    ---------------
    log
        Event log
    dependency_threshold
        Dependency threshold (default: 0.5)
    and_threshold
        AND threshold (default: 0.65)
    loop_two_threshold
        Loop two threshold (default: 0.5)

    Returns
    --------------
    petri_net
        Petri net
    initial_marking
        Initial marking
    final_marking
        Final marking
    """
    from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
    parameters = heuristics_miner.Variants.CLASSIC.value.Parameters
    return heuristics_miner.apply(log, variant=heuristics_miner.Variants.CLASSIC, parameters={
        parameters.DEPENDENCY_THRESH: dependency_threshold, parameters.AND_MEASURE_THRESH: and_threshold,
        parameters.LOOP_LENGTH_TWO_THRESH: loop_two_threshold})


def discover_process_tree_inductive(log: EventLog, noise_threshold: float = 0.0) -> ProcessTree:
    """
    Discovers a process tree using the IMDFc algorithm

    Parameters
    --------------
    log
        Event log
    noise_threshold
        Noise threshold (default: 0.0)

    Returns
    --------------
    process_tree
        Process tree object
    """
    from pm4py.algo.discovery.inductive import algorithm as inductive_miner
    if noise_threshold > 0.0:
        return inductive_miner.apply_tree(log, variant=inductive_miner.Variants.IMf, parameters={
            inductive_miner.Variants.IMf.value.Parameters.NOISE_THRESHOLD: noise_threshold})
    else:
        return inductive_miner.apply_tree(log, variant=inductive_miner.Variants.IM, parameters={
            inductive_miner.Variants.IM.value.Parameters.NOISE_THRESHOLD: noise_threshold})


@deprecation.deprecated(deprecated_in='2.2.2', removed_in='2.3.0',
                        details='discover_tree_inductive is deprecated, use discover_process_tree_inductive')
def discover_tree_inductive(log: EventLog, noise_threshold: float = 0.0) -> ProcessTree:
    warnings.warn('discover_tree_inductive is deprecated, use discover_process_tree_inductive', DeprecationWarning)
    """
    Discovers a process tree using the IMDFc algorithm

    Parameters
    --------------
    log
        Event log
    noise_threshold
        Noise threshold (default: 0.0)

    Returns
    --------------
    process_tree
        Process tree object
    """
    from pm4py.algo.discovery.inductive import algorithm as inductive_miner
    if noise_threshold > 0.0:
        return inductive_miner.apply_tree(log, variant=inductive_miner.Variants.IMf, parameters={
            inductive_miner.Variants.IMf.value.Parameters.NOISE_THRESHOLD: noise_threshold})
    else:
        return inductive_miner.apply_tree(log, variant=inductive_miner.Variants.IM, parameters={
            inductive_miner.Variants.IM.value.Parameters.NOISE_THRESHOLD: noise_threshold})


def discover_heuristics_net(log: EventLog, dependency_threshold: float = 0.5, and_threshold: float = 0.65,
                            loop_two_threshold: float = 0.5) -> HeuristicsNet:
    """
    Discovers an heuristics net

    Parameters
    ---------------
    log
        Event log
    dependency_threshold
        Dependency threshold (default: 0.5)
    and_threshold
        AND threshold (default: 0.65)
    loop_two_threshold
        Loop two threshold (default: 0.5)

    Returns
    --------------
    heu_net
        Heuristics net
    """
    from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
    parameters = heuristics_miner.Variants.CLASSIC.value.Parameters
    return heuristics_miner.apply_heu(log, variant=heuristics_miner.Variants.CLASSIC, parameters={
        parameters.DEPENDENCY_THRESH: dependency_threshold, parameters.AND_MEASURE_THRESH: and_threshold,
        parameters.LOOP_LENGTH_TWO_THRESH: loop_two_threshold})
