import pm4py
import os
import unittest
import unittest.mock
from pm4py.objects.ocel.obj import OCEL
from pm4py.objects.ocpn.obj import OCPetriNet
from pm4py.util import pandas_utils


class OcelDiscoveryTest(unittest.TestCase):
    def test_discovery_ocdfg_deduplicates_qualified_relations(self):
        ocel = OCEL(
            events=pandas_utils.instantiate_dataframe(
                {
                    "ocel:eid": ["e1", "e2"],
                    "ocel:activity": ["A", "B"],
                    "ocel:timestamp": [
                        "2020-01-01 00:00:00",
                        "2020-01-01 00:01:00",
                    ],
                }
            ),
            objects=pandas_utils.instantiate_dataframe(
                {"ocel:oid": ["o1"], "ocel:type": ["order"]}
            ),
            relations=pandas_utils.instantiate_dataframe(
                {
                    "ocel:eid": ["e1", "e1", "e2"],
                    "ocel:activity": ["A", "A", "B"],
                    "ocel:timestamp": [
                        "2020-01-01 00:00:00",
                        "2020-01-01 00:00:00",
                        "2020-01-01 00:01:00",
                    ],
                    "ocel:oid": ["o1", "o1", "o1"],
                    "ocel:type": ["order", "order", "order"],
                    "ocel:qualifier": ["created", "referenced", "updated"],
                }
            ),
        )

        ocdfg = pm4py.discover_ocdfg(ocel, compute_edges_performance=False)

        self.assertEqual(
            {("e1", "e2")},
            ocdfg["edges"]["event_couples"]["order"][("A", "B")],
        )
        self.assertNotIn(("A", "A"), ocdfg["edges"]["event_couples"]["order"])
        self.assertEqual(
            {("e1", "o1")},
            set(ocdfg["activities_indep"]["total_objects"]["A"]),
        )

    def test_discovery_ocdfg_forwards_discovery_parameters(self):
        from pm4py.statistics.ocel import edge_metrics

        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))

        with unittest.mock.patch.object(
            edge_metrics,
            "find_associations_per_edge",
            wraps=edge_metrics.find_associations_per_edge,
        ) as find_edges:
            ocdfg = pm4py.discover_ocdfg(
                ocel,
                event_id="ocel:eid",
                event_activity="ocel:activity",
                event_timestamp="ocel:timestamp",
                object_id="ocel:oid",
                object_type="ocel:type",
                compute_edges_performance=False,
            )

        parameters = find_edges.call_args.kwargs["parameters"]
        self.assertEqual("ocel:eid", parameters["param:event:id"])
        self.assertEqual("ocel:activity", parameters["param:event:activity"])
        self.assertEqual("ocel:timestamp", parameters["param:event:timestamp"])
        self.assertEqual("ocel:oid", parameters["param:object:id"])
        self.assertEqual("ocel:type", parameters["param:object:type"])
        self.assertEqual({"event_couples": {}, "total_objects": {}}, ocdfg["edges_performance"])

    def test_discovery_ocfg_f1(self):
        target_path = os.path.join("test_output_data", "model.svg")
        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))
        ocdfg = pm4py.discover_ocdfg(ocel)
        pm4py.save_vis_ocdfg(ocdfg, target_path, annotation="frequency", act_metric="events", edge_metric="ev_couples", act_threshold=2, edge_threshold=1)
        os.remove(target_path)

    def test_discovery_ocfg_f2(self):
        target_path = os.path.join("test_output_data", "model.svg")
        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))
        ocdfg = pm4py.discover_ocdfg(ocel)
        pm4py.save_vis_ocdfg(ocdfg, target_path, annotation="frequency", act_metric="unique_objects", edge_metric="ev_couples", act_threshold=2, edge_threshold=1)
        os.remove(target_path)

    def test_discovery_ocfg_f3(self):
        target_path = os.path.join("test_output_data", "model.svg")
        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))
        ocdfg = pm4py.discover_ocdfg(ocel)
        pm4py.save_vis_ocdfg(ocdfg, target_path, annotation="frequency", act_metric="total_objects", edge_metric="ev_couples", act_threshold=2, edge_threshold=1)
        os.remove(target_path)


    def test_discovery_ocfg_f4(self):
        target_path = os.path.join("test_output_data", "model.svg")
        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))
        ocdfg = pm4py.discover_ocdfg(ocel)
        pm4py.save_vis_ocdfg(ocdfg, target_path, annotation="frequency", act_metric="unique_objects", edge_metric="unique_objects", act_threshold=2, edge_threshold=1)
        os.remove(target_path)


    def test_discovery_ocfg_f5(self):
        target_path = os.path.join("test_output_data", "model.svg")
        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))
        ocdfg = pm4py.discover_ocdfg(ocel)
        pm4py.save_vis_ocdfg(ocdfg, target_path, annotation="frequency", act_metric="unique_objects", edge_metric="total_objects", act_threshold=2, edge_threshold=1)
        os.remove(target_path)


    def test_discovery_ocfg_p1(self):
        target_path = os.path.join("test_output_data", "model.svg")
        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))
        ocdfg = pm4py.discover_ocdfg(ocel)
        pm4py.save_vis_ocdfg(ocdfg, target_path, annotation="performance", act_metric="events", edge_metric="ev_couples", act_threshold=2, edge_threshold=1)
        os.remove(target_path)

    def test_discovery_ocfg_p2(self):
        target_path = os.path.join("test_output_data", "model.svg")
        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))
        ocdfg = pm4py.discover_ocdfg(ocel)
        pm4py.save_vis_ocdfg(ocdfg, target_path, annotation="performance", act_metric="unique_objects", edge_metric="ev_couples", act_threshold=2, edge_threshold=1)
        os.remove(target_path)

    def test_discovery_ocfg_p3(self):
        target_path = os.path.join("test_output_data", "model.svg")
        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))
        ocdfg = pm4py.discover_ocdfg(ocel)
        pm4py.save_vis_ocdfg(ocdfg, target_path, annotation="performance", act_metric="total_objects", edge_metric="ev_couples", act_threshold=2, edge_threshold=1)
        os.remove(target_path)


    def test_discovery_ocfg_p4(self):
        target_path = os.path.join("test_output_data", "model.svg")
        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))
        ocdfg = pm4py.discover_ocdfg(ocel)
        pm4py.save_vis_ocdfg(ocdfg, target_path, annotation="performance", act_metric="unique_objects", edge_metric="total_objects", act_threshold=2, edge_threshold=1)
        os.remove(target_path)


    def test_discovery_ocfg_p5(self):
        target_path = os.path.join("test_output_data", "model.svg")
        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))
        ocdfg = pm4py.discover_ocdfg(ocel, business_hours=True)
        pm4py.save_vis_ocdfg(ocdfg, target_path, annotation="performance", act_metric="unique_objects", edge_metric="total_objects", act_threshold=2, edge_threshold=1)
        os.remove(target_path)


    def test_discovery_ocfg_p6(self):
        target_path = os.path.join("test_output_data", "model.svg")
        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))
        ocdfg = pm4py.discover_ocdfg(ocel, business_hours=True)
        pm4py.save_vis_ocdfg(ocdfg, target_path, annotation="performance", act_metric="unique_objects", edge_metric="total_objects", act_threshold=2, edge_threshold=1, performance_aggregation="median")
        os.remove(target_path)

    def test_discovery_ocpn_im(self):
        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))
        ocpn = pm4py.discover_oc_petri_net(ocel, inductive_miner_variant="im")
        self.assertIsInstance(ocpn, OCPetriNet)
        self.assertEqual(ocpn["object_types"], ocpn.object_types)
        self.assertTrue(ocpn["activities"])
        self.assertIn("petri_nets", ocpn)
        self.assertEqual(ocpn.get("petri_nets"), ocpn["petri_nets"])

    def test_discovery_ocpn_forwards_inductive_miner_parameters(self):
        from pm4py.algo.discovery.inductive import algorithm as inductive_miner

        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))

        with unittest.mock.patch.object(
            inductive_miner, "apply", wraps=inductive_miner.apply
        ) as miner_apply:
            pm4py.discover_oc_petri_net(
                ocel,
                inductive_miner_variant="im",
                noise_threshold=0.2,
                multi_processing=False,
                disable_fallthroughs=False,
                disable_strict_sequence_cut=False,
            )

        self.assertTrue(miner_apply.call_args_list)
        for call in miner_apply.call_args_list:
            parameters = call.kwargs["parameters"]
            self.assertEqual(0.2, parameters["noise_threshold"])
            self.assertFalse(parameters["multiprocessing"])
            self.assertFalse(parameters["disable_fallthroughs"])
            self.assertFalse(parameters["disable_strict_sequence_cut"])
            self.assertEqual(inductive_miner.Variants.IMf, call.kwargs["variant"])

    def test_discovery_ocpn_imd(self):
        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))
        ocpn = pm4py.discover_oc_petri_net(ocel, inductive_miner_variant="imd")
        self.assertIsInstance(ocpn, OCPetriNet)

    def test_discovery_ocpn_algorithm_variants_return_object(self):
        from pm4py.algo.discovery.ocel.ocpn import algorithm as ocpn_algorithm
        from pm4py.algo.discovery.ocel.ocpn.variants import classic as ocpn_classic

        ocel = pm4py.read_ocel(
            os.path.join("input_data", "ocel", "example_log.jsonocel")
        )

        self.assertIsInstance(ocpn_algorithm.apply(ocel), OCPetriNet)
        self.assertIsInstance(ocpn_classic.apply(ocel), OCPetriNet)

    def test_discovery_ocpn_visualization_accepts_object(self):
        from pm4py.visualization.ocel.ocpn import visualizer as ocpn_visualizer

        ocel = pm4py.read_ocel(
            os.path.join("input_data", "ocel", "example_log.jsonocel")
        )
        ocpn = pm4py.discover_oc_petri_net(ocel)
        gviz = ocpn_visualizer.apply(ocpn)
        self.assertTrue(gviz.source)

    def test_discovery_saw_nets_ocel(self):
        from pm4py.algo.discovery.ocel.saw_nets import algorithm as saw_nets_disc
        ocel = pm4py.read_ocel(os.path.join("input_data", "ocel", "example_log.jsonocel"))
        saw_nets_disc.apply(ocel)


if __name__ == "__main__":
    unittest.main()
