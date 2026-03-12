import pm4py
from pm4py.algo.transformation.to_embeddings import algorithm as to_embeddings
from pm4py.util import constants


def execute_script():
    log = pm4py.read_xes("../tests/input_data/running-example.xes")

    log_paid = to_embeddings.keep_top_k_per_similarity(log, "paid cases", 2, parameters={
        constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY: "concept:name"})
    print(log_paid)

    log_rejected = to_embeddings.keep_top_k_per_similarity(log, "rejected cases", 2, parameters={
        constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY: "concept:name"})
    print(log_rejected)


if __name__ == "__main__":
    execute_script()
