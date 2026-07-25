import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from pm4py.algo.conformance.alignments.petri_net.variants import (
    generator_dijkstra_less_memory,
    generator_dijkstra_no_heuristics,
)
from pm4py.algo.transformation.trace_encodings.variants import trace_based
from pm4py.objects.dfg.utils import dfg_utils
from pm4py.objects.log.exporter.xes import exporter as xes_exporter
from pm4py.objects.log.obj import Event, EventLog, Trace
from pm4py.objects.ocel.validation import ocel20_rel_validation
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import petri_utils
from pm4py.streaming.importer.xes import importer as streaming_xes


class CoverageRegressionTest(unittest.TestCase):
    """Regression coverage for utility and streaming implementations."""

    @staticmethod
    def _input_path(*parts):
        return os.path.join(os.path.dirname(__file__), "input_data", *parts)

    @staticmethod
    def _sequence_net():
        net = PetriNet("abc")
        places = [PetriNet.Place(f"p{i}") for i in range(4)]
        transitions = [
            PetriNet.Transition(f"t_{label}", label)
            for label in ("A", "B", "C")
        ]
        net.places.update(places)
        net.transitions.update(transitions)
        for index, transition in enumerate(transitions):
            petri_utils.add_arc_from_to(places[index], transition, net)
            petri_utils.add_arc_from_to(transition, places[index + 1], net)
        return net, Marking({places[0]: 1}), Marking({places[-1]: 1})

    @staticmethod
    def _interval_log():
        base = datetime(2020, 1, 1, tzinfo=timezone.utc)
        log = EventLog()
        for case_index, offset in enumerate((0, 2)):
            trace = Trace(
                attributes={
                    "concept:name": f"case-{case_index}",
                    "customer": "gold" if case_index == 0 else "silver",
                    "amount": float(10 + case_index),
                }
            )
            for event_index, activity in enumerate(("A", "B", "A", "C")):
                start = base + timedelta(minutes=offset + event_index)
                trace.append(
                    Event(
                        {
                            "concept:name": activity,
                            "org:resource": f"r{event_index % 2}",
                            "lifecycle:transition": "complete",
                            "cost": float(event_index + case_index),
                            "start_timestamp": start,
                            "time:timestamp": start + timedelta(minutes=2),
                        }
                    )
                )
            log.append(trace)
        return log

    def test_trace_encoding_all_extra_features(self):
        log = self._interval_log()
        parameters = {
            "str_tr_attr": ["customer"],
            "str_ev_attr": ["concept:name", "org:resource"],
            "num_tr_attr": ["amount"],
            "num_ev_attr": ["cost"],
            "str_evsucc_attr": ["concept:name"],
            "enable_all_extra_features": True,
            "add_case_identifier_column": True,
            "start_timestamp_key": "start_timestamp",
        }
        data, names = trace_based.apply(log, parameters=parameters)

        self.assertEqual(2, len(data))
        self.assertEqual(len(names), len(data[0]))
        self.assertIn("@@caseDuration", names)
        self.assertTrue(any(name.startswith("resource_workload@@") for name in names))
        self.assertTrue(any(name.startswith("@@max_concurrent") for name in names))

        selected = names[:4]
        selected_data, selected_names = trace_based.apply(
            log,
            parameters={
                "str_tr_attr": ["customer"],
                "str_ev_attr": ["concept:name"],
                "num_tr_attr": ["amount"],
                "num_ev_attr": ["cost"],
                "feature_names": selected,
            },
        )
        self.assertEqual(selected, selected_names)
        self.assertEqual(4, len(selected_data[0]))

    def test_dfg_utility_graph_representations(self):
        dfg = {("A", "A"): 1, ("A", "B"): 5, ("B", "C"): 4, ("C", "D"): 3}
        listed = [((source, target), count) for (source, target), count in dfg.items()]
        ingoing = dfg_utils.get_ingoing_edges(dfg)
        outgoing = dfg_utils.get_outgoing_edges(dfg)

        self.assertEqual(ingoing, dfg_utils.get_ingoing_edges(listed))
        self.assertEqual(outgoing, dfg_utils.get_outgoing_edges(listed))
        self.assertEqual(["A"], dfg_utils.infer_start_activities({("A", "B"): 1}))
        self.assertEqual(["D"], dfg_utils.infer_end_activities(dfg))
        self.assertEqual(["A", "B", "C", "D"], dfg_utils.get_activities_from_dfg(dfg))
        self.assertEqual(5, dfg_utils.get_max_activity_count(dfg, "B"))
        self.assertEqual(6, dfg_utils.max_occ_all_activ(dfg))
        self.assertEqual(5, dfg_utils.max_occ_among_specif_activ(dfg, {"B"}))
        self.assertEqual(0, dfg_utils.sum_start_activities_count(dfg))
        self.assertEqual(3, dfg_utils.sum_end_activities_count(dfg))
        self.assertGreater(dfg_utils.sum_activities_count(dfg, {"A", "B"}), 0)
        self.assertGreater(
            dfg_utils.sum_activities_count(dfg, {"A", "B"}, enable_halving=False),
            0,
        )

        initial = listed + [(("X", "A"), 2), (("X", "Y"), 1), (("D", "Z"), 2), (("W", "Z"), 1)]
        activities = {"A", "B", "C", "D"}
        self.assertIn(
            "A",
            dfg_utils.infer_start_activities_from_prev_connections_and_current_dfg(
                initial, listed, activities
            ),
        )
        self.assertIn(
            "D",
            dfg_utils.infer_end_activities_from_succ_connections_and_current_dfg(
                initial, listed, activities
            ),
        )
        self.assertEqual(
            {"Y"},
            dfg_utils.get_outputs_of_outside_activities_going_to_start_activities(
                initial, listed, activities
            ),
        )
        self.assertEqual(
            {"W"},
            dfg_utils.get_inputs_of_outside_activities_reached_by_end_activities(
                initial, listed, activities
            ),
        )
        self.assertEqual(3, len(dfg_utils.filter_dfg_on_act(listed, {"A", "B", "C"})))
        self.assertTrue(dfg_utils.negate(listed))
        directions = dfg_utils.get_activities_direction(listed, None)
        self.assertEqual(4, len(dfg_utils.get_activities_dirlist(directions)))
        self.assertEqual(["A"], dfg_utils.get_activities_self_loop(listed))

        components = dfg_utils.get_connected_components(
            ingoing, outgoing, {"A", "B", "C", "D", "isolated"}
        )
        self.assertTrue(any("isolated" in component for component in components))
        fixed = dfg_utils.add_to_most_probable_component(
            [{"A"}, {"C"}], "B", ingoing, outgoing
        )
        self.assertTrue(any("B" in component for component in fixed))
        self.assertEqual(
            {"A", "B"},
            dfg_utils.get_all_activities_connected_as_output_to_activity(listed, "A"),
        )
        self.assertEqual(
            {"A"},
            dfg_utils.get_all_activities_connected_as_input_to_activity(listed, "B"),
        )
        matrix, index = dfg_utils.get_dfg_np_matrix(dfg)
        self.assertEqual((4, 4), matrix.shape)
        self.assertEqual(set(range(4)), set(index))

        derived, alphabet, starts, ends = dfg_utils.get_dfg_sa_ea_act_from_variants(
            [("A", "B", "C"), ("A", "D")]
        )
        self.assertTrue(derived)
        self.assertEqual({"A", "B", "C", "D"}, set(alphabet))
        self.assertEqual({"A": 2}, starts)
        self.assertEqual({"C": 1, "D": 1}, ends)
        graph = dfg_utils.transform_dfg_to_directed_nx_graph(listed)
        self.assertEqual(4, len(graph.nodes))
        self.assertIn("D", dfg_utils.get_successors(dfg)["A"])
        self.assertIn("A", dfg_utils.get_predecessors(dfg)["D"])
        pre, post = dfg_utils.get_transitive_relations(dfg, set(alphabet))
        self.assertIn("A", pre["D"])
        self.assertIn("D", post["A"])
        self.assertEqual(set(alphabet), dfg_utils.get_alphabet(dfg))

    def test_generator_alignment_variants(self):
        net, initial_marking, final_marking = self._sequence_net()
        trace = Trace(
            [Event({"concept:name": activity}) for activity in ("A", "X", "C")]
        )

        compact = list(
            generator_dijkstra_less_memory.apply(
                trace,
                net,
                initial_marking,
                final_marking,
                parameters={"ret_tuple_as_trans_desc": True},
            )
        )
        generated = list(
            generator_dijkstra_no_heuristics.apply(
                trace,
                net,
                initial_marking,
                final_marking,
                parameters={"ret_tuple_as_trans_desc": True},
            )
        )
        best_worst = generator_dijkstra_no_heuristics.get_best_worst_cost(
            net, initial_marking, final_marking
        )

        self.assertTrue(compact)
        self.assertGreater(compact[0]["cost"], 0)
        self.assertTrue(generated)
        self.assertGreater(generated[0]["cost"], 0)
        self.assertGreater(best_worst, 0)

    def test_ocel_sqlite_relational_validation(self):
        satisfied, unsatisfied = ocel20_rel_validation.apply(
            self._input_path("ocel", "ocel20_example.sqlite")
        )

        self.assertEqual(24, len(satisfied) + len(unsatisfied))
        self.assertIn("const_1_existence_type_independent_tables", satisfied)

    def test_etree_export_and_streaming_xes_importers(self):
        log = self._interval_log()
        serialized = xes_exporter.serialize(
            log, variant=xes_exporter.Variants.ETREE
        )
        self.assertIn(b"<log", serialized)

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "interval.xes")
            xes_exporter.apply(log, path, variant=xes_exporter.Variants.ETREE)

            event_reader = streaming_xes.apply(
                path,
                variant=streaming_xes.Variants.XES_EVENT_STREAM,
                parameters={"acceptance_condition": lambda event: event.get("concept:name") != "B"},
            )
            events = [event for event in event_reader if event is not None]
            self.assertEqual(6, len(events))
            event_reader.reset()
            appended_events = []
            event_reader.to_event_stream(appended_events)
            self.assertEqual(6, len(appended_events))

            trace_reader = streaming_xes.apply(
                path,
                variant=streaming_xes.Variants.XES_TRACE_STREAM,
                parameters={"acceptance_condition": lambda trace: len(trace) == 4},
            )
            traces = [trace for trace in trace_reader if trace is not None]
            self.assertEqual(2, len(traces))
            trace_reader.reset()
            appended_traces = []
            trace_reader.to_trace_stream(appended_traces)
            self.assertEqual(2, len(appended_traces))


if __name__ == "__main__":
    unittest.main()
