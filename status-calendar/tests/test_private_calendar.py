import base64
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from calendar_backend import connector_project
from calendar_store import Conflict, default_states, write_calendar
from providers.supabase.private_calendar import bind_result, check_receipt, edit_plan, import_plan, read_plan
from providers.supabase.private_binding import source_for


class PrivateCalendarTest(unittest.TestCase):
    ref = "abcdefghijklmnopqrst"
    other = "zyxwvutsrqponmlkjihg"

    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.snapshot = {"revision": 3, "states": default_states(),
                         "days": {"2026-11-18": [{"stateId": "mid-run", "emoji": ""}]}}
        write_calendar(self.directory, self.snapshot)

    def rows(self, snapshot):
        return {"rows": [{"project_ref": self.ref, "snapshot": snapshot}]}

    def test_import_validates_absence_and_keeps_calendar_text_out_of_sql(self):
        self.snapshot["states"][0]["label"] = "Robin's 跑步 🏃\n3 公里"
        write_calendar(self.directory, self.snapshot)
        plan = import_plan(self.directory, self.ref, self.rows(None))
        self.assertEqual((plan["imported_days"], plan["expected_revision"]), (1, 3))
        self.assertIn("on conflict (id) do nothing", plan["sql"])
        self.assertNotIn("Robin", plan["sql"])
        encoded = re.search(r"decode\('([A-Za-z0-9+/=]+)'", plan["sql"]).group(1)
        self.assertEqual(json.loads(base64.b64decode(encoded)), self.snapshot)
        for payload in (self.rows(self.snapshot), {"rows": []}, {"rows": [None]},
                        {"rows": [{"project_ref": self.other, "snapshot": None}]}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                import_plan(self.directory, self.ref, payload)

    def test_bind_requires_a_valid_cloud_row_and_rechecks_imported_local_revision(self):
        for malformed in (None, {}, dict(self.snapshot, revision=True), dict(self.snapshot, revision=-1),
                          dict(self.snapshot, states=None)):
            with self.subTest(snapshot=malformed), self.assertRaises(ValueError):
                bind_result(self.directory, self.ref, self.rows(malformed))
        with self.assertRaises(Conflict):
            bind_result(self.directory, self.ref, dict(self.rows(self.snapshot), imported_revision=2))
        self.assertIsNone(connector_project(self.directory))
        result = bind_result(self.directory, self.ref, dict(self.rows(self.snapshot), imported_revision=3))
        self.assertEqual((result["revision"], result["recorded_days"]), (3, 1))
        self.assertEqual(connector_project(self.directory), self.ref)

    def test_edit_confirms_project_and_card_source_then_guards_write(self):
        current = self.rows(self.snapshot)
        operation = {"action": "day", "date": "2026-11-18", "entries": [],
                     "source": source_for(self.ref), "revision": 3}
        with self.assertRaises(ValueError):
            edit_plan(self.directory, self.ref, dict(current, operation=operation))
        bind_result(self.directory, self.ref, current)
        with self.assertRaises(Conflict):
            edit_plan(self.directory, self.ref, dict(current, operation=dict(operation, revision=2)))
        with self.assertRaises(Conflict):
            edit_plan(self.directory, self.ref, dict(current, operation=dict(operation, source=source_for(self.other))))
        plan = edit_plan(self.directory, self.ref, dict(current, operation=operation))
        self.assertEqual(plan["expected_revision"], 4)
        self.assertIn("where id is true and revision = 3", plan["sql"])
        self.assertEqual(len(self.snapshot["days"]), 1)
        with self.assertRaises(ValueError):
            read_plan("a b")

    def test_receipt_requires_single_row_correct_project_and_exact_new_revision(self):
        receipt = {"project_ref": self.ref, "saved": True, "revision": 8}
        def check(row):
            return check_receipt(self.ref, {"rows": [row], "expected_revision": 8})
        self.assertTrue(check(receipt)["saved"])
        self.assertEqual(check(dict(receipt, saved=False, revision=None))["next"], "read")
        for row in (dict(receipt, saved=1), dict(receipt, revision=7), dict(receipt, saved=False),
                    dict(receipt, project_ref=self.other)):
            with self.subTest(row=row), self.assertRaises(ValueError):
                check(row)


if __name__ == "__main__":
    unittest.main()
