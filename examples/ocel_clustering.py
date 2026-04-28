import pm4py
from pm4py.algo.transformation.ocel.split_ocel import algorithm as ocel_splitter
from pm4py.objects.ocel.obj import OCEL
from typing import Collection


def execute_script():
    ocel: OCEL = pm4py.read_ocel("../tests/input_data/ocel/example_log.jsonocel")
    object_type: str = "order"
    #ocel = pm4py.read_ocel("../tests/input_data/ocel/recruiting-red.jsonocel")
    #object_type = "applications"
    # obtains an OCEL for every application, containing the events of the application and of the connected
    # objects (offers)
    lst_ocels = ocel_splitter.apply(ocel, variant=ocel_splitter.Variants.ANCESTORS_DESCENDANTS, parameters={"object_type": object_type})
    # alternatively, performs a clustering grouping by sub-OCELs following the same patterns (lifecycle activities and connection with offers)
    ocel_clusters: dict[str, Collection[OCEL]] = pm4py.cluster_equivalent_ocel(ocel, object_type)
    print(sorted([len(y) for x, y in ocel_clusters.items()]))


if __name__ == "__main__":
    execute_script()
