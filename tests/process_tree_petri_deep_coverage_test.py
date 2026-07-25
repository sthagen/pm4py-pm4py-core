import unittest

import pm4py
from pm4py.objects.conversion.process_tree import converter as pt_converter
from pm4py.objects.conversion.process_tree.variants import to_petri_net
from pm4py.objects.conversion.wf_net.variants import to_powl as wf_to_powl
from pm4py.objects.log.obj import Event, Trace
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import petri_utils, reduction
from pm4py.objects.process_tree import state as pt_state
from pm4py.objects.process_tree.obj import Operator, ProcessTree
from pm4py.objects.process_tree.utils import generic


class ProcessTreePetriDeepCoverageTest(unittest.TestCase):
    def test_all_process_tree_patterns_across_conversion_variants(self):
        patterns = (
            "'A'",
            "->( 'A', 'B', 'C' )",
            "X( 'A', 'B', tau )",
            "+( 'A', 'B', 'C' )",
            "*( 'A', 'B' )",
            "O( 'A', 'B', tau )",
            "->( X( 'A', 'B' ), +( 'C', 'D' ), *( 'E', 'F' ) )",
        )
        for text in patterns:
            tree = pm4py.parse_process_tree(text)
            net, initial, final = pt_converter.apply(tree)
            self.assertTrue(net.transitions)
            self.assertTrue(initial)
            self.assertTrue(final)
            if tree.operator is not Operator.OR:
                self.assertIsNotNone(pm4py.convert_to_powl(net, initial, final))
            self.assertTrue(pt_converter.apply(tree, variant=pt_converter.Variants.TO_BPMN).get_nodes())
            if tree.operator is Operator.OR:
                with self.assertRaises(Exception):
                    pt_converter.apply(tree, variant=pt_converter.Variants.TO_POWL)
            else:
                self.assertIsNotNone(
                    pt_converter.apply(tree, variant=pt_converter.Variants.TO_POWL)
                )
                bordered, bordered_im, bordered_fm = pt_converter.apply(
                    tree,
                    variant=pt_converter.Variants.TO_PETRI_NET_TRANSITION_BORDERED,
                )
                self.assertTrue(bordered.transitions)
                self.assertTrue(bordered_im)
                self.assertTrue(bordered_fm)

        counts = to_petri_net.Counts()
        self.assertNotEqual(
            to_petri_net.get_new_place(counts), to_petri_net.get_new_place(counts)
        )
        self.assertIsNone(to_petri_net.get_new_hidden_trans(counts).label)
        self.assertEqual("visible", to_petri_net.get_transition(counts, "visible").label)
        leaf = pm4py.parse_process_tree("'leaf'")
        self.assertEqual([], to_petri_net.get_first_terminal_child_transitions(leaf))
        self.assertEqual([], to_petri_net.get_last_terminal_child_transitions(leaf))

    def test_generic_tree_reduction_comparison_and_navigation(self):
        nested = pm4py.parse_process_tree(
            "->( tau, ->( 'A', tau, 'B' ), +( tau, tau ), X( tau, tau, 'C' ) )"
        )
        folded = generic.fold(nested)
        self.assertLess(len(str(folded)), len(str(nested)))
        self.assertTrue(generic.get_leaves(folded))
        self.assertEqual(len(generic.get_leaves(folded)), len(generic.get_leaves_as_tuples(folded)))
        self.assertGreater(generic.get_process_tree_height(folded), 1)
        generic.tree_sort(folded)

        first = pm4py.parse_process_tree("+( 'A', X( 'B', 'C' ), 'D' )")
        second = pm4py.parse_process_tree("+( 'D', X( 'C', 'B' ), 'A' )")
        different = pm4py.parse_process_tree("->( 'A', 'D' )")
        self.assertTrue(generic.structurally_language_equal(first, second))
        self.assertFalse(generic.structurally_language_equal(first, different))
        binary = generic.process_tree_to_binary_process_tree(first)
        self.assertLessEqual(len(binary.children), 2)

        leaves = list(generic.get_leaves(binary))
        ancestor = generic.common_ancestor(leaves[0], leaves[-1])
        self.assertIsNotNone(ancestor)
        self.assertTrue(generic.get_ancestors_until(leaves[0], ancestor))
        self.assertEqual([], generic.get_ancestors_until(ancestor, ancestor))
        self.assertIsNone(generic.get_ancestors_until(leaves[0], ProcessTree(label="outside")))
        self.assertTrue(generic.is_root(binary))
        self.assertTrue(generic.is_operator(binary, Operator.PARALLEL))
        self.assertTrue(generic.is_any_operator_of(binary, [Operator.XOR, Operator.PARALLEL]))
        state_map = {(id(binary), binary): ProcessTree.OperatorState.OPEN}
        self.assertTrue(
            generic.is_in_state(binary, ProcessTree.OperatorState.OPEN, state_map)
        )

        execution = [(leaves[0], pt_state.State.OPEN), (binary, pt_state.State.CLOSED)]
        self.assertEqual([leaves[0]], generic.project_execution_sequence_to_leafs(execution))
        self.assertEqual([leaves[0].label], generic.project_execution_sequence_to_labels(execution))
        for tau in ("tau", "τ", "\u03c4"):
            self.assertTrue(generic.is_tau_leaf(generic.parse(tau)))

    @staticmethod
    def _series_with_silent():
        net = PetriNet("silent series")
        p0, p1, p2, p3 = [PetriNet.Place(f"p{i}") for i in range(4)]
        a = PetriNet.Transition("a", "A")
        tau = PetriNet.Transition("tau", None)
        b = PetriNet.Transition("b", "B")
        net.places.update({p0, p1, p2, p3})
        net.transitions.update({a, tau, b})
        for source, target in (
            (p0, a), (a, p1), (p1, tau), (tau, p2), (p2, b), (b, p3)
        ):
            petri_utils.add_arc_from_to(source, target, net)
        return net, Marking({p0: 1}), Marking({p3: 1}), (p0, p1, p2, p3), (a, tau, b)

    def test_petri_utility_trace_paths_components_and_mutations(self):
        trace = Trace(
            [Event({"concept:name": "A"}), Event({"concept:name": "B"})],
            attributes={"concept:name": "case"},
        )
        trace_net, trace_im, trace_fm = petri_utils.construct_trace_net(trace)
        cost_net, _, _, costs = petri_utils.construct_trace_net_cost_aware(trace, [3, 7])
        self.assertEqual(2, len(trace_net.transitions))
        self.assertEqual({3, 7}, set(costs.values()))
        self.assertEqual(1, len(petri_utils.acyclic_net_variants(trace_net, trace_im, trace_fm)))
        transition = next(iter(cost_net.transitions))
        self.assertIs(transition, petri_utils.get_transition_by_name(cost_net, transition.name))
        self.assertIsNone(petri_utils.get_transition_by_name(cost_net, "missing"))

        net, initial, final, places, transitions = self._series_with_silent()
        self.assertTrue(petri_utils.is_sub_marking(Marking({places[0]: 2}), initial))
        self.assertEqual(initial, petri_utils.place_set_as_marking({places[0]}))
        self.assertEqual({transitions[0]}, petri_utils.post_set(places[0]))
        self.assertEqual({places[0]}, petri_utils.pre_set(transitions[0]))
        petri_utils.decorate_transitions_prepostset(net)
        petri_utils.decorate_places_preset_trans(net)
        shortest = petri_utils.get_places_shortest_path_by_hidden(net, 10)
        self.assertIn(places[2], shortest[places[1]])
        self.assertTrue(petri_utils.invert_spaths_dictionary(shortest))
        self.assertTrue(petri_utils.get_s_components_from_petri(net, initial, final))

        extra_place = petri_utils.add_place(net, "isolated")
        extra_transition = petri_utils.add_transition(net, "isolated transition", "I")
        petri_utils.remove_unconnected_components(net)
        self.assertNotIn(extra_place, net.places)
        self.assertNotIn(extra_transition, net.transitions)

        other = PetriNet("other")
        op = petri_utils.add_place(other, "op")
        ot = petri_utils.add_transition(other, "ot", "O")
        petri_utils.add_arc_from_to(op, ot, other)
        merged = petri_utils.merge(nets=[net, other])
        self.assertGreaterEqual(len(merged.transitions), len(net.transitions))

    def test_reductions_and_wf_net_to_powl_helpers(self):
        net, initial, final, places, transitions = self._series_with_silent()
        reduction.apply_simple_reduction(net)
        self.assertLess(len(net.transitions), 3)

        # Parallel silent transitions exercise FPT; parallel places exercise FPP.
        parallel = PetriNet("parallel")
        source, sink = PetriNet.Place("source"), PetriNet.Place("sink")
        t1, t2 = PetriNet.Transition("t1"), PetriNet.Transition("t2")
        parallel.places.update({source, sink})
        parallel.transitions.update({t1, t2})
        for transition in (t1, t2):
            petri_utils.add_arc_from_to(source, transition, parallel)
            petri_utils.add_arc_from_to(transition, sink, parallel)
        reduction.apply_fpt_rule(parallel)
        self.assertEqual(1, len(parallel.transitions))
        self.assertEqual(2 ** len(parallel.places), len(list(reduction.power_set(parallel.places))))

        for text in (
            "'A'",
            "->( 'A', 'B', 'C' )",
            "X( 'A', 'B', 'C' )",
            "+( 'A', 'B', 'C' )",
            "*( 'A', 'B' )",
        ):
            tree = pm4py.parse_process_tree(text)
            wf_net, im, fm = pm4py.convert_to_petri_net(tree)
            model = wf_to_powl.apply(wf_net)
            self.assertIsNotNone(model)

        invalid = PetriNet("invalid")
        invalid.places.update({PetriNet.Place("a"), PetriNet.Place("b")})
        with self.assertRaises(Exception):
            wf_to_powl.validate_workflow_net(invalid)
        self.assertIsNone(wf_to_powl.mine_base_case(invalid))
        self.assertIsNone(wf_to_powl.mine_self_loop(invalid, *list(invalid.places)))


if __name__ == "__main__":
    unittest.main()
