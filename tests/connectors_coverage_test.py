import importlib.machinery
import os
import sqlite3
import sys
import tempfile
import types
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest import mock

import pandas as pd

from pm4py.algo.connectors import algorithm
from pm4py.algo.connectors.variants import (
    chrome_history,
    firefox_history,
    github_repo,
    outlook_calendar,
    outlook_mail_extractor,
    windows_events,
)


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class _Box:
    def __init__(self, items):
        self.Items = items


class ConnectorsCoverageTest(unittest.TestCase):
    def test_chrome_history_sqlite_file_and_directory_profiles(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = os.path.join(directory, "Default")
            os.mkdir(profile)
            path = os.path.join(profile, "History")
            connection = sqlite3.connect(path)
            connection.execute(
                "CREATE TABLE urls (id INTEGER, url TEXT, title TEXT, typed_count INTEGER, visit_count INTEGER)"
            )
            connection.execute(
                "CREATE TABLE visits (url INTEGER, visit_time INTEGER, visit_duration INTEGER, transition INTEGER, from_visit INTEGER)"
            )
            connection.executemany(
                "INSERT INTO urls VALUES (?, ?, ?, ?, ?)",
                [
                    (1, "https://example.com/path?q=1", "Example", 1, 3),
                    (2, "https://referrer.test/", None, 0, 1),
                ],
            )
            connection.execute(
                "INSERT INTO visits VALUES (?, ?, ?, ?, ?)",
                (1, 13200000000000000, 2500000, 0x1000001, 2),
            )
            connection.commit()
            connection.close()

            dataframe = chrome_history.apply({"history_db_path": directory})
            self.assertEqual(1, len(dataframe))
            self.assertEqual("example.com/path", dataframe.iloc[0]["concept:name"])
            self.assertEqual(2.5, dataframe.iloc[0]["visit_duration"])
            self.assertEqual("TYPED", dataframe.iloc[0]["transition"])
            self.assertEqual("https://referrer.test/", dataframe.iloc[0]["referrer"])
            self.assertEqual("UNKNOWN_255", chrome_history._decode_transition(255))

            single = chrome_history.apply({"history_db_path": path})
            self.assertEqual("DEFAULT", single.iloc[0]["case:concept:name"])
            self.assertTrue(chrome_history.apply({"history_db_path": os.path.join(directory, "missing")}).empty)

    def test_firefox_history_sqlite_file_and_directory_profiles(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = os.path.join(directory, "profile.default")
            os.mkdir(profile)
            path = os.path.join(profile, "places.sqlite")
            connection = sqlite3.connect(path)
            connection.execute(
                "CREATE TABLE moz_places (id INTEGER, url TEXT, title TEXT, visit_count INTEGER, typed INTEGER, frecency INTEGER, guid TEXT)"
            )
            connection.execute(
                "CREATE TABLE moz_historyvisits (place_id INTEGER, visit_date INTEGER, visit_type INTEGER, session INTEGER, from_visit INTEGER)"
            )
            connection.execute(
                "INSERT INTO moz_places VALUES (1, 'https://example.org/a?q=1', 'Title', 4, 1, 50, 'guid')"
            )
            connection.execute(
                "INSERT INTO moz_historyvisits VALUES (1, 1704067200000000, 8, 2, 0)"
            )
            connection.commit()
            connection.close()

            dataframe = firefox_history.apply({"history_db_path": directory})
            self.assertEqual(1, len(dataframe))
            self.assertEqual("RELOAD", dataframe.iloc[0]["visit_type_desc"])
            self.assertTrue(dataframe.iloc[0]["typed"])
            single = firefox_history.apply({"history_db_path": path})
            self.assertEqual("DEFAULT", single.iloc[0]["case:concept:name"])
            self.assertTrue(firefox_history.apply({"history_db_path": os.path.join(directory, "missing")}).empty)

    def test_github_connector_with_mocked_paginated_api(self):
        issue = {
            "timeline_url": "https://api.example/timeline/1",
            "created_at": "2024-01-01T00:00:00Z",
            "user": {"login": "alice"},
            "author_association": "MEMBER",
            "title": "Issue",
            "pull_request": {"url": "https://api.example/pr/1"},
        }
        timeline = [
            {
                "created_at": "2024-01-02T00:00:00Z",
                "event": "closed",
                "actor": {"login": "bob"},
            },
            {"event": "ignored"},
        ]
        responses = [_Response([issue]), _Response(timeline), _Response([])]
        requests_module = types.ModuleType("requests")
        requests_module.get = mock.Mock(side_effect=responses)
        with mock.patch.dict(sys.modules, {"requests": requests_module}), mock.patch.object(
            github_repo.importlib.util, "find_spec", return_value=None
        ), mock.patch.object(github_repo.time, "sleep"):
            dataframe = github_repo.apply(
                {"owner": "owner", "repository": "repo", "auth_token": "secret"}
            )
        self.assertEqual(2, len(dataframe))
        self.assertEqual({"created", "closed"}, set(dataframe["concept:name"]))
        self.assertEqual(
            "Bearer secret",
            requests_module.get.call_args_list[0].kwargs["headers"]["Authorization"],
        )

    def test_outlook_calendar_and_mail_connectors(self):
        now = datetime.now(timezone.utc) - timedelta(days=1)
        calendar_item = types.SimpleNamespace(
            ConversationID="meeting-1",
            Subject="Planning",
            CreationTime=now,
            LastModificationTime=now + timedelta(minutes=1),
            Start=now + timedelta(hours=1),
            Duration=30,
            MeetingStatus=5,
            ReminderSet=True,
            ReminderMinutesBeforeStart=15,
        )
        with mock.patch.object(outlook_calendar.mail_utils, "connect", return_value=_Box([calendar_item])), mock.patch.object(
            outlook_calendar.importlib.util, "find_spec", return_value=None
        ):
            calendar = outlook_calendar.apply(
                {"email_user": "user@example.com", "calendar_id": 9, "include_reminders": True}
            )
        self.assertEqual(6, len(calendar))
        self.assertIn("Meeting Cancelled", set(calendar["concept:name"]))
        self.assertIn("Meeting Reminder Fired", set(calendar["concept:name"]))

        sender = types.SimpleNamespace(Name="Alice")
        recipients = [types.SimpleNamespace(Name="Bob")]
        mail_item = types.SimpleNamespace(
            Class=43,
            Subject="Hello",
            CreationTime=now,
            Sender=sender,
            Recipients=recipients,
            ConversationID="conversation-1",
            ConversationTopic="Topic",
        )
        boxes = [_Box([mail_item]), _Box([mail_item])]
        with mock.patch.object(outlook_mail_extractor.mail_utils, "connect", side_effect=boxes), mock.patch.object(
            outlook_mail_extractor.importlib.util, "find_spec", return_value=None
        ):
            mails = outlook_mail_extractor.apply()
        self.assertEqual(2, len(mails))
        self.assertEqual({"Sent Mail", "Received Mail"}, set(mails["concept:name"]))

    def test_windows_events_connector_with_fake_com_client(self):
        values = {
            "Category": "1",
            "CategoryString": "system",
            "ComputerName": "host",
            "EventCode": "10",
            "EventIdentifier": "20",
            "EventType": "3",
            "LogFile": "Application",
            "Message": "message",
            "RecordNumber": "2",
            "SourceName": "service",
            "TimeGenerated": "20240101010101.000000+000",
            "TimeWritten": "20240101010102.000000+000",
            "Type": "Information",
            "User": "alice",
        }

        class EventItem:
            def Properties_(self, name):
                return values[name]

        services = types.SimpleNamespace(ExecQuery=lambda query: [EventItem()])
        locator = types.SimpleNamespace(ConnectServer=lambda *args: services)
        client = types.ModuleType("win32com.client")
        client.Dispatch = lambda name: locator
        client.__spec__ = importlib.machinery.ModuleSpec("win32com.client", loader=None)
        package = types.ModuleType("win32com")
        package.client = client
        package.__spec__ = importlib.machinery.ModuleSpec("win32com", loader=None)
        with mock.patch.dict(sys.modules, {"win32com": package, "win32com.client": client}), mock.patch.object(
            windows_events.importlib.util, "find_spec", return_value=None
        ):
            dataframe = windows_events.apply()
        self.assertEqual(1, len(dataframe))
        self.assertEqual("service 20", dataframe.iloc[0]["concept:name"])

    def test_connector_algorithm_routes_every_variant(self):
        module_names = {
            "chrome_history": "chrome_history",
            "firefox_history": "firefox_history",
            "github_repo": "github_repo",
            "outlook_calendar": "outlook_calendar",
            "outlook_mail": "outlook_mail_extractor",
            "windows_events": "windows_events",
            "camunda_workflow": "camunda_workflow",
            "sap_accounting": "sap_accounting",
            "sap_o2c": "sap_o2c",
        }
        expected = pd.DataFrame({"value": [1]})
        with ExitStack() as stack:
            for module_name in set(module_names.values()):
                module = __import__(f"pm4py.algo.connectors.variants.{module_name}", fromlist=[module_name])
                stack.enter_context(mock.patch.object(module, "apply", return_value=expected))
            for connector_type in module_names:
                result = algorithm.apply(connector_type, args={"conn": object()})
                self.assertIs(result, expected)
        self.assertIsNone(algorithm.apply("unknown", args={}))


if __name__ == "__main__":
    unittest.main()
