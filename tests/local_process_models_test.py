import os
import unittest

from pm4py import ProcessTree
from pm4py.algo.discovery.local_process_models.algorithm import find_local_process_models
from pm4py.algo.discovery.local_process_models.variants.classic import Parameters
from pm4py.objects.log.importer.xes import importer as xes_importer
from tests.constants import INPUT_DATA_DIR


class LocalProcessModelsTest(unittest.TestCase):
    def test_tree_running_example_log_plain_based(self):
        # to avoid static method warnings in tests,
        # that by construction of the unittest package have to be expressed in such way
        self.dummy_variable = "dummy_value"

        import warnings
        from scipy.optimize import OptimizeWarning

        warnings.filterwarnings("ignore", category=OptimizeWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
        warnings.filterwarnings("ignore", category=RuntimeWarning)

        log = xes_importer.apply(os.path.join(INPUT_DATA_DIR, "running-example.xes"))

        parameters = {Parameters.FREQUENCY_THRESHOLD: 4, Parameters.MAX_ITERATIONS: 2, Parameters.MAX_NUMBER_OF_MODELS: 100}
        local_process_models = find_local_process_models(log,
                                                         selected_activities=None,
                                                         parameters=parameters)

        self.assertEqual(len(local_process_models), 15)
        tree, metrics = local_process_models[0]
        self.assertEqual(tree, ProcessTree(None, None, [], "register request"))
        self.assertEqual(metrics.confidence, 1)
        self.assertEqual(metrics.frequency, 6)

        del log



if __name__ == "__main__":
    unittest.main()
