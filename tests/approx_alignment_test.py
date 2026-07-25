import unittest

from pm4py.algo.conformance.alignments.edit_distance import (
    algorithm as edit_distance_alignments,
)
from pm4py.algo.conformance.alignments.petri_net import (
    algorithm as petri_alignments,
)
from pm4py.objects.log.obj import Event, EventLog, Trace
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import petri_utils
from pm4py.streaming.algo.conformance.alignments import (
    algorithm as streaming_alignments,
)
from pm4py.util.lp import solver as lp_solver


def sequence_net(labels):
    net = PetriNet("sequence")
    places = [PetriNet.Place("p%d" % index) for index in range(len(labels) + 1)]
    net.places.update(places)
    for index, label in enumerate(labels):
        transition = PetriNet.Transition("t_%s" % label, label)
        net.transitions.add(transition)
        petri_utils.add_arc_from_to(places[index], transition, net)
        petri_utils.add_arc_from_to(transition, places[index + 1], net)
    return net, Marking({places[0]: 1}), Marking({places[-1]: 1})


def loop_net():
    net = PetriNet("loop")
    start = PetriNet.Place("start")
    middle = PetriNet.Place("middle")
    final = PetriNet.Place("final")
    net.places.update({start, middle, final})
    transition_a = PetriNet.Transition("t_a", "A")
    transition_b = PetriNet.Transition("t_b", "B")
    transition_c = PetriNet.Transition("t_c", "C")
    net.transitions.update({transition_a, transition_b, transition_c})
    petri_utils.add_arc_from_to(start, transition_a, net)
    petri_utils.add_arc_from_to(transition_a, middle, net)
    petri_utils.add_arc_from_to(middle, transition_b, net)
    petri_utils.add_arc_from_to(transition_b, start, net)
    petri_utils.add_arc_from_to(start, transition_c, net)
    petri_utils.add_arc_from_to(transition_c, final, net)
    return net, Marking({start: 1}), Marking({final: 1})


def trace(labels, case_id=None):
    result = Trace([Event({"concept:name": label}) for label in labels])
    if case_id is not None:
        result.attributes["concept:name"] = case_id
    return result


class ApproxAlignmentTest(unittest.TestCase):
    def test_tandem_repeat_alignment_expands_to_valid_model_loop(self):
        net, im, fm = loop_net()
        observed = trace(["A", "B"] * 4 + ["C"])
        result = petri_alignments.apply(
            observed,
            net,
            im,
            fm,
            variant=petri_alignments.Variants.APPROX_TANDEM_REPEATS,
            parameters={"enable_best_worst_cost": False},
        )
        self.assertTrue(result["is_valid"])
        self.assertEqual(5, result["reduced_trace_length"])
        self.assertEqual(4, result["removed_events"])
        self.assertGreater(result["model_loop_expansions"], 0)
        self.assertEqual(0, result["standard_cost"])

    def test_sliding_window_keeps_executable_endpoint_markings(self):
        net, im, fm = sequence_net(["A", "B", "C", "D"])
        result = petri_alignments.apply(
            trace(["A", "B", "C", "D"]),
            net,
            im,
            fm,
            variant=petri_alignments.Variants.APPROX_SLIDING_WINDOW,
            parameters={
                "window_size": 2,
                "max_candidates": 2,
                "enable_best_worst_cost": False,
            },
        )
        self.assertTrue(result["is_valid"])
        self.assertEqual(2, result["window_count"])
        self.assertEqual([2, 1], result["retained_candidates"])
        self.assertEqual(0, result["cost"])

    def test_fixed_horizon_returns_complete_alignment(self):
        net, im, fm = sequence_net(["A", "B", "C", "D"])
        result = petri_alignments.apply(
            trace(["A", "B", "C", "D"]),
            net,
            im,
            fm,
            variant=petri_alignments.Variants.APPROX_FIXED_HORIZON,
            parameters={
                "horizon": 2,
                "min_progress": 1,
                "enable_best_worst_cost": False,
            },
        )
        self.assertTrue(result["is_valid"])
        self.assertEqual(0, result["standard_cost"])
        if lp_solver.DEFAULT_LP_SOLVER_VARIANT is not None:
            self.assertGreater(result["lp_solved"], 0)
            self.assertFalse(result["fallback_used"])

    def test_subset_edit_distance_returns_alignment_and_bounds(self):
        net, im, fm = sequence_net(["A", "B", "C"])
        log = EventLog(
            [trace(["A", "B", "C"]), trace(["A", "X", "C"]), trace(["A", "C"])]
        )
        results = edit_distance_alignments.apply_approximation(
            log,
            net,
            im,
            fm,
            parameters={"subset_size": 1, "selection_method": "frequency"},
        )
        self.assertEqual(3, len(results))
        self.assertTrue(all(result["is_valid"] for result in results))
        self.assertTrue(
            all(
                result["lower_bound_cost"] <= result["upper_bound_cost"]
                for result in results
            )
        )
        self.assertFalse(results[1]["selected_exact"])
        self.assertEqual(20000, results[1]["standard_cost"])
        summary = edit_distance_alignments.apply_approximation_with_summary(
            log,
            net,
            im,
            fm,
            parameters={"subset_size": 1, "selection_method": "frequency"},
        )
        self.assertLessEqual(
            summary["fitness_lower_bound"], summary["log_fitness"]
        )
        self.assertLessEqual(
            summary["log_fitness"], summary["fitness_upper_bound"]
        )

    def test_subset_simulation_mode_constructs_proxy_behavior(self):
        net, im, fm = sequence_net(["A", "B"])
        results = edit_distance_alignments.apply_approximation(
            EventLog([trace(["A", "B"]), trace(["A"])]),
            net,
            im,
            fm,
            parameters={"subset_size": 1, "selection_method": "simulation"},
        )
        self.assertTrue(all(result["is_valid"] for result in results))
        self.assertTrue(all(not result["selected_exact"] for result in results))

    def test_subset_random_and_k_medoids_selection(self):
        net, im, fm = sequence_net(["A", "B", "C"])
        log = EventLog(
            [
                trace(["A", "B", "C"]),
                trace(["A", "X", "C"]),
                trace(["A", "C"]),
            ]
        )
        for method in ["random", "k_medoids"]:
            results = edit_distance_alignments.apply_approximation(
                log,
                net,
                im,
                fm,
                parameters={
                    "subset_size": 2,
                    "selection_method": method,
                    "random_seed": 7,
                },
            )
            self.assertTrue(all(result["is_valid"] for result in results))
            self.assertTrue(
                all(result["selection_method"] == method for result in results)
            )

    def test_iws_emits_prefix_and_complete_alignments(self):
        net, im, fm = sequence_net(["A", "B", "C"])
        proxy_log = EventLog([trace(["A", "B", "C"])])
        online = streaming_alignments.apply(
            net,
            im,
            fm,
            parameters={"proxy_log": proxy_log, "look_ahead": 3},
        )
        for activity in ["A", "X", "C"]:
            online.receive(
                {
                    "case:concept:name": "case-1",
                    "concept:name": activity,
                }
            )
        prefix = online.get()["case-1"]
        complete = online.finish("case-1")
        self.assertTrue(prefix["is_valid"])
        self.assertFalse(prefix["is_complete"])
        self.assertGreater(prefix["active_states"], 1)
        self.assertIn("decay", prefix)
        self.assertTrue(complete["is_valid"])
        self.assertTrue(complete["is_complete"])
        self.assertEqual("iws", complete["approximation_method"])

    def test_variants_are_exposed_from_alignment_packages(self):
        self.assertIn(
            "APPROX_TANDEM_REPEATS",
            petri_alignments.Variants.__members__,
        )
        self.assertIn(
            "APPROX_SLIDING_WINDOW", petri_alignments.Variants.__members__
        )
        self.assertIn(
            "APPROX_FIXED_HORIZON", petri_alignments.Variants.__members__
        )
        self.assertIn(
            "APPROX_SUBSET", edit_distance_alignments.Variants.__members__
        )
        self.assertIn(
            "APPROX_IWS", streaming_alignments.Variants.__members__
        )


if __name__ == "__main__":
    unittest.main()
