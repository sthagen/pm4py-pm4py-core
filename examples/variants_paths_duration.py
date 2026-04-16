import pm4py


def execute_script():
    log: "pandas.DataFrame" = pm4py.read_xes("../tests/input_data/receipt.xes")
    var_paths_durs: "pandas.DataFrame" = pm4py.get_variants_paths_duration(log)
    print(var_paths_durs.columns)

    # gets for each variant the average times (between all the cases of the given variant)
    # between the activities 'Confirmation of receipt' and 'T02 Check confirmation of receipt'
    df1: "pandas.DataFrame" = var_paths_durs[(var_paths_durs["concept:name"] == "Confirmation of receipt") & (var_paths_durs["concept:name_2"] == "T02 Check confirmation of receipt")]
    print(df1[["@@variant_column", "@@flow_time"]])

    # gets the paths which are repeated in some variants, along with the number of variants for which they are repeated
    df2: "pandas.DataFrame" = var_paths_durs[var_paths_durs["@@cumulative_occ_path_column"] == 1]
    print(df2.groupby(["concept:name", "concept:name_2"]).size())


if __name__ == "__main__":
    execute_script()
