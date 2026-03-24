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
from copy import copy
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pandas as pd
from pm4py.algo.conformance.alignments.petri_net import algorithm as petri_alignments
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.objects.log.obj import EventLog, EventStream
from pm4py.objects.petri_net import semantics
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import align_utils as pn_align_utils, check_soundness
from pm4py.statistics.variants.log import get as variants_get
from pm4py.util import constants, exec_utils


class Parameters(Enum):
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY
    CASE_ID_KEY = constants.PARAMETER_CONSTANT_CASEID_KEY
    TOKEN_REPLAY_VARIANT = "token_replay_variant"
    CLEANING_TOKEN_FLOOD = "cleaning_token_flood"
    SHOW_PROGRESS_BAR = "show_progress_bar"
    MULTIPROCESSING = "multiprocessing"
    CORES = "cores"

    # Optional: if True, uses transition *names* (task IDs) as symbols instead of labels.
    # Useful to disambiguate duplicate labels. Still ignores invisible transitions.
    USE_TASK_IDS = "use_task_ids"


SKIP = ">>"
Prefix = Tuple[str, ...]


def _get_alignment_model_part(step: Any) -> Tuple[Any, Any]:
    """
    Extract (model_transition_name, model_label) from one alignment step.

    Expected format when PM4Py is called with ret_tuple_as_trans_desc=True:
        step == ( (log_trans_name, model_trans_name), (log_label, model_label) )
    where the first tuple comes from the sync-product transition name, and the second from its label.

    Returns
    -------
    model_trans_name, model_label
    """
    try:
        trans_desc, labels = step
        model_trans_name = trans_desc[1]
        model_label = labels[1]
        return model_trans_name, model_label
    except Exception as exc:
        raise ValueError(
            "Unexpected alignment step format. Make sure alignments are computed with "
            "parameters={'ret_tuple_as_trans_desc': True}."
        ) from exc


def _extract_model_sequence(
    alignment: List[Any], *, use_task_ids: bool = False
) -> List[str]:
    """
    Implements the paper's λ̄(γ): projection of *model moves* of an alignment γ,
    yielding a complete activity sequence of the model.

    - Log-only moves are ignored (model side '>>')
    - Invisible model moves are ignored (model label is None)
    - If use_task_ids=True: return model transition *names* (task IDs) for visible moves
      (still ignoring invisible transitions).
    """
    seq: List[str] = []
    for step in alignment:
        model_trans_name, model_label = _get_alignment_model_part(step)

        if model_trans_name == SKIP:
            continue

        if model_label is None or model_label == SKIP:
            continue

        if use_task_ids:
            seq.append(str(model_trans_name))
        else:
            seq.append(str(model_label))

    return seq


def _update_prefix_stats(
    seq: List[str],
    weight: int,
    next_by_prefix: Dict[Prefix, Set[str]],
    prefix_weight: Dict[Prefix, int],
) -> None:
    """
    For each prefix of seq (excluding the full seq), update:
      - next_by_prefix[prefix] : set(next symbols)
      - prefix_weight[prefix]  : ω(prefix) aggregated across traces/variants

    This corresponds to the paper's ω(s) for the Λ1 setting:
      ω(γ) = frequency(trace)
      ω(s) = Σ ω(γ) for all alignments γ whose λ̄(γ) has prefix s.
    """
    if len(seq) < 2:
        return

    prefix: Prefix = ()
    for i in range(len(seq) - 1):
        prefix = prefix + (seq[i],)
        next_sym = seq[i + 1]
        next_by_prefix.setdefault(prefix, set()).add(next_sym)
        prefix_weight[prefix] = prefix_weight.get(prefix, 0) + weight


def apply(
    log: Union[EventLog, EventStream, pd.DataFrame],
    net: PetriNet,
    im: Marking,
    fm: Marking,
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> float:
    """
    Alignment-based ETC precision (per "Measuring precision of modeled behavior").

    Summary of approach (Λ1 case):
      1) compute one optimal alignment per trace variant
      2) build the alignment automaton from λ̄(γ) (projection of model moves)
      3) compute precision from escaping edges:
           precision = 1 - (Σ ω(s)*|a_v(s) \\ e_x(s)|) / (Σ ω(s)*|a_v(s)|)

    Fixes vs the original snippet:
      - empty-prefix executed set taken from aligned sequences (not raw log)
      - available actions aggregated over all markings reached by the same prefix
      - tuple prefixes instead of comma-joined strings
      - robust log conversion and trace counting
    """
    if parameters is None:
        parameters = {}

    if not check_soundness.check_easy_soundness_net_in_fin_marking(net, im, fm):
        raise ValueError(
            "Align-ETC precision can only be applied on a Petri net that is "
            "a sound WF-net (easy sound)."
        )

    activity_key = exec_utils.get_param_value(
        Parameters.ACTIVITY_KEY, parameters, "concept:name"
    )
    debug_level = parameters.get("debug_level", 0)
    use_task_ids = bool(exec_utils.get_param_value(Parameters.USE_TASK_IDS, parameters, False))

    # Convert input to EventLog for consistent handling
    ev_log: EventLog = log_converter.apply(
        log, variant=log_converter.Variants.TO_EVENT_LOG, parameters=parameters
    )

    # 1) Variants -> align fewer traces (one per variant)
    variants = variants_get.get_variants(
        ev_log, parameters={constants.PARAMETER_CONSTANT_ACTIVITY_KEY: activity_key}
    )
    variant_keys = list(variants.keys())

    red_log = EventLog()
    variant_freqs: List[int] = []
    for vkey in variant_keys:
        traces = variants[vkey]
        if not traces:
            continue
        red_log.append(traces[0])
        variant_freqs.append(len(traces))

    # 2) Align each variant trace
    align_params = dict(parameters)
    align_params["ret_tuple_as_trans_desc"] = True
    aligned_variants = petri_alignments.apply(red_log, net, im, fm, parameters=align_params)

    trans_by_name = {t.name: t for t in net.transitions}

    # 3) Build automaton stats from aligned model projections λ̄(γ)
    next_by_prefix: Dict[Prefix, Set[str]] = {}
    prefix_weight: Dict[Prefix, int] = {}
    start_actions: Set[str] = set()

    # Collect all markings reached at each prefix across all aligned traces
    prefix_markings: Dict[Prefix, Set[Marking]] = {}

    for idx, aligned in enumerate(aligned_variants):
        alignment = aligned["alignment"]
        freq = variant_freqs[idx]

        seq = _extract_model_sequence(alignment, use_task_ids=use_task_ids)

        if seq:
            start_actions.add(seq[0])

        _update_prefix_stats(seq, freq, next_by_prefix, prefix_weight)

        if len(seq) < 2:
            continue

        max_prefix_len = len(seq) - 1  # exclude last symbol

        marking = copy(im)
        prefix: Prefix = ()
        seen_visible = 0

        for step in alignment:
            model_trans_name, model_label = _get_alignment_model_part(step)

            # Execute any model-side transition (sync or model-only, incl. invisible)
            if model_trans_name != SKIP:
                if model_trans_name not in trans_by_name:
                    raise KeyError(
                        f"Transition name {model_trans_name!r} from alignment not found in model."
                    )
                new_marking = semantics.execute(trans_by_name[model_trans_name], net, marking)
                if new_marking is None:
                    raise RuntimeError(
                        f"Alignment tried to fire transition {model_trans_name!r} "
                        f"which is not enabled in the current marking."
                    )
                marking = new_marking

            # Update prefix only for visible model moves
            if model_trans_name == SKIP:
                continue
            if model_label is None or model_label == SKIP:
                continue

            seen_visible += 1
            sym = str(model_trans_name) if use_task_ids else str(model_label)
            prefix = prefix + (sym,)

            if seen_visible <= max_prefix_len:
                prefix_markings.setdefault(prefix, set()).add(marking)
            else:
                break

    # 4) Compute available actions a_v(s) and escaping edges
    enabled_cache: Dict[Marking, Set[str]] = {}

    def enabled_symbols_at(m: Marking) -> Set[str]:
        if m in enabled_cache:
            return enabled_cache[m]
        vis_trans = pn_align_utils.get_visible_transitions_eventually_enabled_by_marking(net, m)
        if use_task_ids:
            enabled = {str(t.name) for t in vis_trans}
        else:
            enabled = {str(t.label) for t in vis_trans if t.label is not None}
        enabled_cache[m] = enabled
        return enabled

    sum_at = 0.0
    sum_ee = 0.0

    for prefix, markings in prefix_markings.items():
        if prefix not in prefix_weight:
            continue

        available: Set[str] = set()
        for m in markings:
            available |= enabled_symbols_at(m)

        executed = next_by_prefix.get(prefix, set())
        escaping = available.difference(executed)

        w = prefix_weight[prefix]
        sum_at += len(available) * w
        sum_ee += len(escaping) * w

    # 5) Empty prefix ε
    n_traces = len(ev_log)
    enabled_ini = enabled_symbols_at(im)
    escaping_ini = enabled_ini.difference(start_actions)

    sum_at += len(enabled_ini) * n_traces
    sum_ee += len(escaping_ini) * n_traces

    precision = 1.0
    if sum_at > 0:
        precision = 1.0 - float(sum_ee) / float(sum_at)

    if debug_level:
        print(
            "[Align-ETC Precision (aligned automaton)] "
            f"AT={sum_at:.0f} EE={sum_ee:.0f} precision={precision:.5f}"
        )

    return precision
