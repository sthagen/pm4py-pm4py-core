import pm4py
from pm4py.algo.transformation.to_embeddings import algorithm as to_embeddings
import pandas


def execute_script():
    log: pandas.DataFrame = pm4py.read_xes("../tests/input_data/running-example.xes")
    log = pm4py.format_dataframe(log)

    filt_log_1 = to_embeddings.keep_top_k_per_similarity(log, "pay compensation", k=3,
                                                         variant=to_embeddings.Variants.EVENTS_TRANSFORMERS)
    print(filt_log_1)

    filt_log_2 = to_embeddings.keep_top_k_per_similarity(log, "pay compensation", k=3,
                                                         variant=to_embeddings.Variants.EVENTS_TRANSFORMERS,
                                                         parameters={"keep_cases": True})
    print(filt_log_2)


if __name__ == "__main__":
    execute_script()
