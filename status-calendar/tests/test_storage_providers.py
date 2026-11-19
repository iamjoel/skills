import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import calendar_backend as backend
import connect_cloud
import render_card
import storage_providers
from calendar_store import Conflict, default_states, read_calendar, write_calendar
from save_edit import apply_edit


class MemoryStore:
    def __init__(self, account):
        self.source = hashlib.sha256(account.encode("utf-8")).hexdigest()
        self.snapshot = None

    def read(self):
        return copy.deepcopy(self.snapshot)

    def commit(self, snapshot, expected_revision):
        current = None if self.snapshot is None else self.snapshot["revision"]
        if current != expected_revision:
            raise Conflict(current if current is not None else 0)
        self.snapshot = copy.deepcopy(snapshot)
        return self.read()


class MemoryProvider:
    label = "Test memory store"
    setup_asset = "providers/memory/setup"

    def __init__(self):
        self.accounts = {}

    def prompt_settings(self):
        return {"account": "sample"}

    def authorize(self, payload):
        account = payload["account"]
        if account not in self.accounts:
            self.accounts[account] = MemoryStore(account)
        return self.restore({"account": account})

    def restore(self, binding):
        return self.accounts[binding["account"]], binding


def card_data(fragment):
    script = re.search(r'<script type="application/json"[^>]*>(.*?)</script>', fragment, re.DOTALL)
    return json.loads(script[1])


class StorageProviderTest(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.out = self.directory / "cards"
        self.provider = MemoryProvider()
        for context in (patch.dict(os.environ, STATUS_CALENDAR_DATA_DIR=temporary.name),
                        patch.dict(storage_providers.PROVIDERS, memory=self.provider)):
            context.start()
            self.addCleanup(context.stop)
        self.local = {"revision": 2, "states": default_states(),
                      "days": {"2026-11-16": [{"stateId": "short-run", "emoji": ""}]}}
        write_calendar(self.directory, self.local)
        self.payload = {"provider": "memory", "account": "private-test-account"}

    def test_registered_provider_connects_restores_edits_and_renders(self):
        self.assertIsNone(backend.active_provider_id(self.directory))
        message = dict(self.payload, action="connect", month="2026-11", resume="configure")
        output = io.BytesIO()
        with (patch.object(sys, "argv", ["connect_cloud.py"]),
              patch.object(sys, "stdin", io.StringIO(json.dumps(message))),
              patch.object(sys, "stdout", io.TextIOWrapper(output, write_through=True))):
            connect_cloud.main()
            result = json.loads(output.getvalue())
        self.assertTrue(result["imported"])
        self.assertEqual(result["resume"], "configure")
        self.assertEqual(backend.active_provider_id(self.directory), "memory")
        snapshot, source = backend.read_active(self.directory)
        self.assertEqual(snapshot, self.local)
        self.assertNotEqual(source, "local")
        entry = [{"stateId": "long-gym", "emoji": "🦵"}]
        operation = {"source": source, "revision": 2, "action": "day", "date": "2026-11-18", "entries": entry}
        self.assertEqual(apply_edit(operation)["revision"], 3)
        snapshot, saved_source = backend.read_active(self.directory)
        self.assertEqual(saved_source, source)
        self.assertEqual(snapshot["days"][operation["date"]], entry)
        with self.assertRaises(Conflict):
            apply_edit(operation)
        self.assertEqual(read_calendar(self.directory), self.local)
        fragment = render_card.render("configure", "2026-11", self.out).read_text()
        self.assertNotIn(self.payload["account"], fragment)
        config = card_data(fragment)
        self.assertEqual(config["source"], source)
        self.assertEqual(config["revision"], 3)
        self.assertEqual(config["states"], snapshot["states"])
        self.assertEqual(set(config["usedIds"]), {"short-run", "long-gym"})
        self.assertEqual(card_data(render_card.render("month", "2026-11", self.out).read_text())["days"], snapshot["days"])

    def test_setup_form_uses_registered_assets_and_active_provider(self):
        assets = self.directory / "fixtures"
        fixture = assets / self.provider.setup_asset
        fixture.parent.mkdir(parents=True)
        shutil.copyfile(render_card.ASSETS / "inline-card.html", assets / "inline-card.html")
        form_script = 'function renderStorageSetup(root, data) { root.textContent = "Memory settings " + data.provider; }'
        fixture.with_suffix(".js").write_text(form_script)
        fixture.with_suffix(".css").write_text("")
        with patch.object(render_card, "ASSETS", assets):
            explicit = render_card.render("storage", "2026-11", self.out, provider="memory").read_text()
            self.assertIn(form_script, explicit)
            self.assertEqual(card_data(explicit)["provider"], "memory")
            backend.connect(self.directory, self.payload)
            active = render_card.render("storage", "2026-11", self.out).read_text()
            self.assertIn(form_script, active)
            self.assertEqual(card_data(active)["provider"], "memory")
            self.assertNotIn(self.payload["account"], active)

    def test_failed_switch_preserves_previous_binding_and_rows(self):
        backend.connect(self.directory, self.payload)
        saved_file = backend.connection_file(self.directory)
        saved_binding = saved_file.read_bytes()
        another_store = MemoryStore("unavailable")
        self.provider.accounts["unavailable"] = another_store
        with patch.object(another_store, "commit", side_effect=OSError("write failed")):
            with self.assertRaisesRegex(OSError, "write failed"):
                backend.connect(self.directory, dict(self.payload, account="unavailable"))
        self.assertEqual(saved_file.read_bytes(), saved_binding)
        self.assertEqual(backend.read_active(self.directory)[0], self.local)
        self.assertIsNone(another_store.read())
        self.assertEqual(read_calendar(self.directory), self.local)

    def test_unknown_stored_provider_never_falls_back_to_local(self):
        backend.connect(self.directory, self.payload)
        del storage_providers.PROVIDERS["memory"]
        with self.assertRaises(ValueError):
            backend.read_active(self.directory)
        with self.assertRaises(ValueError):
            apply_edit({"source": "local", "revision": 2, "action": "day", "date": "2026-11-16", "entries": []})
        self.assertEqual(read_calendar(self.directory), self.local)

    def test_same_account_id_and_revision_on_different_provider_rejects_old_card(self):
        other = MemoryProvider()
        with patch.dict(storage_providers.PROVIDERS, other=other):
            backend.connect(self.directory, self.payload)
            _, old_source = backend.read_active(self.directory)
            backend.connect(self.directory, dict(self.payload, provider="other"))
            current, new_source = backend.read_active(self.directory)
            self.assertNotEqual(old_source, new_source)
            with self.assertRaises(Conflict):
                apply_edit({"source": old_source, "revision": current["revision"], "action": "day",
                            "date": "2026-11-16", "entries": []})
            self.assertEqual(backend.read_active(self.directory)[0], self.local)


if __name__ == "__main__":
    unittest.main()
