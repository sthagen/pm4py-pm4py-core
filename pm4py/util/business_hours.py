'''
PM4Py – A Process Mining Library for Python
Copyright (C) 2026 Process Intelligence Solutions GmbH

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
from datetime import date, datetime
from functools import lru_cache
from typing import List, Tuple

from pm4py.util import constants


_SECONDS_PER_DAY = 24 * 60 * 60


@lru_cache(maxsize=512)
def _prepare_business_hour_slots(business_hour_slots):
    """Normalize and precompute values for a weekly business schedule."""
    unified = []
    for begin, end in sorted(business_hour_slots):
        if unified and unified[-1][1] >= begin - 1:
            unified[-1][1] = max(unified[-1][1], end)
        else:
            unified.append([begin, end])

    slots = tuple((begin, end) for begin, end in unified)
    total_seconds = sum(end - start for start, end in slots)
    return slots, total_seconds


def _get_prepared_business_hour_slots(business_hour_slots):
    # Schedules are commonly passed as lists, so convert them to an immutable
    # value before looking them up in the cache. This also makes later changes
    # to a caller-owned list visible on the next calculation.
    slots = tuple((begin, end) for begin, end in business_hour_slots)
    return _prepare_business_hour_slots(slots)


def _seconds_from_week_start(dt):
    """Return wall-clock seconds since Monday 00:00 without temporaries."""
    return (
        dt.weekday() * _SECONDS_PER_DAY
        + dt.hour * 60 * 60
        + dt.minute * 60
        + dt.second
        + dt.microsecond / 1000000
    )


def _seconds_from_day_start(dt):
    """Return wall-clock seconds since 00:00 without temporaries."""
    return (
        dt.hour * 60 * 60
        + dt.minute * 60
        + dt.second
        + dt.microsecond / 1000000
    )


def _business_seconds_from_week_start(dt, business_hour_slots):
    seconds_since_week_start = _seconds_from_week_start(dt)
    total = 0.0
    for start, end in business_hour_slots:
        if seconds_since_week_start <= start:
            break
        total += max(0, min(seconds_since_week_start, end) - start)
    return total


def _get_business_seconds(
    datetime1,
    datetime2,
    business_hour_slots,
    total_seconds_per_week,
    work_calendar=None,
):
    if datetime2 <= datetime1:
        return 0.0

    # Subtracting the weekday from the ordinal gives the Monday ordinal for
    # each timestamp, avoiding date, datetime, and timedelta allocations.
    week_start1 = datetime1.toordinal() - datetime1.weekday()
    week_start2 = datetime2.toordinal() - datetime2.weekday()
    number_of_weeks = (week_start2 - week_start1) // 7

    seconds1 = _business_seconds_from_week_start(
        datetime1, business_hour_slots
    )
    seconds2 = _business_seconds_from_week_start(
        datetime2, business_hour_slots
    )
    total = (
        total_seconds_per_week * number_of_weeks + seconds2 - seconds1
    )
    if work_calendar is None or total == 0:
        return total

    return total - _get_non_working_seconds(
        datetime1, datetime2, business_hour_slots, work_calendar
    )


@lru_cache(maxsize=512)
def _split_business_hour_slots_by_weekday(business_hour_slots):
    """Split weekly slots into per-day wall-clock intervals."""
    daily_slots = [[] for _ in range(7)]
    for start, end in business_hour_slots:
        for weekday in range(7):
            day_start = weekday * _SECONDS_PER_DAY
            slot_start = max(start, day_start)
            slot_end = min(end, day_start + _SECONDS_PER_DAY)
            if slot_end > slot_start:
                daily_slots[weekday].append(
                    (slot_start - day_start, slot_end - day_start)
                )
    return tuple(tuple(slots) for slots in daily_slots)


@lru_cache(maxsize=512)
def _get_business_day_seconds(slots) -> float:
    daily_slots = _split_business_hour_slots_by_weekday(slots)
    daily_seconds = [
        sum(end - start for start, end in slots)
        for slots in daily_slots
        if slots
    ]
    if not daily_seconds:
        return float(_SECONDS_PER_DAY)
    return sum(daily_seconds) / len(daily_seconds)


def get_business_day_seconds(business_hour_slots) -> float:
    """Return the average duration of a configured working day.

    Only weekdays containing at least one business-hour interval contribute
    to the average. Overlapping slots are unified before the duration is
    calculated. An empty schedule falls back to a 24-hour calendar day.
    """
    slots, _ = _get_prepared_business_hour_slots(business_hour_slots)
    return _get_business_day_seconds(slots)


def _get_non_working_seconds(
    datetime1, datetime2, business_hour_slots, work_calendar
):
    """Return scheduled seconds on dates rejected by ``work_calendar``."""
    immutable_slots = tuple(
        (start, end) for start, end in business_hour_slots
    )
    daily_slots = _split_business_hour_slots_by_weekday(immutable_slots)
    start_ordinal = datetime1.toordinal()
    end_ordinal = datetime2.toordinal()
    start_seconds = _seconds_from_day_start(datetime1)
    end_seconds = _seconds_from_day_start(datetime2)
    last_ordinal = end_ordinal if end_seconds > 0 else end_ordinal - 1
    non_working_seconds = 0.0

    weekday = datetime1.weekday()
    for ordinal in range(start_ordinal, last_ordinal + 1):
        slots = daily_slots[weekday]
        if slots and not work_calendar.is_working_day(
            date.fromordinal(ordinal)
        ):
            lower_bound = start_seconds if ordinal == start_ordinal else 0
            upper_bound = (
                end_seconds
                if ordinal == end_ordinal
                else _SECONDS_PER_DAY
            )
            for start, end in slots:
                non_working_seconds += max(
                    0,
                    min(upper_bound, end) - max(lower_bound, start),
                )
        weekday = (weekday + 1) % 7

    return non_working_seconds


class BusinessHours:
    def __init__(self, datetime1, datetime2, **kwargs):
        # Remove timezone info for simplicity (assumes same timezone)
        self.datetime1 = (
            datetime1.replace(tzinfo=None)
            if datetime1.tzinfo is not None
            else datetime1
        )
        self.datetime2 = (
            datetime2.replace(tzinfo=None)
            if datetime2.tzinfo is not None
            else datetime2
        )
        # Use provided business hour slots or default
        self.business_hour_slots = (
            kwargs["business_hour_slots"]
            if "business_hour_slots" in kwargs
            else constants.DEFAULT_BUSINESS_HOUR_SLOTS
        )
        # Unify slots to avoid overlaps
        unified_slots, _ = _get_prepared_business_hour_slots(
            self.business_hour_slots
        )
        # Keep the existing mutable representation of this attribute for
        # compatibility.
        self.business_hour_slots_unified = [
            list(slot) for slot in unified_slots
        ]
        # ``workcalendar`` is the spelling used by the public APIs and older
        # versions; ``work_calendar`` was introduced with weekly slots.
        self.work_calendar = (
            kwargs["work_calendar"]
            if "work_calendar" in kwargs
            else kwargs.get(
                "workcalendar",
                constants.DEFAULT_BUSINESS_HOURS_WORKCALENDAR,
            )
        )

    @property
    def workcalendar(self):
        """Legacy alias for :attr:`work_calendar`."""
        return self.work_calendar

    @workcalendar.setter
    def workcalendar(self, value):
        self.work_calendar = value

    def business_seconds_from_week_start(self, dt):
        """Calculate business seconds from the week start to ``dt``."""
        return _business_seconds_from_week_start(
            dt, self.business_hour_slots_unified
        )

    def get_seconds(self):
        """Calculate total business seconds between datetime1 and datetime2."""
        total_seconds_per_week = sum(
            end - start
            for start, end in self.business_hour_slots_unified
        )
        return _get_business_seconds(
            self.datetime1,
            self.datetime2,
            self.business_hour_slots_unified,
            total_seconds_per_week,
            self.work_calendar,
        )


def soj_time_business_hours_diff(
    st: datetime,
    et: datetime,
    business_hour_slots: List[Tuple[int]],
    work_calendar=constants.DEFAULT_BUSINESS_HOURS_WORKCALENDAR,
) -> float:
    """
    Calculates the difference between the provided timestamps based on business hours.

    Parameters
    ----------
    st : datetime
        Start timestamp
    et : datetime
        End timestamp
    business_hour_slots : List[Tuple[int]]
        Work schedule as list of tuples (start, end) in seconds since week start
    work_calendar
        Calendar exposing ``is_working_day(day)``. Dates rejected by the
        calendar are excluded from the result.

    Returns
    -------
    float
        Difference in business hours (seconds)
    """
    if st.tzinfo is not None:
        st = st.replace(tzinfo=None)
    if et.tzinfo is not None:
        et = et.replace(tzinfo=None)
    slots, total_seconds_per_week = _get_prepared_business_hour_slots(
        business_hour_slots
    )
    return _get_business_seconds(
        st, et, slots, total_seconds_per_week, work_calendar
    )
