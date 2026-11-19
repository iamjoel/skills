import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import calendar_backend as backend
from providers import supabase
from providers.supabase import auth


class LocalLoginTest(unittest.TestCase):
    project = "abcdefghijklmnopqrst"
    url = "https://" + project + ".supabase.co"
    automatic = {"provider": "supabase", "url": url, "project_ref": project,
                 "key": "sb_publishable_example_only", "local_login": True}
    email = "calendar@example.invalid"
    session = {"user_id": "00000000-0000-0000-0000-000000000001", "access_token": "unused",
               "refresh_token": "unused", "expires_at": 4102444800}

    def test_auto_prompts_locally_for_both_values_and_ignores_supplied_email(self):
        with patch.object(auth, "_local_input", side_effect=["  " + self.email + "  ", "test password"]) as prompt:
            with patch.object(auth, "_session_request", return_value=self.session) as exchange:
                _, binding = supabase.authorize(dict(self.automatic, email="wrong@example.invalid"))
        self.assertEqual([call.args for call in prompt.call_args_list], [(self.url,), (self.url, self.email)])
        settings = {"url": self.url, "key": self.automatic["key"], "email": self.email}
        exchange.assert_called_once_with(settings, "password", {"email": self.email, "password": "test password"})
        self.assertEqual(binding, {"settings": settings, "session": self.session})

    def test_manual_requests_preserve_email(self):
        settings = {"url": self.url, "key": self.automatic["key"], "email": self.email}
        with patch.object(auth, "_local_input", return_value="password") as prompt:
            with patch.object(auth, "_session_request", return_value=self.session):
                _, binding = supabase.authorize(settings)
        prompt.assert_called_once_with(self.url, self.email)
        self.assertEqual(binding["settings"], settings)

    def test_invalid_project_and_key_rejected_before_any_prompt(self):
        for change in ({"project_ref": None}, {"project_ref": "z" * 20}, {"project_ref": "A" * 20},
                       {"key": "sb_secret_example_secret"}, {"url": self.url + ".example"}):
            with self.subTest(change=change), patch.object(auth, "_local_input") as prompt:
                with self.assertRaises(ValueError):
                    supabase.authorize(dict(self.automatic, **change))
                prompt.assert_not_called()

    def test_cancel_leaves_previous_binding_intact(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            binding = backend.connection_file(directory)
            binding.write_text("previous content")
            with patch.object(auth, "_local_input", side_effect=ValueError("已取消登录。")):
                with patch.object(auth, "_session_request") as exchange:
                    with self.assertRaisesRegex(ValueError, "取消"):
                        backend.connect(directory, self.automatic)
                    exchange.assert_not_called()
            self.assertEqual(binding.read_text(), "previous content")

    def test_system_dialog_does_not_emit_credentials(self):
        with patch.object(sys, "stdin", io.StringIO()), patch.object(sys, "stderr", io.StringIO()):
            with patch.object(sys, "platform", "darwin"), patch.object(subprocess, "run") as run:
                run.return_value = Mock(returncode=0, stdout=(self.email + "\n").encode())
                self.assertEqual(auth._local_input(self.url), self.email)
                args = run.call_args.args[0]
                self.assertEqual(args[-1], self.url)
                self.assertNotIn(self.email, repr(args))
                self.assertTrue(run.call_args.kwargs["capture_output"])
                run.return_value = Mock(returncode=1, stderr=b"cancelled (-128)")
                with self.assertRaisesRegex(ValueError, "取消"):
                    auth._local_input(self.url, self.email)
                self.assertEqual(sys.stderr.getvalue(), "")

    def test_new_user_guidance_omits_server_body(self):
        failure = HTTPError(self.url, 400, "invalid credentials", {}, io.BytesIO(self.email.encode()))
        with patch.object(auth, "build_opener") as opener, patch.object(auth, "_local_input", return_value="test"):
            opener.return_value.open.side_effect = failure
            with self.assertRaisesRegex(ValueError, "Authentication → Users") as caught:
                supabase.authorize(dict(self.automatic, local_login=False, email=self.email))
        self.assertNotIn(self.email, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
