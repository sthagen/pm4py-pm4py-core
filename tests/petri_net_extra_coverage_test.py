import unittest
from collections import Counter
from unittest import mock

import numpy as np

from pm4py.objects.conversion.wf_net.variants import to_bpmn
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net import properties
from pm4py.objects.petri_net.saw_net import convert as saw_convert
from pm4py.objects.petri_net.saw_net.obj import StochasticArcWeightNet
from pm4py.objects.petri_net.saw_net.semantics import (
    GlobalStochasticArcWeightNetSemantics,
    LocalStochasticArcWeightNetSemantics,
)
from pm4py.objects.petri_net.utils import (
    embeddings_similarity,
    networkx_graph,
    obj_marking,
    petri_utils,
    projection,
)


class _Vectors:
    def __getitem__(self, node):
        return np.array([float(len(node)), float(node.startswith("T_"))])


class _EmbeddingModel:
    wv = _Vectors()


class PetriNetExtraCoverageTest(unittest.TestCase):
    @staticmethod
    def _series_net(invisible=False):
        net = PetriNet("series")
        p0, p1, p2 = (PetriNet.Place(x) for x in ("p0", "p1", "p2"))
        a = PetriNet.Transition("a", None if invisible else "A")
        b = PetriNet.Transition("b", "B")
        net.places.update({p0, p1, p2})
        net.transitions.update({a, b})
        for source, target in ((p0, a), (a, p1), (p1, b), (b, p2)):
            petri_utils.add_arc_from_to(source, target, net)
        return net, Marking({p0: 1}), Marking({p2: 1}), (p0, p1, p2), (a, b)

    @staticmethod
    def _saw_net():
        net = StochasticArcWeightNet("saw")
        place = StochasticArcWeightNet.Place("p")
        transition = StochasticArcWeightNet.Transition("t", "T", weight=2.0)
        net.places.add(place)
        net.transitions.add(transition)
        in_arc = petri_utils.add_arc_from_to(
            place,
            transition,
            net,
            weight={1: 0.75, 2: 0.25, 3: 0.0},
            type=properties.STOCHASTIC_ARC,
        )
        out_arc = petri_utils.add_arc_from_to(
            transition,
            place,
            net,
            weight={1: 1.0},
            type=properties.STOCHASTIC_ARC,
        )
        return net, place, transition, in_arc, out_arc

    def test_stochastic_arc_weight_semantics_and_conversion(self):
        net, place, transition, in_arc, out_arc = self._saw_net()
        marking = Marking({place: 2})
        missing_transition = StochasticArcWeightNet.Transition("missing")
        self.assertFalse(GlobalStochasticArcWeightNetSemantics.is_enabled(net, missing_transition, marking))
        self.assertTrue(GlobalStochasticArcWeightNetSemantics.is_enabled(net, transition, marking))
        self.assertFalse(GlobalStochasticArcWeightNetSemantics.is_enabled(net, transition, Counter()))
        bindings = GlobalStochasticArcWeightNetSemantics.all_legal_bindings(net, transition)
        self.assertEqual(2, len(bindings))
        self.assertEqual([], GlobalStochasticArcWeightNetSemantics.all_legal_bindings(net, missing_transition))
        enabled = GlobalStochasticArcWeightNetSemantics.all_enabled_bindings(net, transition, marking)
        self.assertEqual(2, len(enabled))
        self.assertTrue(GlobalStochasticArcWeightNetSemantics.is_enabled_binding(net, transition, enabled[0], marking))
        self.assertFalse(GlobalStochasticArcWeightNetSemantics.is_enabled_binding(net, missing_transition, enabled[0], marking))
        self.assertFalse(
            GlobalStochasticArcWeightNetSemantics.is_enabled_binding(
                net, transition, [(in_arc, 3), (out_arc, 1)], marking
            )
        )
        fired = GlobalStochasticArcWeightNetSemantics.fire(net, enabled[0], marking)
        self.assertGreaterEqual(fired[place], 0)
        self.assertGreater(GlobalStochasticArcWeightNetSemantics.amortized_priority(enabled[0]), 0)
        self.assertGreater(GlobalStochasticArcWeightNetSemantics.probability_of_binding(net, transition, enabled[0], marking), 0)
        self.assertEqual(1.0, GlobalStochasticArcWeightNetSemantics.probability_of_transition(net, transition, marking))
        self.assertEqual(0.0, GlobalStochasticArcWeightNetSemantics.probability_of_transition(net, missing_transition, marking))
        self.assertEqual(transition, GlobalStochasticArcWeightNetSemantics.sample_enabled_transition(net, marking, seed=1)[0])
        self.assertIsNone(GlobalStochasticArcWeightNetSemantics.sample_enabled_transition(net, Counter(), seed=1))
        self.assertAlmostEqual(
            1.0,
            LocalStochasticArcWeightNetSemantics.probability_of_binding(
                net, transition, enabled[0], marking
            )
            + LocalStochasticArcWeightNetSemantics.probability_of_binding(
                net, transition, enabled[1], marking
            ),
        )

        stochastic, place_map = saw_convert.convert_saw_net_to_stochastic_net_global_semantics(net)
        self.assertEqual(2, len(stochastic.transitions))
        self.assertIn(place, place_map)
        # The converter deliberately receives a self-loop result here so its
        # finite-state expansion terminates on this cyclic fixture.
        with mock.patch.object(saw_convert.sawsem_local, "fire", return_value=marking):
            local, local_marking = saw_convert.convert_saw_net_to_stochastic_net_local_semantics(net, marking)
        self.assertTrue(local.transitions)
        self.assertEqual(2, sum(local_marking.values()))

    def test_object_marking_accessor_operations(self):
        marking = obj_marking.ObjMarking({"p": {"a", "b", "c"}})
        self.assertTrue(marking["p"] >= 3)
        self.assertTrue(marking["p"] > 2)
        self.assertFalse(marking["p"] < 3)
        self.assertTrue(marking["p"] <= 3)
        self.assertTrue(marking["p"] == 3)
        self.assertIn("a", str(marking["p"]))
        remaining = marking["p"] - {"a"}
        self.assertEqual(2, len(remaining))
        with mock.patch.object(
            obj_marking.random, "sample", side_effect=lambda population, count: list(population)[:count]
        ):
            picked_remaining = marking["p"] - 1
            restored = marking["new"] + 1
        self.assertEqual(2, len(picked_remaining))
        self.assertEqual(1, len(restored))
        union = marking["new"] + {"z"}
        self.assertIn("z", union)
        marking.update({"other": {"x"}})
        self.assertEqual({"x"}, marking.__getitem_original__("other"))
        self.assertEqual({}, marking.__getitem_original__("absent"))

    def test_projection_and_networkx_helpers(self):
        net, _, _, places, transitions = self._series_net()
        projected, projected_im, projected_fm = projection.project_net_on_place(places[1])
        self.assertEqual(2, len(projected.transitions))
        self.assertFalse(projected_im)
        self.assertFalse(projected_fm)
        matrix = projection.project_net_on_matrix(net, ["A", "B"])
        self.assertEqual((2, 1), matrix.shape)
        with self.assertRaises(Exception):
            projection.project_net_on_place(places[0])
        invisible_net, _, _, invisible_places, _ = self._series_net(invisible=True)
        with self.assertRaises(Exception):
            projection.project_net_on_place(invisible_places[1])
        with self.assertRaises(Exception):
            projection.project_net_on_matrix(invisible_net, ["A", "B"])

        graph, source, sink, inverse = networkx_graph.create_networkx_undirected_graph(net, places[0], places[2])
        self.assertEqual(5, len(graph))
        self.assertIs(places[0], inverse[source])
        self.assertIs(places[2], inverse[sink])
        directed, inverse_directed = networkx_graph.create_networkx_directed_graph(net)
        self.assertEqual(4, len(directed.edges))
        weighted, direct, inverse_weighted = networkx_graph.create_networkx_directed_graph_ret_dict_both_ways(
            net, weight={transitions[0]: 2, transitions[1]: 3}
        )
        self.assertEqual(4, len(weighted.edges))
        self.assertEqual(set(direct), set(inverse_weighted.values()))

    def test_embedding_helpers_without_optional_training_dependency(self):
        net, _, _, _, _ = self._series_net()
        graph = embeddings_similarity._petri_to_nx(net)
        walk = embeddings_similarity._random_walk(graph, next(iter(graph)), 5)
        self.assertGreaterEqual(len(walk), 2)
        walks = embeddings_similarity._generate_walks(graph, num_walks=2, walk_length=3, seed=4)
        self.assertEqual(2 * len(graph), len(walks))
        model = _EmbeddingModel()
        for mode in ("mean", "sum", "max"):
            self.assertEqual((2,), embeddings_similarity._readout(model, graph, mode=mode).shape)
        self.assertEqual((2,), embeddings_similarity._readout(model, graph, transition_only=True).shape)
        self.assertAlmostEqual(1.0, embeddings_similarity.cosine_similarity([1, 2], [1, 2]))
        self.assertEqual(0.0, embeddings_similarity.cosine_similarity([0, 0], [1, 2]))
        with mock.patch.object(embeddings_similarity, "_train_word2vec", return_value=model):
            embedding = embeddings_similarity.petri_net_embedding(net, dimensions=2, num_walks=1, walk_length=2)
            self.assertEqual((2,), embedding.shape)
            self.assertAlmostEqual(1.0, embeddings_similarity.apply(net, net))

    def test_wf_net_to_bpmn_visible_and_silent_transitions(self):
        visible, im, fm, _, _ = self._series_net()
        visible_bpmn = to_bpmn.apply(visible, im, fm)
        self.assertTrue(visible_bpmn.get_nodes())
        invisible, invisible_im, invisible_fm, _, _ = self._series_net(invisible=True)
        invisible_bpmn = to_bpmn.apply(invisible, invisible_im, invisible_fm)
        self.assertTrue(invisible_bpmn.get_flows())


if __name__ == "__main__":
    unittest.main()
