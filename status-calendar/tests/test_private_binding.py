import json
import os
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import calendar_backend as backend
from calendar_store import Conflict, default_states, read_calendar, write_calendar
from providers.supabase.private_binding import source_for
from render_card import render
from save_edit import apply_edit, edited_snapshot


class PrivateBindingTest(unittest.TestCase):
    project = "abcdefghijklmnopqrst"

    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)
        env = patch.dict(os.environ, STATUS_CALENDAR_DATA_DIR=tmp.name)
        env.start()
        self.addCleanup(env.stop)
        self.local = {"revision": 2, "states": default_states(), "days": {}}
        write_calendar(self.directory, self.local)

    def test_bind_checks_import_revision_and_persists_only_the_reference(self):
        with self.assertRaises(Conflict):
            backend.bind_connector(self.directory, self.project, expected_local_revision=1)
        self.assertIsNone(backend.connector_project(self.directory))
        backend.bind_connector(self.directory, self.project, expected_local_revision=2)
        path = backend.connection_file(self.directory)
        self.assertEqual(json.loads(path.read_text()), {
            "provider": "supabase", "binding": {"mode": "private_connector", "project_ref": self.project},
        })
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(backend.connector_project(self.directory), self.project)
        with self.assertRaises(ValueError):
            backend.bind_connector(self.directory, "invalid-ref")
        self.assertEqual(backend.connector_project(self.directory), self.project)
        with self.assertRaises(ValueError):
            backend.read_active(self.directory)
        with self.assertRaises(ValueError):
            apply_edit({"action": "configure", "revision": 2, "states": []})
        self.assertEqual(read_calendar(self.directory), self.local)

    def test_render_uses_only_the_fresh_snapshot_for_its_bound_project(self):
        source = source_for(self.project)
        remote = {"revision": 8, "states": default_states(), "days": {
            "2025-12-01": [{"stateId": "mid-run", "emoji": ""}],
            "2026-01-02": [{"stateId": "long-gym", "emoji": "🦵"}],
        }}
        def month_view():
            path = render("month", "2026-01", self.directory, connector_snapshot=(source, remote))
            raw = re.search(r'<script type="application/json"[^>]*>(.*?)</script>', path.read_text(), re.S)
            return json.loads(raw[1])

        with self.assertRaises(ValueError):
            month_view()
        backend.bind_connector(self.directory, self.project)
        data = month_view()
        self.assertEqual(data["source"], source)
        self.assertEqual(data["revision"], 8)
        self.assertEqual(data["days"], {"2026-01-02": remote["days"]["2026-01-02"]})
        backend.bind_connector(self.directory, "01234567890123456789")
        with self.assertRaises(ValueError):
            month_view()
        self.assertEqual(read_calendar(self.directory), self.local)

    def test_prepared_edit_checks_source_revision_and_shared_calendar_rules(self):
        source = source_for(self.project)
        snapshot = {"revision": 0, "states": None, "days": {}}
        operation = {"action": "day", "source": source, "revision": 0, "date": "2026-01-02",
                     "entries": [{"stateId": "long-gym", "emoji": "🦵"}]}
        updated = edited_snapshot(operation, snapshot, source)
        self.assertEqual(snapshot, {"revision": 0, "states": None, "days": {}})
        self.assertEqual(updated, {"revision": 1, "states": default_states(),
                                   "days": {"2026-01-02": operation["entries"]}})
        for change in ({"source": "local"}, {"revision": 4}):
            with self.assertRaises(Conflict):
                edited_snapshot(dict(operation, **change), snapshot, source)
        with self.assertRaises(ValueError):
            edited_snapshot({"action": "configure", "revision": 1, "source": source, "states": []},
                            updated, source)
        self.assertEqual(updated["states"], default_states())


if __name__ == "__main__":
    unittest.main()
