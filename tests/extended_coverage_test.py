import importlib.util
import os
import unittest

import pandas as pd

import pm4py
from pm4py.algo.clustering.trace_attribute_driven import (
    algorithm as trace_clustering,
)
from pm4py.algo.conformance.alignments.petri_net import (
    algorithm as petri_alignments,
)
from pm4py.algo.discovery.dfg.variants import clean_time
from pm4py.algo.discovery.footprints import algorithm as footprints
from pm4py.algo.clustering.trace_attribute_driven.util import evaluation
from pm4py.objects.conversion.powl import converter as powl_converter
from pm4py.objects.log.obj import Event, EventLog, Trace
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import petri_utils
from pm4py.statistics.process_cube.pandas import algorithm as pandas_cube
from pm4py.streaming.algo.conformance.declare import (
    algorithm as streaming_declare,
)
from pm4py.streaming.algo.conformance.tbr import algorithm as streaming_tbr
from pm4py.visualization.dfg.variants import timeline
from pm4py.visualization.powl import visualizer as powl_visualizer


class ExtendedCoverageTest(unittest.TestCase):
    """Exercise public algorithm variants not reached by the legacy runner."""

    @staticmethod
    def _input_path(*parts):
        return os.path.join(os.path.dirname(__file__), "input_data", *parts)

    @staticmethod
    def _sequence_net(labels=("A", "B", "C"), invisible=False):
        net = PetriNet("sequence")
        places = [
            PetriNet.Place(f"p{index}")
            for index in range(len(labels) + 1 + (1 if invisible else 0))
        ]
        net.places.update(places)
        current = 0
        for index, label in enumerate(labels):
            transition = PetriNet.Transition(f"t_{label}", label)
            net.transitions.add(transition)
            petri_utils.add_arc_from_to(places[current], transition, net)
            current += 1
            petri_utils.add_arc_from_to(transition, places[current], net)
            if invisible and index == 0:
                silent = PetriNet.Transition(f"tau_{index}", None)
                net.transitions.add(silent)
                petri_utils.add_arc_from_to(places[current], silent, net)
                current += 1
                petri_utils.add_arc_from_to(silent, places[current], net)
        return net, Marking({places[0]: 1}), Marking({places[current]: 1})

    @staticmethod
    def _trace(labels):
        return Trace([Event({"concept:name": label}) for label in labels])

    def test_streaming_declare_all_automata(self):
        unary = ("existence", "absence", "exactly_one", "init")
        binary = (
            "responded_existence", "coexistence", "response", "precedence",
            "succession", "altresponse", "altprecedence", "altsuccession",
            "chainresponse", "chainprecedence", "chainsuccession",
            "noncoexistence", "nonsuccession", "nonchainsuccession",
        )
        model = {template: {"A": {}} for template in unary}
        model.update({template: {("A", "B"): {}} for template in binary})
        model["unsupported"] = {("A", "B"): {}}
        monitor = streaming_declare.apply(model)

        for case_id, activities in (("fit", ("A", "B")), ("repeat", ("B", "A", "A"))):
            for index, activity in enumerate(activities):
                monitor.receive(
                    {
                        "case:concept:name": case_id,
                        "concept:name": activity,
                        "time:timestamp": index,
                    }
                )
        monitor.receive({"concept:name": "B"})
        result = monitor.get()

        self.assertEqual(6, result["total_events_processed"])
        self.assertEqual({"fit", "repeat", "undefined_case"}, set(result["cases"]))
        self.assertGreater(result["total_deviations"], 0)
        self.assertEqual(6, len(result["deviations_per_time"]))

    def test_streaming_token_replay_fit_and_deviations(self):
        net, initial_marking, final_marking = self._sequence_net(invisible=True)
        monitor = streaming_tbr.apply(net, initial_marking, final_marking)

        for activity in ("A", "B", "C"):
            monitor.receive(
                {"case:concept:name": "fit", "concept:name": activity}
            )
        self.assertEqual(0, monitor.get_status("fit")["missing"])
        self.assertTrue(monitor.terminate("fit")["is_fit"])

        monitor.receive({"case:concept:name": "bad", "concept:name": "B"})
        monitor.receive({"case:concept:name": "bad", "concept:name": "unknown"})
        monitor.receive({"concept:name": "A"})
        diagnostics = monitor.get()
        self.assertEqual(["bad"], diagnostics["case"].tolist())
        self.assertGreater(monitor.get_status("bad")["missing"], 0)
        self.assertFalse(monitor.terminate("bad")["is_fit"])
        self.assertIsNone(monitor.get_status("missing"))
        monitor.terminate_all()

    def test_petri_alignment_search_variants(self):
        net, initial_marking, final_marking = self._sequence_net()
        trace = self._trace(("A", "X", "C"))
        variants = (
            petri_alignments.Variants.VERSION_DIJKSTRA_LESS_MEMORY,
            petri_alignments.Variants.VERSION_DIJKSTRA_NO_HEURISTICS,
            petri_alignments.Variants.VERSION_DISCOUNTED_A_STAR,
        )
        for variant in variants:
            result = petri_alignments.apply(
                trace,
                net,
                initial_marking,
                final_marking,
                variant=variant,
                parameters={"enable_best_worst_cost": False},
            )
            self.assertTrue(result["alignment"])
            self.assertGreater(result["cost"], 0)

    def test_powl_footprints_conversion_and_visualizers(self):
        net, initial_marking, final_marking = pm4py.read_pnml(
            self._input_path("running-example.pnml")
        )
        model = pm4py.convert_to_powl(net, initial_marking, final_marking)

        model_footprints = footprints.apply(model)
        converted_net, converted_im, converted_fm = powl_converter.apply(model)
        self.assertIn("register request", model_footprints["activities"])
        self.assertTrue(converted_net.transitions)
        self.assertTrue(converted_im)
        self.assertTrue(converted_fm)

        for variant in (
            powl_visualizer.POWLVisualizationVariants.BASIC,
            powl_visualizer.POWLVisualizationVariants.NET,
        ):
            svg = powl_visualizer.apply(
                model,
                variant=variant,
                frequency_tags=False,
                parameters={"format": "svg"},
            )
            self.assertIn("<svg", svg)
            self.assertIn("register request", svg)

    def test_trace_attribute_clustering_variants(self):
        log = EventLog()
        variants = (
            ("north", ("A", "B", "C")),
            ("south", ("A", "C")),
            ("east", ("A", "D", "C")),
            ("west", ("D", "B", "C")),
        )
        for group, activities in variants:
            for repetition in range(2):
                trace = self._trace(activities)
                trace.attributes.update(
                    {"concept:name": f"{group}-{repetition}", "region": group}
                )
                log.append(trace)

        variants = (
            trace_clustering.Variants.VARIANT_DMM_LEVEN,
            trace_clustering.Variants.VARIANT_AVG_LEVEN,
            trace_clustering.Variants.VARIANT_DMM_VEC,
            trace_clustering.Variants.VARIANT_AVG_VEC,
            evaluation.dfg_dis,
        )
        for variant in variants:
            tree, leaves = trace_clustering.apply(
                log,
                "region",
                variant=variant,
                parameters={"show_progress_bar": False},
            )
            self.assertEqual("root", tree["name"])
            self.assertEqual(4, len(leaves))

    def test_pandas_process_cube_dimension_modes(self):
        table = pd.DataFrame(
            {
                "case:concept:name": ["c1", "c2", "c3", "c4"],
                "x": [0.0, 1.0, 2.0, 3.0],
                "y": [10.0, 20.0, 30.0, 40.0],
                "xp_A": [1, 0, 1, 0],
                "xp_B": [0, 1, 0, 1],
                "yp_C": [1, 1, 0, 0],
                "yp_D": [0, 0, 1, 1],
                "value": [1.0, 2.0, 3.0, 4.0],
            }
        )
        parameters = {
            "x_bins": [0, 1.5, 3.1],
            "y_bins": [9, 25, 41],
            "aggregation_function": "sum",
        }
        for x_col, y_col in (("x", "y"), ("x", "yp"), ("xp", "y"), ("xp", "yp")):
            cube, cases = pandas_cube.apply(
                table, x_col, y_col, "value", parameters=parameters
            )
            self.assertFalse(cube.empty)
            self.assertTrue(cases)

        empty, cases = pandas_cube.apply(
            table.assign(xp_A=0, xp_B=0), "xp", "yp", "value"
        )
        self.assertTrue(empty.empty)
        self.assertEqual({}, cases)

    @unittest.skipUnless(
        importlib.util.find_spec("polars"), "polars is not installed"
    )
    def test_polars_process_cube_dimension_modes(self):
        import polars as pl

        from pm4py.statistics.process_cube.polars import algorithm as polars_cube

        table = pl.DataFrame(
            {
                "case:concept:name": ["c1", "c2", "c3", "c4"],
                "x": [0.0, 1.0, 2.0, 3.0],
                "y": [10.0, 20.0, 30.0, 40.0],
                "category": ["one", "two", "one", "two"],
                "xp_A": [1, 0, 1, 0],
                "xp_B": [0, 1, 0, 1],
                "yp_C": [1, 1, 0, 0],
                "yp_D": [0, 0, 1, 1],
                "value": [1.0, 2.0, 3.0, 4.0],
            }
        )
        parameters = {
            "x_bins": [0, 1.5, 3.1],
            "y_bins": [9, 25, 41],
            "aggregation_function": "sum",
        }
        dimensions = (
            ("x", "y"), ("x", "yp"), ("xp", "y"), ("xp", "yp"),
            (("x", "category"), ("y", "yp")),
        )
        for index, (x_col, y_col) in enumerate(dimensions):
            cube, cases = polars_cube.apply(
                table.lazy() if index == 0 else table,
                x_col,
                y_col,
                "value",
                parameters=parameters,
            )
            self.assertFalse(cube.is_empty())
            self.assertTrue(cases)

    def test_timeline_dfg_visualization(self):
        log = pm4py.read_xes(
            self._input_path("running-example.xes"),
            return_legacy_log_object=False,
        )
        dfg, starts, ends = pm4py.discover_dfg(log)
        elapsed = clean_time.apply(log)
        graph = timeline.apply(
            dict(dfg),
            elapsed,
            log=log,
            parameters={
                "format": "svg",
                "start_activities": starts,
                "end_activities": ends,
            },
        )

        self.assertEqual("svg", graph.format)
        self.assertIn("register request", graph.source)
        self.assertIn("@@startnode", graph.source)


if __name__ == "__main__":
    unittest.main()
