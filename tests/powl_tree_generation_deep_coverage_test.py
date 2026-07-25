import unittest
from unittest import mock

import pm4py

from pm4py.algo.simulation.tree_generator.variants import basic, ptandloggenerator
from pm4py.objects.conversion.process_tree.variants import to_petri_net
from pm4py.objects.conversion.wf_net.variants import to_powl as wf_to_powl
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import petri_utils
from pm4py.objects.powl.BinaryRelation import BinaryRelation
from pm4py.objects.powl.obj import (
    FrequentTransition,
    Operator,
    OperatorPOWL,
    Sequence,
    SilentTransition,
    StrictPartialOrder,
    Transition,
)
from pm4py.objects.process_tree.obj import ProcessTree


class PowlTreeGenerationDeepCoverageTest(unittest.TestCase):
    @staticmethod
    def _net(name, places, transitions, arcs):
        net = PetriNet(name)
        net.places.update(places)
        net.transitions.update(transitions)
        for source, target in arcs:
            petri_utils.add_arc_from_to(source, target, net)
        return net

    def test_binary_relation_mutation_transitivity_reduction_and_errors(self):
        relation = BinaryRelation(["a", "b", "c"])
        relation.add_edge("a", "b")
        relation.add_edge("b", "c")
        self.assertFalse(relation.is_transitive())
        relation.add_transitive_edges()
        self.assertTrue(relation.is_strict_partial_order())
        self.assertEqual(relation.get_start_nodes(), {"a"})
        self.assertEqual(relation.get_end_nodes(), {"c"})
        reduced = relation.get_transitive_reduction()
        self.assertFalse(reduced.is_edge("a", "c"))
        self.assertIn("a", repr(relation))

        relation.remove_edge_without_violating_transitivity("a", "b")
        self.assertFalse(relation.is_edge("a", "b"))
        relation.remove_edge("b", "c")
        relation.add_node("d")
        relation.add_node("d")
        self.assertEqual(len(relation.nodes), 4)
        self.assertEqual(len(relation.edges), 4)

        for operation in (
            lambda: relation.add_edge("missing", "a"),
            lambda: relation.remove_edge("a", "missing"),
            lambda: relation.remove_edge_without_violating_transitivity("missing", "a"),
            lambda: relation.is_edge("a", "missing"),
        ):
            with self.assertRaises(Exception):
                operation()

        reflexive = BinaryRelation(["x"])
        reflexive.add_edge("x", "x")
        self.assertFalse(reflexive.is_irreflexive())
        with self.assertRaises(ValueError):
            reflexive.get_transitive_reduction()

    def test_powl_comparison_validation_content_and_simplification_branches(self):
        a, b, c = Transition("A"), Transition("B"), Transition("C")
        self.assertNotEqual(a, b)
        self.assertTrue(a.equal_content(Transition("A")))
        self.assertFalse(a.equal_content(object()))
        self.assertTrue(a < b)
        self.assertTrue(a < StrictPartialOrder([Transition("Z")]))
        self.assertTrue(a < OperatorPOWL(Operator.XOR, [Transition("X"), Transition("Y")]))
        self.assertIs(a.__lt__(object()), NotImplemented)
        self.assertIn("partially ordered", a.model_description())
        with mock.patch("builtins.print") as printer:
            a.print()
            printer.assert_called_once()

        frequent_optional = FrequentTransition("A", 0, 1)
        frequent_loop = FrequentTransition("B", 1, "-")
        self.assertTrue(frequent_optional.skippable)
        self.assertTrue(frequent_loop.selfloop)

        order = StrictPartialOrder([a, b, c])
        order.add_edge(a, b)
        order.add_edge(b, c)
        order.add_edge(a, c)
        order.validate_partial_orders()
        copied = order.copy()
        self.assertTrue(order.equal_content(copied))
        self.assertFalse(order.equal_content(a))
        self.assertFalse(order.equal_content(StrictPartialOrder([Transition("A")])))
        self.assertIn("-->", order.to_string(indent=True, max_indent=3))
        self.assertIs(order.__lt__(object()), NotImplemented)

        mismatched_content = Sequence([Transition("A"), Transition("C"), Transition("B")])
        self.assertFalse(order.equal_content(mismatched_content))
        missing_edge = StrictPartialOrder([Transition("A"), Transition("B"), Transition("C")])
        self.assertFalse(order.equal_content(missing_edge))

        invalid_reflexive = StrictPartialOrder([Transition("R")])
        invalid_reflexive.add_edge(invalid_reflexive.children[0], invalid_reflexive.children[0])
        with self.assertRaises(Exception):
            invalid_reflexive.validate_partial_orders()
        invalid_transitive = StrictPartialOrder([Transition("1"), Transition("2"), Transition("3")])
        invalid_transitive.add_edge(invalid_transitive.children[0], invalid_transitive.children[1])
        invalid_transitive.add_edge(invalid_transitive.children[1], invalid_transitive.children[2])
        with self.assertRaises(Exception):
            invalid_transitive.validate_partial_orders()

        nested_free = StrictPartialOrder([Sequence([Transition("D"), Transition("E")]), Transition("F")])
        flattened_free = nested_free.simplify()
        self.assertEqual(len(flattened_free.children), 3)
        nested_connected = StrictPartialOrder(
            [Sequence([Transition("G"), Transition("H")]), Transition("I")]
        )
        nested_connected.add_edge(nested_connected.children[0], nested_connected.children[1])
        flattened_connected = nested_connected.simplify()
        self.assertGreaterEqual(len(flattened_connected.children), 3)
        self.assertTrue(
            nested_connected.simplify_using_frequent_transitions().equal_content(
                nested_connected
            )
        )

        optional_left = OperatorPOWL(Operator.XOR, [Transition("A"), SilentTransition()])
        optional_right = OperatorPOWL(Operator.XOR, [SilentTransition(), Transition("A")])
        loop_left = OperatorPOWL(Operator.LOOP, [Transition("A"), SilentTransition()])
        loop_right = OperatorPOWL(Operator.LOOP, [SilentTransition(), Transition("A")])
        for model in (optional_left, optional_right, loop_left, loop_right):
            self.assertIsInstance(model.simplify_using_frequent_transitions(), FrequentTransition)

        nested_xor = OperatorPOWL(
            Operator.XOR,
            [OperatorPOWL(Operator.XOR, [Transition("A"), Transition("B")]), Transition("C")],
        )
        self.assertEqual(len(nested_xor.simplify().children), 3)
        silent_loop_first = OperatorPOWL(
            Operator.XOR,
            [SilentTransition(), OperatorPOWL(Operator.LOOP, [SilentTransition(), Transition("A")])],
        )
        silent_loop_second = OperatorPOWL(
            Operator.XOR,
            [OperatorPOWL(Operator.LOOP, [Transition("A"), SilentTransition()]), SilentTransition()],
        )
        self.assertEqual(silent_loop_first.simplify().operator, Operator.LOOP)
        self.assertEqual(silent_loop_second.simplify().operator, Operator.LOOP)

        self.assertTrue(optional_left.equal_content(optional_left.copy()))
        self.assertFalse(optional_left.equal_content(a))
        self.assertFalse(optional_left.equal_content(loop_left))
        self.assertFalse(optional_left.equal_content(OperatorPOWL(Operator.XOR, [Transition("A"), Transition("B"), Transition("C")])))
        self.assertIs(optional_left.__lt__(object()), NotImplemented)
        with self.assertRaises(Exception):
            OperatorPOWL(Operator.XOR, [a])
        with self.assertRaises(Exception):
            OperatorPOWL(Operator.LOOP, [a])
        with self.assertRaises(Exception):
            OperatorPOWL(Operator.SEQUENCE, [a, b])

    def test_basic_tree_generator_all_operators_root_and_leaf(self):
        self.assertEqual(len(basic.generate_random_string(8)), 8)
        for value, expected in (
            (0.1, Operator.SEQUENCE),
            (0.3, Operator.LOOP),
            (0.6, Operator.XOR),
            (0.9, Operator.PARALLEL),
        ):
            with mock.patch.object(basic.random, "random", return_value=value):
                self.assertEqual(basic.get_random_operator(), expected)

        leaf = basic.apply(
            {
                basic.Parameters.REC_DEPTH: 3,
                basic.Parameters.MIN_REC_DEPTH: 0,
                basic.Parameters.MAX_REC_DEPTH: 1,
            }
        )
        self.assertIsNotNone(leaf.label)
        root = basic.apply(
            {
                basic.Parameters.MIN_REC_DEPTH: 0,
                basic.Parameters.MAX_REC_DEPTH: 0,
                basic.Parameters.PROB_LEAF: 0,
            }
        )
        self.assertEqual(root.operator, Operator.SEQUENCE)
        self.assertEqual(len(root.children), 3)

        for operator in (Operator.SEQUENCE, Operator.LOOP, Operator.XOR, Operator.PARALLEL):
            with mock.patch.object(basic, "get_random_operator", return_value=operator), mock.patch.object(
                basic.random, "randrange", return_value=2
            ):
                generated = basic.apply(
                    {
                        basic.Parameters.REC_DEPTH: 1,
                        basic.Parameters.MIN_REC_DEPTH: 0,
                        basic.Parameters.MAX_REC_DEPTH: 1,
                        basic.Parameters.PROB_LEAF: 0,
                    }
                )
            self.assertEqual(generated.operator, operator)
            self.assertGreaterEqual(len(generated.children), 2)

    def test_ptandlog_choices_parameters_operators_and_multiple_models(self):
        with mock.patch.object(ptandloggenerator.random, "random", return_value=0.1):
            self.assertEqual(ptandloggenerator.choices(["a", "b"], k=2), ["a", "a"])
            self.assertEqual(
                ptandloggenerator.choices(["a", "b"], weights=[1, 3], k=1), ["a"]
            )
            self.assertEqual(
                ptandloggenerator.choices(["a", "b"], cum_weights=[1, 4], k=1), ["a"]
            )
        with self.assertRaises(TypeError):
            ptandloggenerator.choices([1], weights=[1], cum_weights=[1])
        with self.assertRaises(ValueError):
            ptandloggenerator.choices([1, 2], weights=[1])
        for name, operator in (
            ("choice", Operator.XOR),
            ("sequence", Operator.SEQUENCE),
            ("parallel", Operator.PARALLEL),
            ("or", Operator.OR),
            ("loop", Operator.LOOP),
        ):
            self.assertEqual(ptandloggenerator.assign_operator(name), operator)
        self.assertIsNone(ptandloggenerator.assign_operator("unknown"))

        parameters = {
            "mode": 2,
            "min": 2,
            "max": 2,
            "sequence": 2,
            "choice": 1,
            "parallel": 1,
            "loop": 0,
            "or": 0,
            "silent": 0,
            "duplicate": 0,
            "no_models": 2,
        }
        models = ptandloggenerator.apply(parameters.copy())
        self.assertEqual(len(models), 2)
        single_parameters = parameters.copy()
        single_parameters["no_models"] = 1
        self.assertIsInstance(ptandloggenerator.apply(single_parameters), ProcessTree)

        generator = ptandloggenerator.GeneratedTree(single_parameters)
        generator.iter = generator.iter_all_strings()
        self.assertEqual(generator.get_next_activity(), "a")
        with mock.patch.object(ptandloggenerator, "choices", return_value=["or"]):
            self.assertEqual(generator.select_operator(), "or")
        distribution = generator.calculate_activity_distribution(2, 2, 2)
        self.assertIsNotNone(distribution)

    def test_wf_to_powl_clone_graph_cleanup_preprocess_and_boundaries(self):
        p0, p1, p2 = (PetriNet.Place(name) for name in ("p0", "p1", "p2"))
        tau = PetriNet.Transition("tau", None)
        a = PetriNet.Transition("a", "A")
        net = self._net("series", {p0, p1, p2}, {tau, a}, [(p0, tau), (tau, p1), (p1, a), (a, p2)])
        self.assertTrue(wf_to_powl.is_silent(tau))
        self.assertIsInstance(wf_to_powl.pn_transition_to_powl(tau), SilentTransition)
        self.assertIsInstance(wf_to_powl.pn_transition_to_powl(a), Transition)
        ids = wf_to_powl.id_generator()
        self.assertEqual((next(ids), next(ids)), ("id1", "id2"))
        graph = wf_to_powl.get_simplified_reachability_graph(net)
        self.assertIn(a, graph[tau])
        reachable = wf_to_powl.get_reachable_transitions_from_place_to_another(p0, p2)
        self.assertEqual(reachable, {tau, a})
        clone, clone_start, clone_end = wf_to_powl.clone_subnet(net, {tau, a}, p0, p2)
        self.assertEqual(len(clone.transitions), 2)
        self.assertIn(clone_start, clone.places)
        self.assertIn(clone_end, clone.places)

        start_places, end_places = wf_to_powl.remove_initial_and_end_silent_activities(
            net, {p0}, {p2}
        )
        self.assertEqual(start_places, {p1})
        self.assertEqual(end_places, {p2})

        # A trailing silent transition covers the symmetric end-cleanup branch.
        q0, q1, q2 = (PetriNet.Place(name) for name in ("q0", "q1", "q2"))
        b = PetriNet.Transition("b", "B")
        trailing = PetriNet.Transition("trailing", None)
        trailing_net = self._net(
            "trailing", {q0, q1, q2}, {b, trailing},
            [(q0, b), (b, q1), (q1, trailing), (trailing, q2)],
        )
        starts, ends = wf_to_powl.remove_initial_and_end_silent_activities(
            trailing_net, {q0}, {q2}
        )
        self.assertEqual(ends, {q1})

        duplicate_net = PetriNet("duplicates")
        d1, d2 = PetriNet.Place("d1"), PetriNet.Place("d2")
        duplicate_net.places.update({d1, d2})
        starts, ends = wf_to_powl.remove_duplicated_places(
            duplicate_net, {d1, d2}, {d1, d2}
        )
        self.assertEqual(len(duplicate_net.places), 1)
        self.assertEqual(len(starts), 1)
        self.assertEqual(len(ends), 1)

        isolated_net = PetriNet("isolated")
        isolated = PetriNet.Place("isolated")
        isolated_net.places.add(isolated)
        starts, ends = wf_to_powl.remove_unconnected_places(
            isolated_net, {isolated}, {isolated}
        )
        self.assertFalse(isolated_net.places)
        self.assertFalse(starts)
        self.assertFalse(ends)
        with self.assertRaises(Exception):
            wf_to_powl.add_new_start_and_end_if_needed(PetriNet("empty"), set(), set())

    def test_wf_to_powl_preprocess_shared_presets_postsets_and_translation_failures(self):
        # Identical places are merged by preprocessing.
        net = PetriNet("identical")
        p1, p2 = PetriNet.Place("p1"), PetriNet.Place("p2")
        net.places.update({p1, p2})
        wf_to_powl.preprocess(net)
        self.assertEqual(len(net.places), 1)

        # Two places with a shared two-transition preset trigger factoring.
        shared_pre = PetriNet("shared pre")
        p1, p2, e1, e2 = (PetriNet.Place(x) for x in ("p1", "p2", "e1", "e2"))
        left, right = PetriNet.Transition("left", "L"), PetriNet.Transition("right", "R")
        out1, out2 = PetriNet.Transition("out1", "O1"), PetriNet.Transition("out2", "O2")
        shared_pre.places.update({p1, p2, e1, e2})
        shared_pre.transitions.update({left, right, out1, out2})
        for edge in ((e1, left), (left, p1), (left, p2), (e2, right), (right, p1), (right, p2), (p1, out1), (p2, out2)):
            petri_utils.add_arc_from_to(*edge, shared_pre)
        wf_to_powl.preprocess(shared_pre)
        self.assertTrue(any(t.label is None for t in shared_pre.transitions))

        # Symmetric shared postset factoring.
        shared_post = PetriNet("shared post")
        p1, p2, s1, s2 = (PetriNet.Place(x) for x in ("p1", "p2", "s1", "s2"))
        in1, in2 = PetriNet.Transition("in1", "I1"), PetriNet.Transition("in2", "I2")
        left, right = PetriNet.Transition("left", "L"), PetriNet.Transition("right", "R")
        shared_post.places.update({p1, p2, s1, s2})
        shared_post.transitions.update({in1, in2, left, right})
        for edge in ((s1, in1), (in1, p1), (s2, in2), (in2, p2), (p1, left), (p2, left), (p1, right), (p2, right)):
            petri_utils.add_arc_from_to(*edge, shared_post)
        wf_to_powl.preprocess(shared_post)
        self.assertTrue(any(t.label is None for t in shared_post.transitions))

        for tree_text in ("->('A','B')", "X('A','B')", "+('A','B')", "*('A','B')"):
            tree = pm4py.parse_process_tree(tree_text)
            wf_net, _, _ = pm4py.convert_to_petri_net(tree)
            self.assertIsNotNone(wf_to_powl.apply(wf_net))

        invalid = PetriNet("cycle")
        place = PetriNet.Place("p")
        transition = PetriNet.Transition("t", "T")
        invalid.places.add(place)
        invalid.transitions.add(transition)
        petri_utils.add_arc_from_to(place, transition, invalid)
        petri_utils.add_arc_from_to(transition, place, invalid)
        with self.assertRaises(Exception):
            wf_to_powl.validate_workflow_net(invalid)

    def test_process_tree_to_petri_net_helpers_and_duplicate_cleanup(self):
        counts = to_petri_net.Counts()
        self.assertNotEqual(to_petri_net.get_new_place(counts).name, to_petri_net.get_new_place(counts).name)
        self.assertIsNone(to_petri_net.get_new_hidden_trans(counts).label)
        self.assertEqual(to_petri_net.get_transition(counts, "A").label, "A")

        tree = pm4py.parse_process_tree("->(*(X('A',tau),'B'),+('C','D'),O('E','F'))")
        first = to_petri_net.get_first_terminal_child_transitions(tree)
        last = to_petri_net.get_last_terminal_child_transitions(tree)
        self.assertTrue(first)
        self.assertTrue(last)
        self.assertIsInstance(to_petri_net.check_initial_loop(tree), bool)
        self.assertIsInstance(to_petri_net.check_terminal_loop(tree), bool)
        net, initial, final = to_petri_net.apply(tree)
        self.assertTrue(net.transitions)
        self.assertTrue(initial)
        self.assertTrue(final)

        duplicate_net = PetriNet("duplicate transitions")
        p0, p1 = PetriNet.Place("p0"), PetriNet.Place("p1")
        t1, t2 = PetriNet.Transition("t1", None), PetriNet.Transition("t2", None)
        duplicate_net.places.update({p0, p1})
        duplicate_net.transitions.update({t1, t2})
        for transition in (t1, t2):
            petri_utils.add_arc_from_to(p0, transition, duplicate_net)
            petri_utils.add_arc_from_to(transition, p1, duplicate_net)
        to_petri_net.clean_duplicate_transitions(duplicate_net)
        self.assertEqual(len(duplicate_net.transitions), 1)


if __name__ == "__main__":
    unittest.main()
