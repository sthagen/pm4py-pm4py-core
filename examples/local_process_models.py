import os

from pm4py.algo.discovery.local_process_models.algorithm import find_local_process_models
from pm4py.objects.log.importer.xes import importer as xes_import
from pm4py.objects.log.obj import EventLog


def execute_script():
    log_path: str = os.path.join(os.path.join("..", "tests", "input_data", "running-example.xes"))
    log: EventLog = xes_import.apply(log_path)

    lpms = find_local_process_models(log,
                                     selected_activities=None,
                                     parameters = {"max_iterations": 2})

    if len(lpms):
        process_tree, metrics = lpms[0]

        print(process_tree)


if __name__ == "__main__":
    execute_script()
