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

from pm4py.objects.ocel.obj import OCEL
from pm4py.algo.discovery.ocel.ocdfg.variants import classic as ocdfg_discovery
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from enum import Enum
from pm4py.util import exec_utils
from pm4py.objects.ocel import constants as ocel_constants
from collections import Counter
from typing import Optional, Dict, Any
from pm4py.objects.dfg.obj import DFG
from pm4py.objects.conversion.process_tree import converter as tree_converter
from pm4py.algo.conformance.tokenreplay import algorithm as token_based_replay
from pm4py.objects.ocel.util import flattening
from pm4py.objects.ocpn.obj import OCPetriNet
from pm4py.objects.ocpn import factory as ocpn_factory
from copy import copy


class Parameters(Enum):
    EVENT_ACTIVITY = ocel_constants.PARAM_EVENT_ACTIVITY
    OBJECT_ID = ocel_constants.PARAM_OBJECT_ID
    OBJECT_TYPE = ocel_constants.PARAM_OBJECT_TYPE
    INDUCTIVE_MINER_VARIANT = "inductive_miner_variant"
    DOUBLE_ARC_THRESHOLD = "double_arc_threshold"
    DIAGNOSTICS_WITH_TBR = "diagnostics_with_token_based_replay"


def apply(
    ocel: OCEL, parameters: Optional[Dict[Any, Any]] = None
) -> OCPetriNet:
    """
    Discovers an object-centric Petri net (without annotation) from the
    given object-centric event log, using the Inductive Miner as process
    discovery algorithm.

    Reference paper: van der Aalst, Wil MP, and Alessandro Berti. "Discovering object-centric Petri nets." Fundamenta informaticae 175.1-4 (2020): 1-40.

    Parameters
    ----------
    ocel
        Object-centric event log
    parameters
        Parameters of the algorithm, including:

        - Parameters.EVENT_ACTIVITY => the activity attribute to be used
        - Parameters.OBJECT_ID => the object identifier attribute to be used
        - Parameters.OBJECT_TYPE => the object type attribute to be used
        - Parameters.DOUBLE_ARC_THRESHOLD => the threshold for the attribution of the "double arc", as described in the paper.
        - Parameters.DIAGNOSTICS_WITH_TBR => performs token-based replay and stores the result in the return dict

    Returns
    -----------------
    ocpn
        Object-centric Petri net model. The returned object preserves the
        legacy dictionary payload for retro-compatibility with code that still
        accesses keys such as ``ocpn["petri_nets"]``.

    """
    if parameters is None:
        parameters = {}

    double_arc_threshold = exec_utils.get_param_value(
        Parameters.DOUBLE_ARC_THRESHOLD, parameters, 0.8
    )
    inductive_miner_variant = exec_utils.get_param_value(
        Parameters.INDUCTIVE_MINER_VARIANT, parameters, "im"
    )
    diagnostics_with_tbr = exec_utils.get_param_value(
        Parameters.DIAGNOSTICS_WITH_TBR, parameters, False
    )
    event_activity = exec_utils.get_param_value(
        Parameters.EVENT_ACTIVITY, parameters, ocel.event_activity
    )
    object_id = exec_utils.get_param_value(
        Parameters.OBJECT_ID, parameters, ocel.object_id_column
    )
    object_type = exec_utils.get_param_value(
        Parameters.OBJECT_TYPE, parameters, ocel.object_type_column
    )

    ocdfg_parameters = copy(parameters)
    ocdfg_parameters["compute_edges_performance"] = False
    ocpn = ocdfg_discovery.apply(ocel, parameters=ocdfg_parameters)
    activity_event_counts = Counter(ocel.events[event_activity])
    object_ids = {
        ot: set(ot_relations[object_id].unique())
        for ot, ot_relations in ocel.relations.groupby(object_type)
    }
    for ot in ocpn["object_types"]:
        object_ids.setdefault(ot, set())

    petri_nets = {}
    double_arcs_on_activity = {}
    tbr_results = {}

    for ot in ocpn["object_types"]:
        activities_eo = ocpn["activities_ot"]["total_objects"][ot]

        start_activities = {
            x: len(y)
            for x, y in ocpn["start_activities"]["events"][ot].items()
        }
        end_activities = {
            x: len(y) for x, y in ocpn["end_activities"]["events"][ot].items()
        }
        dfg = {}
        if ot in ocpn["edges"]["event_couples"]:
            dfg = {
                x: len(y)
                for x, y in ocpn["edges"]["event_couples"][ot].items()
            }

        is_activity_double = {}
        for act in activities_eo:
            ev_obj_count = Counter([x[0] for x in activities_eo[act]])
            single_object_events = 0
            for y in ev_obj_count.values():
                if y == 1:
                    single_object_events += 1

            total_activity_events = activity_event_counts[act]
            score = (
                single_object_events / total_activity_events
                if total_activity_events
                else 0
            )

            if score < double_arc_threshold:
                is_activity_double[act] = True
            else:
                is_activity_double[act] = False

        double_arcs_on_activity[ot] = is_activity_double

        im_parameters = copy(parameters)
        # disables the fallthroughs, as computing the model on a myriad of different object types
        # could be really expensive
        im_parameters["disable_fallthroughs"] = True
        # for performance reasons, also disable the strict sequence cut (use
        # the normal sequence cut)
        im_parameters["disable_strict_sequence_cut"] = True

        process_tree = None
        flat_log = None

        if inductive_miner_variant == "im" or diagnostics_with_tbr:
            # do the flattening only if it is required
            flat_log = flattening.flatten(ocel, ot, parameters=parameters)

        if inductive_miner_variant == "imd":
            obj = DFG()
            obj._graph = Counter(dfg)
            obj._start_activities = Counter(start_activities)
            obj._end_activities = Counter(end_activities)
            process_tree = inductive_miner.apply(
                obj,
                variant=inductive_miner.Variants.IMd,
                parameters=im_parameters,
            )
        elif inductive_miner_variant == "im":
            process_tree = inductive_miner.apply(
                flat_log, parameters=im_parameters
            )

        petri_net = tree_converter.apply(process_tree, parameters=parameters)

        if diagnostics_with_tbr:
            tbr_parameters = copy(parameters)
            tbr_parameters["enable_pltr_fitness"] = True
            tbr_parameters["show_progress_bar"] = False

            (
                replayed_traces,
                place_fitness_per_trace,
                transition_fitness_per_trace,
                notexisting_activities_in_model,
            ) = token_based_replay.apply(
                flat_log,
                petri_net[0],
                petri_net[1],
                petri_net[2],
                parameters=tbr_parameters,
            )
            place_diagnostics = {
                place: {"m": 0, "r": 0, "c": 0, "p": 0}
                for place in place_fitness_per_trace
            }
            trans_count = {trans: 0 for trans in petri_net[0].transitions}
            # computes the missing, remaining, consumed, and produced tokens
            # per place.
            for place, res in place_fitness_per_trace.items():
                place_diagnostics[place]["m"] += res["m"]
                place_diagnostics[place]["r"] += res["r"]
                place_diagnostics[place]["c"] += res["c"]
                place_diagnostics[place]["p"] += res["p"]

            # counts the number of times a transition has been fired during the
            # replay.
            for trace in replayed_traces:
                for trans in trace["activated_transitions"]:
                    trans_count[trans] += 1

            tbr_results[ot] = (place_diagnostics, trans_count)

        petri_nets[ot] = petri_net

    ocpn["petri_nets"] = petri_nets
    ocpn["double_arcs_on_activity"] = double_arcs_on_activity
    ocpn["object_ids"] = object_ids
    ocpn["tbr_results"] = tbr_results

    return ocpn_factory.create(ocpn)
