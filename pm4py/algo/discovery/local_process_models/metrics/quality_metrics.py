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
import uuid
from statistics import harmonic_mean

import pm4py.algo.simulation.playout.petri_net.variants.extensive as extensive_playout
from pm4py import filter_event_attribute_values, get_event_attribute_values, convert_to_dataframe
from pm4py import get_variants
from pm4py.algo.conformance.alignments.petri_net.algorithm import apply_trace, VERSION_STATE_EQUATION_A_STAR
from pm4py.algo.simulation.playout.petri_net import algorithm as playout_algo
from pm4py.convert import convert_to_petri_net
from pm4py.objects.log.obj import Trace, Event
from pm4py.objects.petri_net.obj import PetriNet
from pm4py.objects.petri_net.semantics import enabled_transitions, execute
from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to
from pm4py.util import constants


class LocalProcessModelStats(object):

    def __init__(self, frequency, determinism, confidence, language_fit, coverage, number_of_activities):
        self.frequency = frequency
        self.determinism = determinism
        self.confidence = confidence
        self.language_fit = language_fit
        self.coverage = coverage
        self.number_of_activities = number_of_activities


"""
Evaluates the quality of the local process model based on the 5 quality metrics.
Returns true if the tree should be extended, otherwise false.
If all 5 quality thresholds are met, the tree along with its stats is added to return_lpms.
"""
def evaluate_tree(log,
                  tree,
                  activities_used_in_model,
                  projected_log_variants_cache,
                  activity_key,
                  timestamp_key,
                  case_id_key,
                  iteration,
                  frequency_threshold, confidence_threshold, determinism_threshold,
                  language_fit_threshold, coverage_threshold,
                  return_lpms) -> bool:
    # we have only one final marking per petri net so we need to only add one transition
    ev_pn, ev_im, ev_fm, backloop_transition_name = __build_lpn_evaluation_petri_net(tree)

    variants, activity_occurrences, num_events = __get_projected_log_variants_and_metrics(
        projected_log_variants_cache, frozenset(activities_used_in_model),
        log, activity_key, timestamp_key, case_id_key)

    frequency, confidence, determinism, segments = __compute_freq_conf_det(
        ev_pn,
        ev_im,
        ev_fm,
        backloop_transition_name,
        activities_used_in_model,
        activity_key, timestamp_key, case_id_key,
        variants,
        activity_occurrences)

    if frequency < frequency_threshold or determinism < determinism_threshold:
        return False

    number_of_events_in_log = sum(len(trace) for trace in log)
    coverage = num_events / number_of_events_in_log
    if coverage < coverage_threshold or confidence < confidence_threshold:
        return True # no need to calculate language fit if coverage or confidence is already insufficient

    pn, im, fm = convert_to_petri_net(tree)
    language_fit = compute_language_fit(pn, im, fm, iteration, segments)

    if language_fit >= language_fit_threshold:
        stats = LocalProcessModelStats(frequency, determinism, confidence,
                                       language_fit, coverage, iteration)
        return_lpms.append((tree, stats))

    return True


def __build_lpn_evaluation_petri_net(tree):
    pn, im, fm = convert_to_petri_net(tree)

    backloop_transition_name = str(uuid.uuid4())
    loop_back_transition = PetriNet.Transition(
        backloop_transition_name, None
    )

    pn.transitions.add(loop_back_transition)
    for start_place in im.keys():
        add_arc_from_to(loop_back_transition, start_place, pn)

    for final_place in fm.keys():
        add_arc_from_to(final_place, loop_back_transition, pn)

    return pn, im, im, backloop_transition_name


def __compute_freq_conf_det(ev_pn, ev_im, ev_fm, backloop_transition_name,
                            activities_used_in_model,
                            activity_key, timestamp_key, case_id_key,
                            variants,
                            projected_log_activity_occurrences):


    parameters = {
        "case_id_key": case_id_key,
        "activity_key": activity_key,
        constants.PARAMETER_CONSTANT_ACTIVITY_KEY: activity_key,
        "timestamp_key": timestamp_key,
        "return_diagnostics_dataframe": False,
        "ret_tuple_as_trans_desc": True,
        "model_cost_function": {transition: 0 if transition.label is None else 99999999 for transition in ev_pn.transitions},
        "event_cost_function": {activity: 1 for activity in activities_used_in_model},
        "sync_cost_function": {t: 0 for t in ev_pn.transitions},
        "show_progress_bar": False,
    }

    alignments = []
    for trace, num in variants:
        alignment = apply_trace(
            trace,
            ev_pn,
            ev_im,
            ev_fm,
            parameters=parameters,
            variant=VERSION_STATE_EQUATION_A_STAR
        )
        alignments.append((alignment, num))

    number_of_model_executions = 0
    activities_occurences_in_model = {a: 0 for a in activities_used_in_model}

    seen_model_segments = set()

    for alignment, trace_count in alignments:
        current_segment = []
        num_segments = 0
        for step in alignment["alignment"]:
            (_, model_transition), (log_activity, model_activity) = step

            if model_activity != ">>" and log_activity == model_activity:
                activities_occurences_in_model[log_activity] += trace_count
                current_segment.append(log_activity)

            elif model_activity is None:
                if model_transition is backloop_transition_name:
                    if len(current_segment):
                        seen_model_segments.add(tuple(current_segment))
                        num_segments += 1
                        current_segment = []

        if len(current_segment) > 0:
            seen_model_segments.add(tuple(current_segment))
            num_segments += 1
        number_of_model_executions += num_segments * trace_count

    confidence_per_activity = [activities_occurences_in_model[a] / projected_log_activity_occurrences[i]
                               if projected_log_activity_occurrences[i] != 0
                               else 0
                               for i, a in enumerate(activities_used_in_model)]

    if any(map(lambda c: c == 0, confidence_per_activity)):
        confidence = 0
    else:
        confidence = harmonic_mean(confidence_per_activity)

    num_enabled_transitions = 0
    num_fired_transitions = 0
    for alignment, trace_count in alignments:
        current_marking = ev_im
        for step in alignment["alignment"]:
            (_, model_transition), (log_activity, model_activity) = step
            if model_activity != ">>":
                all_enabled = enabled_transitions(ev_pn, current_marking)
                fired_transition = next((t for t in all_enabled if t.name == model_transition), None)

                num_enabled_transitions += len(all_enabled) * trace_count
                num_fired_transitions += trace_count

                current_marking = execute(fired_transition, ev_pn, current_marking)

    determinism = num_fired_transitions / num_enabled_transitions if num_enabled_transitions > 0 else 0

    return number_of_model_executions, confidence, determinism, seen_model_segments


def compute_language_fit(pn, im, fm, iteration, traces_executed_during_alignments):
    n = iteration * 2 # should be greater or equal to iteration

    parameters = {
        extensive_playout.Parameters.MAX_TRACE_LENGTH: n
    }

    simulated_log = playout_algo.apply(
        pn,
        im,
        fm,
        variant=playout_algo.Variants.EXTENSIVE,
        parameters=parameters
    )

    allowed_variants = get_variants(simulated_log)
    total_traces = len(allowed_variants)

    match_count = 0
    for allowed_trace in allowed_variants:
        if allowed_trace in traces_executed_during_alignments:
            match_count += 1

    return match_count / total_traces if total_traces > 0 else 0


def __get_projected_log_variants_and_metrics(projected_log_variants_cache, activities_used_in_model, log, activity_key,
                                             timestamp_key, case_id_key):
    if frozenset(activities_used_in_model) in projected_log_variants_cache:
        return projected_log_variants_cache[frozenset(activities_used_in_model)]
    else:
        projected_log = filter_event_attribute_values(log,
                                                      case_id_key=case_id_key,
                                                      attribute_key=activity_key,
                                                      values=activities_used_in_model,
                                                      level="event")

        # this is a workaround since get_variants has an unexpected return value when passing EventLog types
        projected_log = convert_to_dataframe(projected_log)

        variants = [(Trace([Event({activity_key: e}) for e in trace]), num)
                    for trace, num in get_variants(projected_log,
                                                   case_id_key=case_id_key,
                                                   activity_key=activity_key,
                                                   timestamp_key=timestamp_key).items()]

        all_counts = get_event_attribute_values(projected_log, activity_key)
        activity_occurrences = [all_counts.get(a, 0) for a in activities_used_in_model]
        num_events = sum(activity_occurrences)

        projected_log_variants_cache[frozenset(activities_used_in_model)] = variants, activity_occurrences, num_events

        return variants, activity_occurrences, num_events