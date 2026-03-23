'''
    PM4Py – A Process Mining Library for Python
Copyright (C) 2024 Process Intelligence Solutions UG (haftungsbeschränkt)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see this software project's root or
visit <https://www.gnu.org/licenses/>.

Website: https://processintelligence.solutions
Contact: info@processintelligence.solutions
'''
from pm4py.util.constants import CASE_CONCEPT_NAME
from pm4py.algo.filtering.common.timestamp.timestamp_common import (
    get_dt_from_string,
)
from pm4py.util.xes_constants import DEFAULT_TIMESTAMP_KEY
from pm4py.util.constants import (
    PARAMETER_CONSTANT_TIMESTAMP_KEY,
    PARAMETER_CONSTANT_CASEID_KEY,
)
from enum import Enum
from pm4py.util import exec_utils, pandas_utils, constants
from copy import copy
from typing import Optional, Dict, Any, Union
import pandas as pd
import datetime


class Parameters(Enum):
    TIMESTAMP_KEY = PARAMETER_CONSTANT_TIMESTAMP_KEY
    CASE_ID_KEY = PARAMETER_CONSTANT_CASEID_KEY
    KEEP_NAN_VALUES = "keep_nan_values"


def filter_traces_contained(
    df: pd.DataFrame,
    dt1: Union[str, datetime.datetime],
    dt2: Union[str, datetime.datetime],
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> pd.DataFrame:
    """
    Get traces that are contained in the given interval

    Parameters
    ----------
    df
        Pandas dataframe
    dt1
        Lower bound to the interval (possibly expressed as string, but automatically converted)
    dt2
        Upper bound to the interval (possibly expressed as string, but automatically converted)
    parameters
        Possible parameters of the algorithm, including:
            Parameters.TIMESTAMP_KEY -> Attribute to use as timestamp
            Parameters.CASE_ID_KEY -> Column that contains the timestamp
            Parameters.KEEP_NAN_VALUES -> If true, keeps traces which do not contain any event with temporal data for the selected attribute. Default is false


    Returns
    ----------
    df
        Filtered dataframe
    """
    if parameters is None:
        parameters = {}
    timestamp_key = exec_utils.get_param_value(
        Parameters.TIMESTAMP_KEY, parameters, DEFAULT_TIMESTAMP_KEY
    )
    case_id_glue = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, CASE_CONCEPT_NAME
    )
    keep_nan_values = exec_utils.get_param_value(
        Parameters.KEEP_NAN_VALUES, parameters, False
    )

    dt1 = get_dt_from_string(dt1)
    dt2 = get_dt_from_string(dt2)

    agg_df = df.groupby(case_id_glue)[timestamp_key].agg(['min', 'max'])

    containment_mask = (agg_df['min'].ge(dt1) & agg_df['max'].le(dt2))

    if keep_nan_values:
        mask = containment_mask | agg_df['min'].isna() # if min is NaN, max is also NaN
    else:
        mask = containment_mask

    case_ids = agg_df.index[mask]

    ret = df[df[case_id_glue].isin(case_ids)].copy()

    if hasattr(df, "attrs"):
        ret.attrs = copy(df.attrs)

    return ret


def filter_traces_intersecting(
    df: pd.DataFrame,
    dt1: Union[str, datetime.datetime],
    dt2: Union[str, datetime.datetime],
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> pd.DataFrame:
    """
    Filter traces intersecting the given interval

    Parameters
    ----------
    df
        Pandas dataframe
    dt1
        Lower bound to the interval (possibly expressed as string, but automatically converted)
    dt2
        Upper bound to the interval (possibly expressed as string, but automatically converted)
    parameters
        Possible parameters of the algorithm, including:
            Parameters.TIMESTAMP_KEY -> Attribute to use as timestamp
            Parameters.CASE_ID_KEY -> Column that contains the timestamp
            Parameters.KEEP_NAN_VALUES -> If true, keeps traces which do not contain any event with data for the selected timestamp attribute. Default is false

    Returns
    ----------
    df
        Filtered dataframe
    """
    if parameters is None:
        parameters = {}

    timestamp_key = exec_utils.get_param_value(
        Parameters.TIMESTAMP_KEY, parameters, DEFAULT_TIMESTAMP_KEY
    )
    case_id_glue = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, CASE_CONCEPT_NAME
    )
    keep_nan_values = exec_utils.get_param_value(
        Parameters.KEEP_NAN_VALUES, parameters, False
    )

    dt1 = get_dt_from_string(dt1)
    dt2 = get_dt_from_string(dt2)

    agg_df = df.groupby(case_id_glue)[timestamp_key].agg(['min', 'max'])

    intersect_mask = (agg_df['min'].lt(dt2)) & (agg_df['max'].gt(dt1))

    if keep_nan_values:
        mask = intersect_mask | agg_df['min'].isna()
    else:
        mask = intersect_mask

    valid_cases = agg_df.index[mask]
    ret = df[df[case_id_glue].isin(valid_cases)].copy()

    if hasattr(df, "attrs"):
        ret.attrs = copy(df.attrs)

    return ret


def apply_events(
    df: pd.DataFrame,
    dt1: Union[str, datetime.datetime],
    dt2: Union[str, datetime.datetime],
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> pd.DataFrame:
    """
    Get a new log containing all the events contained in the given interval

    Parameters
    ----------
    df
        Pandas dataframe
    dt1
        Lower bound to the interval (possibly expressed as string, but automatically converted)
    dt2
        Upper bound to the interval (possibly expressed as string, but automatically converted)
    parameters
        Possible parameters of the algorithm, including:
            Parameters.TIMESTAMP_KEY -> Attribute to use as timestamp
            Parameters.KEEP_NAN_VALUES -> If true, keeps events which do not contain temporal data for the selected attribute. Default is false

    Returns
    ----------
    df
        Filtered dataframe
    """
    if parameters is None:
        parameters = {}

    timestamp_key = exec_utils.get_param_value(
        Parameters.TIMESTAMP_KEY, parameters, DEFAULT_TIMESTAMP_KEY
    )
    keep_nan_values = exec_utils.get_param_value(
        Parameters.KEEP_NAN_VALUES, parameters, False
    )
    dt1 = get_dt_from_string(dt1)
    dt2 = get_dt_from_string(dt2)

    containment_mask = (df[timestamp_key].ge(dt1) & df[timestamp_key].le(dt2))

    if keep_nan_values:
        mask = containment_mask | df[timestamp_key].isna()
    else:
        mask = containment_mask

    ret = df[mask]

    ret.attrs = copy(df.attrs) if hasattr(df, "attrs") else {}
    return ret


def filter_traces_attribute_in_timeframe(
    df: pd.DataFrame,
    attribute: str,
    attribute_value: str,
    dt1: Union[str, datetime.datetime],
    dt2: Union[str, datetime.datetime],
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> pd.DataFrame:
    """
    Get a new log containing all the traces that have an event in the given interval with the specified attribute value

    Parameters
    -----------
    df
        Dataframe
    attribute
        The attribute to filter on
    attribute_value
        The attribute value to filter on
    dt1
        Lower bound to the interval
    dt2
        Upper bound to the interval
    parameters
        Possible parameters of the algorithm, including:
            Parameters.TIMESTAMP_KEY -> Attribute to use as timestamp
            Parameters.KEEP_NAN_VALUES -> If true, keeps traces which do not contain any event with temporal data for the selected attribute. Default is false

    Returns
    ------------
    df
        Filtered dataframe
    """

    if parameters is None:
        parameters = {}
    timestamp_key = exec_utils.get_param_value(
        Parameters.TIMESTAMP_KEY, parameters, DEFAULT_TIMESTAMP_KEY
    )
    case_id_glue = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, CASE_CONCEPT_NAME
    )
    keep_nan_values = exec_utils.get_param_value(
        Parameters.KEEP_NAN_VALUES, parameters, False
    )

    dt1 = get_dt_from_string(dt1)
    dt2 = get_dt_from_string(dt2)

    attribute_filtered = df[df[attribute] == attribute_value]

    containment_mask = attribute_filtered[timestamp_key].ge(dt1) & attribute_filtered[timestamp_key].le(dt2)

    if keep_nan_values:
        mask = containment_mask | attribute_filtered[timestamp_key].isna()
    else:
        mask = containment_mask

    case_ids = attribute_filtered.loc[mask, case_id_glue].unique()

    ret = df[df[case_id_glue].isin(case_ids)].copy()

    ret.attrs = copy(df.attrs) if hasattr(df, "attrs") else {}
    return ret


def filter_traces_starting_in_timeframe(
    df: pd.DataFrame,
    dt1: Union[str, datetime.datetime],
    dt2: Union[str, datetime.datetime],
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> pd.DataFrame:
    """
    Keep/Exclude traces whose *first event* timestamp falls in [dt1, dt2].

    Parameters
    ----------
    df
        Pandas dataframe
    dt1
        Lower bound to the interval (string or datetime)
    dt2
        Upper bound to the interval (string or datetime)
    parameters
        Possible parameters of the algorithm, including:
            Parameters.TIMESTAMP_KEY -> Attribute to use as timestamp
            Parameters.CASE_ID_KEY -> Column that contains the case id
            "positive" (bool, default True) -> keep (True) or exclude (False) the matching cases
            Parameters.KEEP_NAN_VALUES -> If true, keeps traces which do not contain any event with temporal data for the selected attribute. Default is false

    Returns
    ----------
    df
        Filtered dataframe (all events for the selected cases)
    """
    if parameters is None:
        parameters = {}

    timestamp_key = exec_utils.get_param_value(
        Parameters.TIMESTAMP_KEY, parameters, DEFAULT_TIMESTAMP_KEY
    )
    case_id_glue = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, CASE_CONCEPT_NAME
    )
    positive = exec_utils.get_param_value("positive", parameters, True)
    keep_nan_values = exec_utils.get_param_value(
        Parameters.KEEP_NAN_VALUES, parameters, False
    )

    dt1 = get_dt_from_string(dt1)
    dt2 = get_dt_from_string(dt2)

    agg_df = df.groupby(case_id_glue)[timestamp_key].min().to_frame()

    in_range = agg_df[timestamp_key].ge(dt1) & agg_df[timestamp_key].le(dt2)

    if keep_nan_values:
        mask = in_range | agg_df[timestamp_key].isna()
    else:
        mask = in_range

    case_ids = agg_df.loc[mask].index

    if positive:
        ret = df[df[case_id_glue].isin(case_ids)].copy()
    else:
        ret = df[~df[case_id_glue].isin(case_ids)].copy()

    ret.attrs = copy(df.attrs) if hasattr(df, "attrs") else {}
    return ret


def filter_traces_completing_in_timeframe(
    df: pd.DataFrame,
    dt1: Union[str, datetime.datetime],
    dt2: Union[str, datetime.datetime],
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> pd.DataFrame:
    """
    Keep/Exclude traces whose *last event* timestamp falls in [dt1, dt2].

    Parameters
    ----------
    df
        Pandas dataframe
    dt1
        Lower bound to the interval (string or datetime)
    dt2
        Upper bound to the interval (string or datetime)
    parameters
        Possible parameters of the algorithm, including:
            Parameters.TIMESTAMP_KEY -> Attribute to use as timestamp
            Parameters.CASE_ID_KEY -> Column that contains the case id
            "positive" (bool, default True) -> keep (True) or exclude (False) the matching cases
            Parameters.KEEP_NAN_VALUES -> If true, keeps traces which do not contain any event with temporal data for the selected attribute. Default is false

    Returns
    ----------
    df
        Filtered dataframe (all events for the selected cases)
    """
    if parameters is None:
        parameters = {}

    timestamp_key = exec_utils.get_param_value(
        Parameters.TIMESTAMP_KEY, parameters, DEFAULT_TIMESTAMP_KEY
    )
    case_id_glue = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, CASE_CONCEPT_NAME
    )
    positive = exec_utils.get_param_value("positive", parameters, True)
    keep_nan_values = exec_utils.get_param_value(
        Parameters.KEEP_NAN_VALUES, parameters, False
    )

    dt1 = get_dt_from_string(dt1)
    dt2 = get_dt_from_string(dt2)

    agg_df = df.groupby(case_id_glue)[timestamp_key].max().to_frame()

    in_range = agg_df[timestamp_key].ge(dt1) & agg_df[timestamp_key].le(dt2)

    if keep_nan_values:
        mask = in_range | agg_df[timestamp_key].isna()
    else:
        mask = in_range

    case_ids = agg_df.loc[mask].index

    if positive:
        ret = df[df[case_id_glue].isin(case_ids)].copy()
    else:
        ret = df[~df[case_id_glue].isin(case_ids)].copy()

    ret.attrs = copy(df.attrs) if hasattr(df, "attrs") else {}
    return ret


def apply(df, parameters=None):
    del df
    del parameters
    raise Exception("apply method not available for timestamp filter")


def apply_auto_filter(df, parameters=None):
    del df
    del parameters
    raise Exception(
        "apply_auto_filter method not available for timestamp filter"
    )
