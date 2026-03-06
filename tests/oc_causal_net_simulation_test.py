import unittest
from pm4py.objects.oc_causal_net.creation.factory import create_oc_causal_net
from pm4py.objects.oc_causal_net.semantics import OCCausalNetSemantics, OCCausalNetState
from pm4py.algo.simulation.playout.oc_causal_net.variants import extensive as playout_extensive  
from pm4py.algo.simulation.playout.oc_causal_net import algorithm as playout_algorithm

class OCCausalNetSimulationTest(unittest.TestCase):
    
    def test_playout_occn_extensive(self):
        occn = occn_ABC()
        
        parameters = {
            playout_extensive.Parameters.MAX_BINDINGS_PER_ACTIVITY: 3,
            playout_extensive.Parameters.RETURN_SEQUENCES: True,
        }
        
        objects = {
            "order": set()
        }
        valid_sequences_iter, _, _ = playout_extensive.apply(occn, objects, parameters)
        valid_sequences = list(valid_sequences_iter)
        self.assertEqual(len(valid_sequences), 1)
    
        objects = {
            "order": {"o1"}
        }
        valid_sequences_iter, _, _ = playout_extensive.apply(occn, objects, parameters)
        valid_sequences = list(valid_sequences_iter)
        self.assertEqual(len(valid_sequences), 1)
        
        objects = {
            "order": {"o1", "o2"}
        }
        valid_sequences_iter, _, _ = playout_extensive.apply(occn, objects, parameters)
        valid_sequences = list(valid_sequences_iter)
        self.assertEqual(len(valid_sequences), 252)
    
    def test_playout_occn_extensive_bf_limited(self):
        occn = occn_ABC()
        
        parameters = {
            playout_extensive.Parameters.MAX_BINDINGS_PER_ACTIVITY: 3,
            playout_extensive.Parameters.RETURN_SEQUENCES: True,
        }
        objects = {
            "order": {"o1", "o2"}
        }
        valid_sequences_iter, _, _ = playout_extensive.apply(occn, objects, parameters)
        valid_sequences = list(valid_sequences_iter)
        self.assertEqual(len(valid_sequences), 252)
        
        parameters = {
            playout_extensive.Parameters.MAX_BINDINGS_PER_ACTIVITY: 3,
            playout_extensive.Parameters.RETURN_SEQUENCES: True,
            playout_extensive.Parameters.BRANCHING_FACTOR_ACTIVITIES: 1.5,
            playout_extensive.Parameters.BRANCHING_FACTOR_BINDINGS: 1.5,
        }
        for _ in range (10):
            valid_sequences_iter_sub, _, _ = playout_extensive.apply(occn, objects, parameters)
            valid_sequences_sub = list(valid_sequences_iter_sub)
            for seq in valid_sequences_sub:
                self.assertTrue(seq in valid_sequences)

    def test_playout_occn_algorithm_dispatch(self):
        occn = occn_ABC()
        parameters = {
            playout_extensive.Parameters.MAX_BINDINGS_PER_ACTIVITY: 3,
            playout_extensive.Parameters.RETURN_SEQUENCES: True,
        }
        objects = {"order": {"o1"}}

        valid_sequences_iter, _, _ = playout_algorithm.apply(
            occn, objects, parameters=parameters
        )
        valid_sequences = list(valid_sequences_iter)
        self.assertEqual(len(valid_sequences), 1)
    
def occn_ABC():
    marker_groups = {
        "START_order": {
            "img": [],
            "omg": [
                [("a", "order", (1, 1), 0)],
            ],
        },
        "a": {
            "img": [
                [("START_order", "order", (1, 1), 0)],
            ],
            "omg": [
                [("b", "order", (1, 1), 0)],
            ],
        },
        "b": {
            "img": [
                [("a", "order", (1, 1), 0)],
            ],
            "omg": [
                [("c", "order", (1, 1), 0)],
            ],
        },
        "c": {
            "img": [
                [("b", "order", (1, 1), 0)],
            ],
            "omg": [
                [("END_order", "order", (1, 1), 0)],
            ],
        },
        "END_order": {
            "img": [
                [("c", "order", (1, 1), 0)],
            ]
        },
    }

    occn = create_oc_causal_net(marker_groups)
    return occn
    
if __name__ == "__main__":
    unittest.main()
