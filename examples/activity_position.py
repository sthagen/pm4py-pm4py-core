import pandas as pd
import pm4py
import os


def execute_script():
    dataframe = pd.read_csv(os.path.join("..", "tests", "input_data", "receipt.csv"))
    dataframe = pm4py.format_dataframe(dataframe)
    # prints the summary of the positions of two activities
    print(pm4py.get_activity_position_summary(dataframe, "Confirmation of receipt"))
    print(pm4py.get_activity_position_summary(dataframe, "T02 Check confirmation of receipt"))


if __name__ == "__main__":
    execute_script()
