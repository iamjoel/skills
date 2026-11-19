import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import calendar_backend as backend
import connect_cloud
from calendar_store import Conflict, default_states, read_calendar, write_calendar, write_private_json
from providers.supabase import auth, auto_setup, store
from render_card import render
from save_edit import apply_edit


class CloudCalendarTest(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.settings = {"url": "https://abcdefghijklmnopqrst.supabase.co",
                         "key": "sb_publishable_example_only", "email": "test@example.invalid"}
        self.session = {"access_token": "example-access", "refresh_token": "example-refresh",
                        "user_id": "00000000-0000-0000-0000-000000000001", "expires_at": 4102444800}
        self.original = {"revision": 1, "states": default_states(),
                         "days": {"2026-11-11": [{"stateId": "mid-run", "emoji": ""}]}}
        write_calendar(self.directory, self.original)
        self.remote = None
        for context in (patch.dict(os.environ, STATUS_CALENDAR_DATA_DIR=temporary.name),
                        patch.object(auth, "sign_in", return_value=self.session),
                        patch.object(store, "_request", side_effect=self.exchange)):
            context.start()
            self.addCleanup(context.stop)

    def exchange(self, settings, session, method, filters, payload=None):
        self.assertEqual(settings, self.settings)
        self.assertEqual(session, self.session)
        user_id = self.session["user_id"]
        if method == "POST":
            self.assertIsNone(self.remote, "An existing cloud calendar must not be replaced")
            self.remote = {key: copy.deepcopy(payload[key]) for key in ("revision", "states", "days")}
        elif method == "PATCH":
            self.assertEqual(filters["revision"], "eq." + str(self.remote["revision"]))
            self.assertEqual(filters["user_id"], "eq." + user_id)
            self.remote = copy.deepcopy(payload)
        else:
            self.assertEqual(method, "GET")
            self.assertEqual(filters["user_id"], "eq." + user_id)
        return [] if self.remote is None else [dict(copy.deepcopy(self.remote), user_id=user_id)]

    def test_first_connection_imports_without_overwriting_existing_cloud_data(self):
        self.assertTrue(backend.connect(self.directory, self.settings)["imported"])
        self.assertEqual(self.remote, self.original)
        self.remote.update(revision=7, days={})
        self.assertFalse(backend.connect(self.directory, self.settings)["imported"])
        self.assertEqual(self.remote["revision"], 7)
        self.assertEqual(self.remote["days"], {})
        self.assertEqual(read_calendar(self.directory), self.original)
        self.assertEqual(backend.connection_file(self.directory).stat().st_mode & 0o777, 0o600)

    def test_ready_setup_receipt_counts_recorded_dates_only_on_first_import(self):
        self.original["days"]["2026-10-03"] = [
            {"stateId": "short-run", "emoji": ""}, {"stateId": "long-gym", "emoji": "🦵"},
        ]
        self.original["days"]["2026-11-12"] = []
        write_calendar(self.directory, self.original)
        evidence = {"project_ref": "abcdefghijklmnopqrst", "schema_status": "ready", "resume": "month",
                    "month": "2026-10", "url": self.settings["url"], "key": self.settings["key"]}
        with patch.object(auth, "_local_input", return_value=self.settings["email"]):
            created = auto_setup.advance(self.directory, evidence)
            self.assertEqual(created, {"connected": True, "calendar": "created", "imported": True,
                                       "imported_days": 2, "next": "render", "resume": "month", "month": "2026-10"})
            self.assertEqual(self.remote, self.original)
            remote_only = {"2025-05-02": [{"stateId": "short-run", "emoji": ""}]}
            self.remote.update(revision=9, days=remote_only)
            existing = auto_setup.advance(self.directory, evidence)
            self.assertEqual(existing, {"connected": True, "calendar": "existing", "imported": False,
                                        "imported_days": 0, "next": "render", "resume": "month", "month": "2026-10"})
        self.assertEqual(self.remote["days"], remote_only)
        self.assertEqual(self.remote["revision"], 9)
        self.assertEqual(read_calendar(self.directory), self.original)

    def test_local_card_cannot_write_after_switch_even_with_same_revision(self):
        backend.connect(self.directory, self.settings)
        with self.assertRaises(Conflict):
            apply_edit({"revision": 1, "action": "day", "date": "2026-11-11", "entries": []})
        self.assertEqual(self.remote, self.original)
        fragment = render("month", "2026-11", self.directory).read_text()
        self.assertNotIn("function renderStorageSetup(", fragment)
        for value in [*self.settings.values(), self.session["access_token"], self.session["refresh_token"]]:
            self.assertNotIn(value, fragment)

    def test_cloud_read_error_cannot_fork_or_modify_local_records(self):
        backend.connect(self.directory, self.settings)
        _, source = backend.read_active(self.directory)
        with patch.object(store.SupabaseStore, "read", side_effect=ValueError("offline")):
            with self.assertRaisesRegex(ValueError, "offline"):
                apply_edit({"revision": 1, "source": source, "action": "day",
                            "date": "2026-11-11", "entries": []})
        self.assertEqual(read_calendar(self.directory), self.original)
        self.assertEqual(self.remote, self.original)

    def test_legacy_connection_accepts_cards_with_original_owner_hash(self):
        legacy = self.directory / "supabase-session.json"
        write_private_json(legacy, {"settings": self.settings, "session": self.session})
        self.remote = copy.deepcopy(self.original)
        owner = self.settings["url"] + "/" + self.session["user_id"]
        old_source = hashlib.sha256(owner.encode("utf-8")).hexdigest()
        self.assertEqual(backend.read_active(self.directory), (self.original, old_source))
        result = apply_edit({"source": old_source, "revision": 1, "action": "day",
                             "date": "2026-11-11", "entries": []})
        self.assertEqual(result["revision"], 2)
        self.assertEqual(self.remote["days"], {})
        self.assertEqual(read_calendar(self.directory), self.original)

    def test_legacy_connect_message_without_provider_uses_supabase(self):
        message = dict(self.settings, action="connect", resume="configure", month="2026-11")
        output = io.BytesIO()
        with (patch.object(sys, "argv", ["connect_cloud.py"]),
              patch.object(sys, "stdin", io.StringIO(json.dumps(message))),
              patch.object(sys, "stdout", io.TextIOWrapper(output, write_through=True))):
            connect_cloud.main()
            result = json.loads(output.getvalue())
        self.assertTrue(result["connected"])
        self.assertEqual(result["resume"], "configure")
        self.assertEqual(self.remote, self.original)
        self.assertEqual(backend.active_provider_id(self.directory), "supabase")
        self.assertEqual(backend.connection_file(self.directory).name, "storage-connection.json")


if __name__ == "__main__":
    unittest.main()
