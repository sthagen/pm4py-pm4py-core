import random
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from pm4py.util.business_hours import (
    BusinessHours,
    get_business_day_seconds,
    soj_time_business_hours_diff,
)
from pm4py.util.constants import DEFAULT_BUSINESS_HOUR_SLOTS
from pm4py.util.vis_utils import human_readable_stat


class HolidayCalendar:
    def __init__(self, holidays):
        self.holidays = set(holidays)

    def is_working_day(self, day):
        if isinstance(day, datetime):
            day = day.date()
        return day.weekday() < 5 and day not in self.holidays


def weekday_slots(start_hour=8, end_hour=17):
    return [
        (
            weekday * 24 * 60 * 60 + start_hour * 60 * 60,
            weekday * 24 * 60 * 60 + end_hour * 60 * 60,
        )
        for weekday in range(5)
    ]


class BusinessHoursTest(unittest.TestCase):
    def test_business_day_duration_is_derived_from_weekly_slots(self):
        slots = weekday_slots(8, 16)

        self.assertEqual(8 * 60 * 60, get_business_day_seconds(slots))
        self.assertEqual(
            "4D",
            human_readable_stat(
                4 * 8 * 60 * 60, business_hour_slots=slots
            ),
        )
        self.assertEqual("1D", human_readable_stat(4 * 8 * 60 * 60))

    def test_performance_dfg_uses_business_days_in_labels(self):
        from pm4py.visualization.dfg.variants import performance

        duration = 4 * 8 * 60 * 60
        slots = weekday_slots(8, 16)
        graph = performance.apply(
            {("A", "B"): duration},
            activities_count={"A": 1, "B": 1},
            serv_time={"A": -1, "B": -1},
            parameters={"business_hour_slots": slots},
        )

        self.assertIn('label="4D"', graph.source)

    def test_discovered_performance_dfg_retains_business_hour_slots(self):
        import pm4py
        from pm4py.discovery import discover_performance_dfg
        from pm4py.objects.log.obj import Event, EventLog, Trace

        slots = weekday_slots(8, 16)
        trace = Trace(
            [
                Event(
                    {
                        "concept:name": "start",
                        "time:timestamp": datetime(2025, 1, 7, 8),
                    }
                ),
                Event(
                    {
                        "concept:name": "finish",
                        "time:timestamp": datetime(2025, 1, 10, 16),
                    }
                ),
            ]
        )

        dfg, start_activities, end_activities = discover_performance_dfg(
            EventLog([trace]),
            business_hours=True,
            business_hour_slots=slots,
            perf_aggregation_key="median",
        )
        with patch("pm4py.visualization.dfg.visualizer.view") as view:
            pm4py.view_performance_dfg(
                dfg,
                start_activities,
                end_activities,
                aggregation_measure="median",
            )
        graph = view.call_args.args[0]

        self.assertIsInstance(dfg, dict)
        self.assertEqual(4 * 8 * 60 * 60, dfg[("start", "finish")])
        self.assertEqual(tuple(slots), dfg.business_hour_slots)
        self.assertIn('label="4D"', graph.source)

    def test_variant_duration_uses_configured_working_day(self):
        from pm4py.visualization.variants_duration.variants.classic import (
            _format_duration,
        )

        duration = 4 * 8 * 60 * 60

        self.assertEqual("4.0d", _format_duration(duration, 8 * 60 * 60))
        self.assertEqual("1.3d", _format_duration(duration))

    def test_default_schedule_across_multiple_weeks(self):
        start = datetime(2024, 1, 1, 8, 30)
        end = datetime(2024, 1, 16, 10, 0)

        self.assertEqual(
            111 * 60 * 60 + 30 * 60,
            soj_time_business_hours_diff(
                start, end, DEFAULT_BUSINESS_HOUR_SLOTS
            ),
        )

    def test_overlapping_slots_are_counted_once(self):
        slots = [
            (9 * 60 * 60, 12 * 60 * 60),
            (10 * 60 * 60, 14 * 60 * 60),
        ]
        start = datetime(2024, 1, 1, 8, 0)
        end = datetime(2024, 1, 1, 15, 0)

        business_hours = BusinessHours(
            start, end, business_hour_slots=slots
        )

        self.assertEqual(5 * 60 * 60, business_hours.get_seconds())
        self.assertEqual(
            [[9 * 60 * 60, 14 * 60 * 60]],
            business_hours.business_hour_slots_unified,
        )

    def test_timezone_is_ignored_consistently(self):
        start = datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc)
        end = datetime(
            2024, 1, 1, 10, 0, tzinfo=timezone(timedelta(hours=2))
        )

        self.assertEqual(
            2 * 60 * 60,
            soj_time_business_hours_diff(
                start, end, DEFAULT_BUSINESS_HOUR_SLOTS
            ),
        )

    def test_schedule_mutation_is_visible_to_later_calls(self):
        slots = [(8 * 60 * 60, 9 * 60 * 60)]
        start = datetime(2024, 1, 1, 8, 0)
        end = datetime(2024, 1, 1, 10, 0)

        self.assertEqual(
            60 * 60, soj_time_business_hours_diff(start, end, slots)
        )
        slots[0] = (8 * 60 * 60, 10 * 60 * 60)
        self.assertEqual(
            2 * 60 * 60, soj_time_business_hours_diff(start, end, slots)
        )

    def test_workcalendar_excludes_holidays(self):
        slots = weekday_slots()
        calendar = HolidayCalendar(
            {date(2026, 12, 25), date(2026, 12, 26)}
        )
        start = datetime(2026, 12, 24, 8, 0)
        end = datetime(2026, 12, 28, 17, 0)

        business_hours = BusinessHours(
            start,
            end,
            business_hour_slots=slots,
            workcalendar=calendar,
        )

        self.assertIs(calendar, business_hours.work_calendar)
        self.assertIs(calendar, business_hours.workcalendar)
        self.assertEqual(18 * 60 * 60, business_hours.get_seconds())

    def test_event_log_performance_dfg_forwards_workcalendar(self):
        from pm4py.discovery import discover_performance_dfg
        from pm4py.objects.log.obj import Event, EventLog, Trace

        calendar = HolidayCalendar({date(2026, 12, 25)})
        trace = Trace(
            [
                Event(
                    {
                        "concept:name": "A",
                        "time:timestamp": datetime(2026, 12, 24, 8),
                    }
                ),
                Event(
                    {
                        "concept:name": "B",
                        "time:timestamp": datetime(2026, 12, 28, 17),
                    }
                ),
            ]
        )

        dfg, _, _ = discover_performance_dfg(
            EventLog([trace]),
            business_hours=True,
            business_hour_slots=weekday_slots(),
            workcalendar=calendar,
            perf_aggregation_key="mean",
        )

        self.assertEqual(18 * 60 * 60, dfg[("A", "B")])

    def test_work_calendar_spelling_and_helper_are_supported(self):
        calendar = HolidayCalendar({date(2024, 1, 1)})
        start = datetime(2024, 1, 1, 8, 0)
        end = datetime(2024, 1, 2, 10, 0)

        business_hours = BusinessHours(
            start,
            end,
            business_hour_slots=DEFAULT_BUSINESS_HOUR_SLOTS,
            work_calendar=calendar,
        )

        self.assertEqual(3 * 60 * 60, business_hours.get_seconds())
        self.assertEqual(
            3 * 60 * 60,
            soj_time_business_hours_diff(
                start,
                end,
                DEFAULT_BUSINESS_HOUR_SLOTS,
                work_calendar=calendar,
            ),
        )

    def test_calendar_applies_to_each_date_of_cross_midnight_slot(self):
        monday_at_22 = 22 * 60 * 60
        tuesday_at_2 = 24 * 60 * 60 + 2 * 60 * 60
        calendar = HolidayCalendar({date(2024, 1, 2)})

        self.assertEqual(
            2 * 60 * 60,
            soj_time_business_hours_diff(
                datetime(2024, 1, 1, 21, 0),
                datetime(2024, 1, 2, 3, 0),
                [(monday_at_22, tuesday_at_2)],
                work_calendar=calendar,
            ),
        )

    def test_matches_interval_based_reference(self):
        random_generator = random.Random(1988)
        epoch = datetime(2024, 1, 1)
        calendar = HolidayCalendar(
            {
                date(2024, 1, 3),
                date(2024, 1, 8),
                date(2024, 1, 19),
                date(2024, 2, 14),
            }
        )
        slots = [
            (7 * 60 * 60, 12 * 60 * 60),
            (11 * 60 * 60, 17 * 60 * 60),
            (
                2 * 24 * 60 * 60 + 9 * 60 * 60,
                2 * 24 * 60 * 60 + 18 * 60 * 60,
            ),
            (
                4 * 24 * 60 * 60 + 8 * 60 * 60,
                4 * 24 * 60 * 60 + 16 * 60 * 60,
            ),
        ]

        for _ in range(100):
            start = epoch + timedelta(
                seconds=random_generator.randrange(35 * 24 * 60 * 60)
            )
            end = start + timedelta(
                seconds=random_generator.randrange(21 * 24 * 60 * 60)
            )
            self.assertEqual(
                self._reference_seconds(start, end, slots),
                soj_time_business_hours_diff(start, end, slots),
            )
            self.assertEqual(
                self._reference_seconds(start, end, slots, calendar),
                soj_time_business_hours_diff(
                    start, end, slots, work_calendar=calendar
                ),
            )

    @staticmethod
    def _reference_seconds(start, end, slots, work_calendar=None):
        unified = []
        for begin, finish in sorted(slots):
            if unified and unified[-1][1] >= begin - 1:
                unified[-1][1] = max(unified[-1][1], finish)
            else:
                unified.append([begin, finish])

        week_start = start - timedelta(
            days=start.weekday(),
            hours=start.hour,
            minutes=start.minute,
            seconds=start.second,
            microseconds=start.microsecond,
        )
        total = 0.0
        while week_start < end:
            for begin, finish in unified:
                slot_start = week_start + timedelta(seconds=begin)
                slot_end = week_start + timedelta(seconds=finish)
                overlap_start = max(start, slot_start)
                overlap_end = min(end, slot_end)
                if work_calendar is None:
                    total += max(
                        0.0,
                        (overlap_end - overlap_start).total_seconds(),
                    )
                else:
                    while overlap_start < overlap_end:
                        next_day = datetime.combine(
                            overlap_start.date() + timedelta(days=1),
                            datetime.min.time(),
                        )
                        segment_end = min(overlap_end, next_day)
                        if work_calendar.is_working_day(
                            overlap_start.date()
                        ):
                            total += (
                                segment_end - overlap_start
                            ).total_seconds()
                        overlap_start = segment_end
            week_start += timedelta(days=7)
        return total


if __name__ == "__main__":
    unittest.main()
