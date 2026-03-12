import pm4py
import os


def execute_script():
    log = pm4py.read_xes(os.path.join("..", "tests", "input_data", "roadtraffic100traces.xes"))

    clusters = pm4py.llm.clustering(log, openai_model="o3-mini")

    for cluster_name, dataframe in clusters:
        print("\n")
        print(cluster_name)
        print(dataframe)


if __name__ == "__main__":
    execute_script()
