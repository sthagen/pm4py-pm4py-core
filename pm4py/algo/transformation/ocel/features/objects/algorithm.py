'''
    This file is part of PM4Py (More Info: https://pm4py.fit.fraunhofer.de).

    PM4Py is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    PM4Py is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with PM4Py.  If not, see <https://www.gnu.org/licenses/>.
'''
from pm4py.objects.ocel.obj import OCEL
from typing import Optional, Dict, Any, List
from enum import Enum
from pm4py.util import exec_utils
from pm4py.algo.transformation.ocel.features.objects import object_lifecycle_length, object_lifecycle_duration, object_degree_centrality, object_general_descendants_graph, object_general_interaction_graph, object_general_inheritance_graph, object_cobirth_graph, object_codeath_graph, object_lifecycle_activities, object_str_attributes, object_num_attributes, objects_interaction_graph_ot, object_work_in_progress, related_events_features, related_activities_features, obj_con_in_graph_features, object_lifecycle_unq_act


class Parameters(Enum):
    ENABLE_ALL = "enable_all"
    ENABLE_OBJECT_LIFECYCLE_LENGTH = "enable_object_lifecycle_length"
    ENABLE_OBJECT_LIFECYCLE_UNQ_ACT = "enable_object_lifecycle_unq_act"
    ENABLE_OBJECT_LIFECYCLE_DURATION = "enable_object_lifecycle_duration"
    ENABLE_OBJECT_DEGREE_CENTRALITY = "enable_object_degree_centrality"
    ENABLE_OBJECT_GENERAL_INTERACTION_GRAPH = "enable_object_general_interaction_graph"
    ENABLE_OBJECT_GENERAL_DESCENDANTS_GRAPH = "enable_object_general_descendants_graph"
    ENABLE_OBJECT_GENERAL_INHERITANCE_GRAPH = "enable_object_general_inheritance_graph"
    ENABLE_OBJECT_COBIRTH_GRAPH = "enable_object_cobirth_graph"
    ENABLE_OBJECT_CODEATH_GRAPH = "enable_object_codeath_graph"
    ENABLE_OBJECT_LIFECYCLE_ACTIVITIES = "enable_object_lifecycle_activities"
    ENABLE_OBJECT_STR_ATTRIBUTES = "enable_object_str_attributes"
    ENABLE_OBJECT_NUM_ATTRIBUTES = "enable_object_num_attributes"
    ENABLE_OBJECT_INTERACTION_GRAPH_OT = "enable_object_interaction_graph_ot"
    ENABLE_OBJECT_WORK_IN_PROGRESS = "enable_object_work_in_progress"
    ENABLE_RELATED_EVENTS_FEATURES = "enable_related_events_features"
    ENABLE_RELATED_ACTIVITIES_FEATURES = "enable_related_activities_features"
    ENABLE_OBJ_CON_IN_GRAPH_FEATURES = "enable_obj_con_in_graph_features"
    FILTER_PER_TYPE = "filter_per_type"


def apply(ocel: OCEL, parameters: Optional[Dict[Any, Any]] = None):
    """
    Extract a feature table related to the objects of an OCEL

    Parameters
    ------------------
    ocel
        OCEL
    parameters
        Parameters of the algorithm, including:
        - Parameters.ENABLE_ALL => enable the extraction of all the belowmentioned features
        - Parameters.ENABLE_OBJECT_LIFECYCLE_LENGTH => enables the object lifecycle length feature
        - Parameters.ENABLE_OBJECT_LIFECYCLE_DURATION => enables the object lifecycle duration feature
        - Parameters.ENABLE_OBJECT_LIFECYCLE_UNQ_ACT => enables the object lifecycle unique activities feature
        - Parameters.ENABLE_OBJECT_DEGREE_CENTRALITY => enables the object degree centrality feature
        - Parameters.ENABLE_OBJECT_GENERAL_INTERACTION_GRAPH => enables the object general interaction graph feature
        - Parameters.ENABLE_OBJECT_GENERAL_DESCENDANTS_GRAPH => enables the object general descendants graph feature
        - Parameters.ENABLE_OBJECT_GENERAL_INHERITANCE_GRAPH => enables the object general inheritance graph feature
        - Parameters.ENABLE_OBJECT_COBIRTH_GRAPH => enables the object cobirth graph feature
        - Parameters.ENABLE_OBJECT_CODEATH_GRAPH => enables the object codeath graph feature
        - Parameters.ENABLE_OBJECT_LIFECYCLE_ACTIVITIES => enables the features associated to the activities in the
                                                            lifecycle of an object
        - Parameters.ENABLE_OBJECT_STR_ATTRIBUTES => enables the one-hot-encoding of a specified collection of string
                                                    attributes for each object.
        - Parameters.ENABLE_OBJECT_NUM_ATTRIBUTES => enables the extraction of a specified collection of numeric
                                                    attributes for each object.
        - Parameters.ENABLE_OBJECT_INTERACTION_GRAPH_OT => enables the extraction of the number of interacting objects
                                                            per object type.
        - Parameters.FILTER_PER_TYPE => once obtained, filter only the objects that belongs to a specific type
        - Parameters.ENABLE_RELATED_EVENTS_FEATURES => enables the extraction of features for the related events to a
                                                        given object.
        - Parameters.ENABLE_RELATED_ACTIVITIES_FEATURES => enables the extraction of features for the last occurrence
                                                        of an activity in the events related to the object.
        - Parameters.ENABLE_OBJ_CON_IN_GRAPH_FEATURES => enables the extraction of features from the neighboring
                                                        objects.

    Returns
    ------------------
    data
        Values of the features
    feature_names
        Names of the features
    """
    if parameters is None:
        parameters = {}

    enable_all = exec_utils.get_param_value(Parameters.ENABLE_ALL, parameters, True)
    enable_object_lifecycle_length = exec_utils.get_param_value(Parameters.ENABLE_OBJECT_LIFECYCLE_LENGTH, parameters, enable_all)
    enable_object_lifecycle_duration = exec_utils.get_param_value(Parameters.ENABLE_OBJECT_LIFECYCLE_DURATION, parameters, enable_all)
    enable_object_degree_centrality = exec_utils.get_param_value(Parameters.ENABLE_OBJECT_DEGREE_CENTRALITY, parameters, enable_all)
    enable_object_general_interaction_graph = exec_utils.get_param_value(Parameters.ENABLE_OBJECT_GENERAL_INTERACTION_GRAPH, parameters, enable_all)
    enable_object_general_descendants_graph = exec_utils.get_param_value(Parameters.ENABLE_OBJECT_GENERAL_DESCENDANTS_GRAPH, parameters, enable_all)
    enable_object_general_inheritance_graph = exec_utils.get_param_value(Parameters.ENABLE_OBJECT_GENERAL_INHERITANCE_GRAPH, parameters, enable_all)
    enable_object_cobirth_graph = exec_utils.get_param_value(Parameters.ENABLE_OBJECT_COBIRTH_GRAPH, parameters, enable_all)
    enable_object_codeath_graph = exec_utils.get_param_value(Parameters.ENABLE_OBJECT_CODEATH_GRAPH, parameters, enable_all)
    enable_object_lifecycle_activities = exec_utils.get_param_value(Parameters.ENABLE_OBJECT_LIFECYCLE_ACTIVITIES, parameters, enable_all)
    enable_object_str_attributes = exec_utils.get_param_value(Parameters.ENABLE_OBJECT_STR_ATTRIBUTES, parameters, enable_all)
    enable_object_num_attributes = exec_utils.get_param_value(Parameters.ENABLE_OBJECT_NUM_ATTRIBUTES, parameters, enable_all)
    enable_object_interaction_graph_ot = exec_utils.get_param_value(Parameters.ENABLE_OBJECT_INTERACTION_GRAPH_OT, parameters, enable_all)
    enable_work_in_progress = exec_utils.get_param_value(Parameters.ENABLE_OBJECT_WORK_IN_PROGRESS, parameters, enable_all)
    enable_object_lifecycle_unq_act = exec_utils.get_param_value(Parameters.ENABLE_OBJECT_LIFECYCLE_UNQ_ACT, parameters, enable_all)
    enable_related_events_features = exec_utils.get_param_value(Parameters.ENABLE_RELATED_EVENTS_FEATURES, parameters, False)
    enable_related_activities_features = exec_utils.get_param_value(Parameters.ENABLE_RELATED_ACTIVITIES_FEATURES, parameters, False)
    enable_obj_con_in_graph_features = exec_utils.get_param_value(Parameters.ENABLE_OBJ_CON_IN_GRAPH_FEATURES, parameters, False)

    filter_per_type = exec_utils.get_param_value(Parameters.FILTER_PER_TYPE, parameters, None)

    ordered_objects = list(ocel.objects[ocel.object_id_column])

    datas = [[] for x in ordered_objects]
    feature_namess = []

    if enable_object_lifecycle_length:
        data, feature_names = object_lifecycle_length.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_object_lifecycle_duration:
        data, feature_names = object_lifecycle_duration.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_object_degree_centrality:
        data, feature_names = object_degree_centrality.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_object_general_interaction_graph:
        data, feature_names = object_general_interaction_graph.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_object_general_descendants_graph:
        data, feature_names = object_general_descendants_graph.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_object_general_inheritance_graph:
        data, feature_names = object_general_inheritance_graph.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_object_cobirth_graph:
        data, feature_names = object_cobirth_graph.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_object_codeath_graph:
        data, feature_names = object_codeath_graph.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_object_lifecycle_activities:
        data, feature_names = object_lifecycle_activities.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_object_str_attributes:
        data, feature_names = object_str_attributes.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_object_num_attributes:
        data, feature_names = object_num_attributes.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_object_interaction_graph_ot:
        data, feature_names = objects_interaction_graph_ot.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_work_in_progress:
        data, feature_names = object_work_in_progress.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_object_lifecycle_unq_act:
        data, feature_names = object_lifecycle_unq_act.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_related_events_features:
        data, feature_names = related_events_features.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_related_activities_features:
        data, feature_names = related_activities_features.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if enable_obj_con_in_graph_features:
        data, feature_names = obj_con_in_graph_features.apply(ocel, parameters=parameters)
        feature_namess = feature_namess + feature_names
        for i in range(len(data)):
            datas[i] = datas[i] + data[i]

    if filter_per_type is not None:
        object_type = ocel.objects[[ocel.object_id_column, ocel.object_type_column]].to_dict("records")
        object_type = {x[ocel.object_id_column]: x[ocel.object_type_column] for x in object_type}
        idxs = [i for i in range(len(ordered_objects)) if object_type[ordered_objects[i]] == filter_per_type]
        datas = [datas[i] for i in idxs]

    return datas, feature_namess


def transform_features_to_dict_dict(ocel: OCEL, data: List[List[float]], feature_names: List[str], parameters=None):
    """
    Transforms object-based features expressed in the conventional way to a dictionary
    where the key is the object ID, the second key is the feature name and the value is the feature value.

    Parameters
    -----------------
    ocel
        Object-centric event log
    data
        Values of the features
    feature_names
        Names of the features

    Returns
    -----------------
    dict_dict
        Dictionary associating an ID to a dictionary of features
    """
    if parameters is None:
        parameters = {}

    objects = list(ocel.objects[ocel.object_id_column])
    ret = {}
    i = 0
    while i < len(data):
        dct = {}
        j = 0
        while j < len(feature_names):
            dct[feature_names[j]] = data[i][j]
            j = j + 1
        ret[objects[i]] = dct
        i = i + 1

    return ret
