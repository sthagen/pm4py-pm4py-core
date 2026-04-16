import pm4py
import os
import unittest
from pm4py.objects.ocpn.obj import OCPetriNet


class OcelDiscoveryTest(unittest.TestCase):
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
