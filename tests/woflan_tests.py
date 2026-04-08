import os
import numpy as np
from pm4py.algo.analysis.woflan import algorithm as woflan
from pm4py.objects.log.importer.xes import importer as xes_import
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.algo.discovery.alpha import algorithm as alpha_miner
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils
from pm4py.algo.analysis.woflan.graphs.minimal_coverability_graph import minimal_coverability_graph
import unittest
from unittest import mock
from pm4py.objects.conversion.process_tree import converter as process_tree_converter
from pm4py.util import nx_utils


class WoflanTest(unittest.TestCase):
    def test_running_example_alpha(self):
        path = os.path.join("input_data", "running-example.xes")
        log = xes_import.apply(path)
        net, i_m, f_m = alpha_miner.apply(log)
        self.assertTrue(woflan.apply(net, i_m, f_m, parameters={"print_diagnostics": False}))

    def test_running_example_inductive(self):
        path = os.path.join("input_data", "running-example.xes")
        log = xes_import.apply(path)
        process_tree = inductive_miner.apply(log)
        net, im, fm = process_tree_converter.apply(process_tree)
        self.assertTrue(woflan.apply(net, im, fm, parameters={"print_diagnostics": False}))

    def test_figure415(self):
        net = PetriNet("figure_4_15")
        p_1 = PetriNet.Place("p_1")
        p_2 = PetriNet.Place("p_2")
        p_3 = PetriNet.Place("p_3")
        p_4 = PetriNet.Place("p_4")
        p_5 = PetriNet.Place("p_5")
        p_6 = PetriNet.Place("p_6")
        p_7 = PetriNet.Place("p_7")
        net.places.add(p_1)
        net.places.add(p_2)
        net.places.add(p_3)
        net.places.add(p_4)
        net.places.add(p_5)
        net.places.add(p_6)
        net.places.add(p_7)
        t_1 = PetriNet.Transition("t_1", "t_1")
        t_2 = PetriNet.Transition("t_2", "t_2")
        t_3 = PetriNet.Transition("t_3", "t_3")
        t_4 = PetriNet.Transition("t_4", "t_4")
        t_5 = PetriNet.Transition("t_5", "t_5")
        t_6 = PetriNet.Transition("t_6", "t_6")
        net.transitions.add(t_1)
        net.transitions.add(t_2)
        net.transitions.add(t_3)
        net.transitions.add(t_4)
        net.transitions.add(t_5)
        net.transitions.add(t_6)
        petri_utils.add_arc_from_to(p_1, t_1, net)
        petri_utils.add_arc_from_to(t_1, p_3, net)
        petri_utils.add_arc_from_to(t_1, p_2, net)
        petri_utils.add_arc_from_to(t_1, p_5, net)
        petri_utils.add_arc_from_to(p_5, t_2, net)
        petri_utils.add_arc_from_to(p_5, t_5, net)
        petri_utils.add_arc_from_to(p_3, t_2, net)
        petri_utils.add_arc_from_to(p_3, t_4, net)
        petri_utils.add_arc_from_to(t_2, p_6, net)
        petri_utils.add_arc_from_to(t_2, p_4, net)
        petri_utils.add_arc_from_to(t_5, p_5, net)
        petri_utils.add_arc_from_to(t_5, p_3, net)
        petri_utils.add_arc_from_to(p_2, t_2, net)
        petri_utils.add_arc_from_to(t_3, p_2, net)
        petri_utils.add_arc_from_to(t_3, p_3, net)
        petri_utils.add_arc_from_to(t_3, p_4, net)
        petri_utils.add_arc_from_to(p_6, t_5, net)
        petri_utils.add_arc_from_to(p_6, t_6, net)
        petri_utils.add_arc_from_to(p_6, t_3, net)
        petri_utils.add_arc_from_to(t_4, p_6, net)
        petri_utils.add_arc_from_to(t_4, p_5, net)
        petri_utils.add_arc_from_to(p_4, t_3, net)
        petri_utils.add_arc_from_to(p_4, t_6, net)
        petri_utils.add_arc_from_to(p_4, t_4, net)
        petri_utils.add_arc_from_to(t_6, p_7, net)
        initial_marking = Marking()
        initial_marking[p_1] = 1
        final_marking = Marking()
        final_marking[p_7] = 1
        self.assertTrue(woflan.apply(net, initial_marking, final_marking, parameters={"print_diagnostics": False}))

    def test_figure42(self):
        net = PetriNet("figure_4_2")
        p_1 = PetriNet.Place("p_1")
        p_2 = PetriNet.Place("p_2")
        p_3 = PetriNet.Place("p_3")
        p_4 = PetriNet.Place("p_4")
        p_5 = PetriNet.Place("p_5")
        p_6 = PetriNet.Place("p_6")
        p_7 = PetriNet.Place("p_7")
        p_8 = PetriNet.Place("p_8")
        net.places.add(p_1)
        net.places.add(p_2)
        net.places.add(p_3)
        net.places.add(p_4)
        net.places.add(p_5)
        net.places.add(p_6)
        net.places.add(p_7)
        net.places.add(p_8)
        t_1 = PetriNet.Transition("t_1", "t_1")
        t_2 = PetriNet.Transition("t_2", "t_2")
        t_3 = PetriNet.Transition("t_3", "t_3")
        t_4 = PetriNet.Transition("t_4", "t_4")
        t_5 = PetriNet.Transition("t_5", "t_5")
        t_6 = PetriNet.Transition("t_6", "t_6")
        t_7 = PetriNet.Transition("t_7", "t_7")
        t_8 = PetriNet.Transition("t_8", "t_8")
        net.transitions.add(t_1)
        net.transitions.add(t_2)
        net.transitions.add(t_3)
        net.transitions.add(t_4)
        net.transitions.add(t_5)
        net.transitions.add(t_6)
        net.transitions.add(t_7)
        net.transitions.add(t_8)
        petri_utils.add_arc_from_to(p_1, t_1, net)
        petri_utils.add_arc_from_to(t_1, p_6, net)
        petri_utils.add_arc_from_to(t_1, p_4, net)
        petri_utils.add_arc_from_to(p_4, t_4, net)
        petri_utils.add_arc_from_to(p_4, t_5, net)
        petri_utils.add_arc_from_to(t_2, p_6, net)
        petri_utils.add_arc_from_to(t_2, p_4, net)
        petri_utils.add_arc_from_to(t_4, p_3, net)
        petri_utils.add_arc_from_to(t_4, p_5, net)
        petri_utils.add_arc_from_to(t_5, p_7, net)
        petri_utils.add_arc_from_to(t_7, p_4, net)
        petri_utils.add_arc_from_to(p_3, t_2, net)
        petri_utils.add_arc_from_to(p_3, t_3, net)
        petri_utils.add_arc_from_to(p_5, t_2, net)
        petri_utils.add_arc_from_to(p_5, t_3, net)
        petri_utils.add_arc_from_to(p_5, t_4, net)
        petri_utils.add_arc_from_to(p_7, t_6, net)
        petri_utils.add_arc_from_to(p_8, t_7, net)
        petri_utils.add_arc_from_to(p_8, t_8, net)
        petri_utils.add_arc_from_to(t_3, p_2, net)
        petri_utils.add_arc_from_to(p_6, t_6, net)
        petri_utils.add_arc_from_to(t_6, p_5, net)
        petri_utils.add_arc_from_to(t_8, p_8, net)
        initial_marking = Marking()
        initial_marking[p_1] = 1
        final_marking = Marking()
        final_marking[p_2] = 1
        self.assertFalse(woflan.apply(net, initial_marking, final_marking, parameters={"print_diagnostics": False}))

    def test_mcg(self):
        net = PetriNet("mcg")
        p_1 = PetriNet.Place("p_1")
        p_2 = PetriNet.Place("p_2")
        p_3 = PetriNet.Place("p_3")
        p_4 = PetriNet.Place("p_4")
        p_5 = PetriNet.Place("p_5")
        net.places.add(p_1)
        net.places.add(p_2)
        net.places.add(p_3)
        net.places.add(p_4)
        net.places.add(p_5)
        t_1 = PetriNet.Transition("t_1", "t_1")
        t_2 = PetriNet.Transition("t_2", "t_2")
        t_3 = PetriNet.Transition("t_3", "t_3")
        t_4 = PetriNet.Transition("t_4", "t_4")
        t_5 = PetriNet.Transition("t_5", "t_5")
        t_6 = PetriNet.Transition("t_6", "t_6")
        net.transitions.add(t_1)
        net.transitions.add(t_2)
        net.transitions.add(t_3)
        net.transitions.add(t_4)
        net.transitions.add(t_5)
        net.transitions.add(t_6)
        petri_utils.add_arc_from_to(p_1, t_1, net)
        petri_utils.add_arc_from_to(t_1, p_2, net)
        petri_utils.add_arc_from_to(p_2, t_3, net)
        petri_utils.add_arc_from_to(t_3, p_3, net, weight=2)
        petri_utils.add_arc_from_to(p_3, t_4, net)
        petri_utils.add_arc_from_to(t_4, p_2, net)
        petri_utils.add_arc_from_to(p_1, t_2, net)
        petri_utils.add_arc_from_to(t_2, p_4, net)
        petri_utils.add_arc_from_to(p_4, t_5, net)
        petri_utils.add_arc_from_to(t_5, p_5, net, weight=2)
        petri_utils.add_arc_from_to(p_5, t_6, net)
        petri_utils.add_arc_from_to(t_6, p_4, net)
        initial_marking = Marking()
        initial_marking[p_1] = 1
        mcg = minimal_coverability_graph.apply(net, initial_marking)

    def test_compute_unbounded_sequences(self):
        tree = nx_utils.DiGraph()
        tree.add_node(0, marking=np.array([0]))
        tree.add_node(1, marking=np.array([0]))
        tree.add_node(2, marking=np.array([np.inf]))
        tree.add_edge(0, 1, transition="good")
        tree.add_edge(0, 2, transition="bad")

        class FakeWoflan:
            def __init__(self):
                self._tree = None

            def get_net(self):
                return None

            def get_initial_marking(self):
                return None

            def get_final_marking(self):
                return None

            def set_restricted_coverability_tree(self, tree):
                self._tree = tree

            def get_restricted_coverability_tree(self):
                return self._tree

        with mock.patch.object(
            woflan, "restricted_coverability_tree", return_value=tree
        ), mock.patch.object(
            woflan, "convert_marking", return_value=np.array([1])
        ):
            sequences = woflan.compute_unbounded_sequences(FakeWoflan())

        self.assertEqual([["bad"]], sequences)


if __name__ == '__main__':
    unittest.main()
