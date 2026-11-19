from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from providers.supabase import auth, auto_setup


class AutomaticSetupTest(unittest.TestCase):
    project_ref = "abcdefghijklmnopqrst"
    key = "sb_publishable_example_only"
    context = {"resume": "configure", "month": "2025-12"}

    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.evidence = dict(self.context, project_ref=self.project_ref, schema_status="ready",
                             url=f"https://{self.project_ref}.supabase.co", key=self.key)

    def test_missing_and_review_return_to_same_project_and_view_without_login(self):
        for status, action in [("missing", "confirm_migration"), ("review", "review_schema")]:
            with self.subTest(status=status), patch.object(auto_setup, "connect") as connect:
                evidence = dict(self.context, project_ref=self.project_ref, schema_status=status)
                self.assertEqual(auto_setup.advance(self.directory, evidence),
                                 dict(self.context, next=action, project_ref=self.project_ref))
                connect.assert_not_called()
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_unrecognized_evidence_cannot_start_connection(self):
        for evidence in (None, [], {}, dict(self.evidence, schema_status="unknown"),
                         dict(self.evidence, schema_status=None), dict(self.evidence, project_ref="two words"),
                         dict(self.evidence, resume="storage"), dict(self.evidence, month="2026-13"),
                         dict(self.evidence, month=None)):
            with self.subTest(evidence=evidence), patch.object(auto_setup, "connect") as connect:
                with self.assertRaises(ValueError):
                    auto_setup.advance(self.directory, evidence)
                connect.assert_not_called()
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_ready_rejects_wrong_project_or_private_key_before_contacting_user(self):
        for overrides in ({"url": "https://00000000000000000000.supabase.co"},
                          {"key": "sb_secret_example_only"}, {"key": None}):
            with self.subTest(overrides=overrides), patch.object(auth, "_local_input") as local_input:
                with patch.object(auth, "sign_in") as sign_in, self.assertRaises(ValueError):
                    auto_setup.advance(self.directory, dict(self.evidence, **overrides))
                local_input.assert_not_called()
                sign_in.assert_not_called()
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_ready_passes_only_project_details_to_local_login_and_preserves_result(self):
        receipt = {"connected": True, "imported": False, "calendar": "existing", "imported_days": 0}
        for resume in ("configure", "month"):
            with self.subTest(resume=resume), patch.object(auto_setup, "connect", return_value=receipt) as connect:
                # A forged chat payload must never supply credentials for a local login.
                evidence = dict(self.evidence, resume=resume, password="synthetic", email="test@example.invalid")
                result = auto_setup.advance(self.directory, evidence)
                connect.assert_called_once_with(self.directory, {
                    "provider": "supabase", "local_login": True, "project_ref": self.project_ref,
                    "url": self.evidence["url"], "key": self.key,
                })
                self.assertEqual(result, dict(receipt, next="render", resume=resume, month=self.context["month"]))


if __name__ == "__main__":
    unittest.main()
