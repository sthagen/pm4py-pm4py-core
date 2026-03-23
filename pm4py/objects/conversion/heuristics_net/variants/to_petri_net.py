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
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to, remove_transition
from pm4py.util import nx_utils


def remove_rendundant_invisible_transitions(net):
    """
    Remove redundant transitions from Petri net

    Parameters
    -----------
    net
        Petri net

    Returns
    -----------
    net
        Cleaned net
    """
    trans = [x for x in list(net.transitions) if not x.label]
    i = 0
    while i < len(trans):
        if trans[i] in net.transitions:
            preset_i = set(x.source for x in trans[i].in_arcs)
            postset_i = set(x.target for x in trans[i].out_arcs)
            j = 0
            while j < len(trans):
                if not j == i:
                    preset_j = set(x.source for x in trans[j].in_arcs)
                    postset_j = set(x.target for x in trans[j].out_arcs)
                    if len(preset_j) == len(preset_i) and len(postset_j) < len(postset_i):
                        if (
                            len(preset_j.intersection(preset_i)) == len(preset_j)
                            and len(postset_j.intersection(postset_i)) == len(postset_j)
                        ):
                            remove_transition(net, trans[j])
                            del trans[j]
                            continue
                j = j + 1
            i = i + 1
    return net


def find_bindings(and_measures):
    """
    Find the bindings given the AND measures.

    NOTE: and_measures_in/out is stored asymmetrically (only one direction
    for each unordered pair). We build an undirected graph and take maximal cliques.
    """
    G = nx_utils.Graph()

    # FIX 1: build the graph correctly (and don't mis-add n1 instead of n2)
    for n1, rels in and_measures.items():
        G.add_node(n1)
        for n2 in rels:
            G.add_node(n2)
            G.add_edge(n1, n2)

    return list(nx_utils.find_cliques(G))


def apply(heu_net, parameters=None):
    """
    Converts an Heuristics Net to a Petri net

    Parameters
    --------------
    heu_net
        Heuristics net
    parameters
        Possible parameters of the algorithm

    Returns
    --------------
    net
        Petri net
    im
        Initial marking
    fm
        Final marking
    """
    if parameters is None:
        parameters = {}

    net = PetriNet("")
    im = Marking()
    fm = Marking()

    source_places = []
    sink_places = []
    hid_trans_count = 0

    # Create one source/sink place per (possibly merged) start/end set (kept as in original)
    for index, sa_list in enumerate(heu_net.start_activities):
        source = PetriNet.Place("source" + str(index))
        source_places.append(source)
        net.places.add(source)
        im[source] = 1

    for index, ea_list in enumerate(heu_net.end_activities):
        sink = PetriNet.Place("sink" + str(index))
        sink_places.append(sink)
        net.places.add(sink)
        fm[sink] = 1

    act_trans = {}
    who_is_entering = {}
    who_is_exiting = {}

    # Build transitions and predecessor/successor relations
    for act1_name in heu_net.nodes:
        act1 = heu_net.nodes[act1_name]

        if act1_name not in act_trans:
            act_trans[act1_name] = PetriNet.Transition(act1_name, act1_name)
            net.transitions.add(act_trans[act1_name])
            who_is_entering[act1_name] = set()
            who_is_exiting[act1_name] = set()

            for index, sa_list in enumerate(heu_net.start_activities):
                if act1_name in sa_list:
                    who_is_entering[act1_name].add((None, index))

            for index, ea_list in enumerate(heu_net.end_activities):
                if act1_name in ea_list:
                    who_is_exiting[act1_name].add((None, index))

        for act2 in act1.output_connections:
            act2_name = act2.node_name

            if act2_name not in act_trans:
                act_trans[act2_name] = PetriNet.Transition(act2_name, act2_name)
                net.transitions.add(act_trans[act2_name])
                who_is_entering[act2_name] = set()
                who_is_exiting[act2_name] = set()

                for index, sa_list in enumerate(heu_net.start_activities):
                    if act2_name in sa_list:
                        who_is_entering[act2_name].add((None, index))

                for index, ea_list in enumerate(heu_net.end_activities):
                    if act2_name in ea_list:
                        who_is_exiting[act2_name].add((None, index))

            who_is_entering[act2_name].add((act1_name, None))
            who_is_exiting[act1_name].add((act2_name, None))

    # -------------------------
    # Build "entering" structure
    # -------------------------
    places_entering = {}

    for act in who_is_entering:
        places_entering[act] = {}

        entering = list(who_is_entering[act])
        entering_preds = sorted([x for x in entering if x[0] is not None], key=lambda x: x[0])
        entering_sources = [x for x in entering if x[0] is None]

        # FIX 3: master_place must exist also when there are multiple sources only (merged nets)
        # Additionally, if there is at least one predecessor, we need a place before the activity transition.
        master_place = None
        if entering_preds or len(entering) > 1:
            master_place = PetriNet.Place("pre_" + act)
            net.places.add(master_place)
            add_arc_from_to(master_place, act_trans[act], net)

        # --- AND-joins (based on cliques) ---
        # FIX 2: do NOT rely on `if pred in and_measures_in` because the structure is asymmetric.
        cliques = find_bindings(heu_net.nodes[act].and_measures_in)
        pred_names = [p[0] for p in entering_preds]
        pred_names_set = set(pred_names)

        and_members = set()
        for clique in cliques:
            clique = [n for n in clique if n in pred_names_set]
            if len(clique) < 2:
                continue
            and_members.update(clique)

            hid_trans_count += 1
            hid_trans = PetriNet.Transition("hid_" + str(hid_trans_count), None)
            net.transitions.add(hid_trans)

            add_arc_from_to(hid_trans, master_place, net)

            for pred in clique:
                key = (pred, None)
                if key not in places_entering[act]:
                    s_place = PetriNet.Place(f"splace_in_{act}_{pred}")
                    net.places.add(s_place)
                    places_entering[act][key] = s_place
                add_arc_from_to(places_entering[act][key], hid_trans, net)

        # --- Remaining predecessors (OR-join / simple sequence) ---
        for pred_tuple in entering_preds:
            pred_name = pred_tuple[0]
            if pred_name in and_members:
                continue

            if len(entering) == 1:
                # Single predecessor only: connect directly to the master place
                places_entering[act][pred_tuple] = master_place
            else:
                # Multiple incoming alternatives: keep an explicit s_place + hid transition (as in original)
                key = pred_tuple
                if key not in places_entering[act]:
                    s_place = PetriNet.Place(f"splace_in_{act}_{pred_name}")
                    net.places.add(s_place)
                    places_entering[act][key] = s_place

                hid_trans_count += 1
                hid_trans = PetriNet.Transition("hid_" + str(hid_trans_count), None)
                net.transitions.add(hid_trans)

                add_arc_from_to(places_entering[act][key], hid_trans, net)
                add_arc_from_to(hid_trans, master_place, net)

        # --- Sources ---
        for src_tuple in entering_sources:
            src_idx = src_tuple[1]
            if len(entering) == 1:
                add_arc_from_to(source_places[src_idx], act_trans[act], net)
            else:
                hid_trans_count += 1
                hid_trans = PetriNet.Transition("hid_" + str(hid_trans_count), None)
                net.transitions.add(hid_trans)

                add_arc_from_to(source_places[src_idx], hid_trans, net)
                add_arc_from_to(hid_trans, master_place, net)

    # ------------------------
    # Build "exiting" structure
    # ------------------------
    for act in who_is_exiting:
        exiting = list(who_is_exiting[act])
        exiting_succs = sorted([x for x in exiting if x[0] is not None], key=lambda x: x[0])
        exiting_sinks = [x for x in exiting if x[0] is None]

        # Simple case: only one successor
        if len(exiting) == 1 and exiting_succs:
            succ = exiting_succs[0][0]
            if (act, None) in places_entering.get(succ, {}):
                add_arc_from_to(act_trans[act], places_entering[succ][(act, None)], net)
            continue

        # Simple case: only one sink
        if len(exiting) == 1 and exiting_sinks:
            sink_idx = exiting_sinks[0][1]
            add_arc_from_to(act_trans[act], sink_places[sink_idx], net)
            continue

        # FIX 3: int_place must exist also when there are multiple sinks only (merged nets)
        int_place = PetriNet.Place("intplace_" + str(act))
        net.places.add(int_place)
        add_arc_from_to(act_trans[act], int_place, net)

        # AND-splits (based on cliques)
        cliques = find_bindings(heu_net.nodes[act].and_measures_out)
        succ_names = [x[0] for x in exiting_succs]
        succ_names_set = set(succ_names)

        and_members = set()
        for clique in cliques:
            clique = [n for n in clique if n in succ_names_set]
            if len(clique) < 2:
                continue
            and_members.update(clique)

            hid_trans_count += 1
            hid_trans = PetriNet.Transition("hid_" + str(hid_trans_count), None)
            net.transitions.add(hid_trans)

            add_arc_from_to(int_place, hid_trans, net)

            for succ in clique:
                if (act, None) in places_entering.get(succ, {}):
                    add_arc_from_to(hid_trans, places_entering[succ][(act, None)], net)

        # Remaining successors (OR-split)
        for succ_tuple in exiting_succs:
            succ = succ_tuple[0]
            if succ in and_members:
                continue
            if (act, None) in places_entering.get(succ, {}):
                hid_trans_count += 1
                hid_trans = PetriNet.Transition("hid_" + str(hid_trans_count), None)
                net.transitions.add(hid_trans)

                add_arc_from_to(int_place, hid_trans, net)
                add_arc_from_to(hid_trans, places_entering[succ][(act, None)], net)

        # Sinks
        for sink_tuple in exiting_sinks:
            sink_idx = sink_tuple[1]

            hid_trans_count += 1
            hid_trans = PetriNet.Transition("hid_" + str(hid_trans_count), None)
            net.transitions.add(hid_trans)

            add_arc_from_to(int_place, hid_trans, net)
            add_arc_from_to(hid_trans, sink_places[sink_idx], net)

    # Cleanup + reductions
    net = remove_rendundant_invisible_transitions(net)

    from pm4py.objects.petri_net.utils import reduction
    reduction.apply_simple_reduction(net)

    return net, im, fm
