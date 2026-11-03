#!/usr/bin/env python3
"""Synthetic pipeline tests: no TTS service, speech model, or medical content.

Run with ``python3 -B -m unittest discover -s tests -v`` from the Skill folder.
PCM fixtures exercise file integrity and state transitions only. The synthetic
review records below are test fixtures, not evidence of listening or fact checks.
"""

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import wave


sys.dont_write_bytecode = True
SKILL_ROOT = Path(__file__).resolve().parents[1]


def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validator = load_script("validate_episode", "validate_episode.py")
renderer = load_script("synthetic_podcast_renderer", "render_episode.py")


def synthetic_pcm(label="fixture"):
    """Return a valid, deterministic 48 kHz PCM fixture, never generated speech."""
    sample = 1 + int.from_bytes(hashlib.sha256(label.encode()).digest()[:2], "little") % 30000
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(48000)
        output.writeframes(sample.to_bytes(2, "little", signed=True) * 4800)
    return stream.getvalue()


@contextlib.contextmanager
def synthetic_service(*args, **kwargs):
    yield "synthetic-test-service"


class SyntheticPipelineTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="podcast-synthetic-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "input.json"
        self.output = self.root / "render"
        self.show_path = self.root / "show.json"
        self.show = json.loads((SKILL_ROOT / "assets" / "show.json").read_text(encoding="utf-8"))
        for speaker in ("male", "female"):
            reference = self.root / (speaker + "-synthetic-reference.wav")
            reference.write_bytes(synthetic_pcm(speaker))
            self.show["speakers"][speaker]["reference"] = str(reference)
        self.save_json(self.show_path, self.show)
        self.episode = {
            "schema_version": 1,
            "title": "Synthetic pipeline fixture",
            "language": "zh-CN",
            "sources": [{"id": "s1", "title": "Synthetic source fixture",
                         "url": "https://example.invalid/synthetic-test", "type": "synthetic",
                         "accessed_at": "2026-10-23"}],
            "claims": [{"id": "c1", "text": "这是合成测试记录，不表达医学结论。",
                        "source_ids": ["s1"], "population": "synthetic fixture",
                        "outcome": "synthetic fixture", "limitations": "synthetic fixture",
                        "applicability": "automated tests only", "certainty": "synthetic fixture"}],
            "chapters": [{"id": "ch1", "title": "Synthetic chapter"}],
            "turns": [
                {"id": "t1", "speaker": "male", "chapter_id": "ch1",
                 "text": "这是合成测试。", "claim_ids": ["c1"]},
                {"id": "t2", "speaker": "female", "chapter_id": "ch1",
                 "text": "这是第二段测试。", "claim_ids": []},
            ],
            "reviews": {},
        }
        self.bind_synthetic_reviews()
        self.args = argparse.Namespace(episode=str(self.source), show=str(self.show_path),
                                       output_dir=str(self.output), redo=[],
                                       endpoint="http://127.0.0.1:8808")
        patches = contextlib.ExitStack()
        self.addCleanup(patches.close)
        self.synth = patches.enter_context(mock.patch.object(
            renderer, "synthesize", side_effect=self.synthesize))
        patches.enter_context(mock.patch.object(renderer, "service", synthetic_service))
        patches.enter_context(mock.patch.object(renderer, "engine_identity", return_value={"synthetic_test": True}))
        patches.enter_context(mock.patch.object(renderer, "ffmpeg", return_value=None))

    @staticmethod
    def save_json(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def synthesize(endpoint, text, *args, **kwargs):
        return synthetic_pcm(text)

    def bind_synthetic_reviews(self):
        content_hash = validator.review_content_sha256(self.episode)
        self.episode["reviews"] = {
            key: {"status": "passed", "reviewer": "synthetic test fixture",
                  "reviewed_at": "2026-10-23", "notes": "Synthetic test only; no medical review.",
                  "content_sha256": content_hash}
            for key in ("evidence", "editorial")
        }
        self.save_json(self.source, self.episode)

    def render(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return renderer.render(self.args)

    def manifest(self):
        return json.loads((self.output / "render-manifest.json").read_text(encoding="utf-8"))

    def synthetic_audio_review(self):
        path = self.output / "audio-review.json"
        review = json.loads(path.read_text(encoding="utf-8"))
        review.update(status="passed", reviewer="synthetic test fixture", reviewed_at="2026-10-23",
                      notes="Synthetic test state only; no actual listening performed.")
        for segment in review["segments"]:
            segment.update(status="passed", notes="Synthetic test fixture only.")
        self.save_json(path, review)

    def finalize(self):
        return renderer.finalize(argparse.Namespace(render_dir=str(self.output)))

    def test_script_only_export_keeps_pending_and_does_not_synthesize(self):
        for review in self.episode["reviews"].values():
            review.update(status="pending", reviewer="", reviewed_at="", notes="Synthetic pending fixture")
        self.save_json(self.source, self.episode)
        episode, warnings = validator.load_episode(self.source)
        exported = validator.export_text(episode, self.root / "script")
        self.assertEqual(set(exported), {"transcript.md", "show-notes.md", "evidence.json"})
        self.assertTrue(any("尚未通过" in warning for warning in warnings))
        self.synth.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_rendered_fixture_can_finalize_after_synthetic_review(self):
        self.render()
        self.synthetic_audio_review()
        result = self.finalize()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["formats"], ["wav"])
        delivery = Path(result["delivery"])
        with wave.open(str(delivery / "episode.wav"), "rb") as audio:
            self.assertEqual((audio.getframerate(), audio.getnchannels(), audio.getsampwidth()), (48000, 1, 2))
            self.assertEqual(audio.getnframes(), 23040)
        self.assertTrue((delivery / "episode.json").is_file())
        self.assertTrue((delivery / "audio-review.json").is_file())

    def test_editing_script_invalidates_old_review_before_render(self):
        self.episode["turns"][0]["text"] = "这是修改后的合成测试。"
        self.save_json(self.source, self.episode)
        with self.assertRaisesRegex(ValueError, "审稿所绑定的内容"):
            self.render()
        self.synth.assert_not_called()
        self.assertFalse((self.output / "render-manifest.json").exists())
        self.assertFalse((self.output / "draft.wav").exists())

    def test_finalize_rejects_source_changed_after_render(self):
        self.render()
        self.synthetic_audio_review()
        self.episode["turns"][0]["text"] = "这是重新审过的合成测试。"
        self.bind_synthetic_reviews()
        with self.assertRaisesRegex(ValueError, "脚本、配置、声音或引擎已变化"):
            self.finalize()
        self.assertFalse(list(self.output.glob("delivery-*")))

    def test_unmanaged_directory_preserves_existing_user_files(self):
        self.output.mkdir()
        originals = {"draft.wav": b"user draft", "episode.json": b"user episode",
                     "render-manifest.json": b"user manifest"}
        for name, content in originals.items():
            (self.output / name).write_bytes(content)
        with self.assertRaisesRegex(ValueError, "非空且不是本工具"):
            self.render()
        for name, content in originals.items():
            self.assertEqual((self.output / name).read_bytes(), content)
        self.synth.assert_not_called()

    def test_pending_audio_review_blocks_finalize(self):
        self.render()
        with self.assertRaisesRegex(ValueError, "尚未完成整体回听"):
            self.finalize()
        self.assertFalse(list(self.output.glob("delivery-*")))

    def test_valid_wav_tampering_blocks_finalize(self):
        self.render()
        self.synthetic_audio_review()
        segment = self.manifest()["segments"][0]
        path = self.output / segment["file"]
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        path.write_bytes(synthetic_pcm("different PCM payload"))
        self.assertNotEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)
        with wave.open(str(path), "rb") as audio:
            self.assertGreater(audio.getnframes(), 0)
        with self.assertRaisesRegex(ValueError, "片段文件已改变"):
            self.finalize()
        self.assertFalse(list(self.output.glob("delivery-*")))

    def test_failure_blocks_finalize_and_resume_reuses_good_segment(self):
        self.render()
        first, second = self.manifest()["segments"]
        first_bytes = (self.output / first["file"]).read_bytes()
        (self.output / second["file"]).write_bytes(b"broken synthetic cache")
        self.synth.side_effect = RuntimeError("synthetic request failure")
        with self.assertRaisesRegex(RuntimeError, "synthetic request failure"):
            self.render()
        self.assertFalse(self.manifest()["complete"])
        self.assertFalse((self.output / "draft.wav").exists())
        with self.assertRaisesRegex(ValueError, "生成记录未完成"):
            self.finalize()
        self.synth.reset_mock()
        self.synth.side_effect = self.synthesize
        self.render()
        self.assertEqual(self.synth.call_count, 1)
        self.assertEqual(self.synth.call_args.args[1], self.episode["turns"][1]["text"])
        self.assertEqual((self.output / first["file"]).read_bytes(), first_bytes)
        self.assertTrue(self.manifest()["complete"])

    def test_failed_redo_cannot_revive_old_audio_and_passed_review(self):
        self.render()
        self.synthetic_audio_review()
        self.args.redo = ["t2-001"]
        self.synth.side_effect = RuntimeError("synthetic redo failure")
        with self.assertRaisesRegex(RuntimeError, "synthetic redo failure"):
            self.render()
        self.synth.reset_mock()
        self.synth.side_effect = self.synthesize
        self.args.redo = []
        self.render()
        self.assertEqual(self.synth.call_count, 1, "Failed redo must not silently reuse the old audio")
        review = json.loads((self.output / "audio-review.json").read_text(encoding="utf-8"))
        self.assertEqual(review["status"], "pending")
        statuses = {segment["id"]: segment["status"] for segment in review["segments"]}
        self.assertEqual(statuses["t2-001"], "pending")

    def test_local_redo_resets_affected_and_overall_review(self):
        self.render()
        self.synthetic_audio_review()
        self.synth.reset_mock()
        self.args.redo = ["t2-001"]
        self.render()
        self.assertEqual(self.synth.call_count, 1)
        self.assertEqual(self.synth.call_args.args[1], self.episode["turns"][1]["text"])
        review = json.loads((self.output / "audio-review.json").read_text(encoding="utf-8"))
        checks = {segment["id"]: segment["status"] for segment in review["segments"]}
        self.assertEqual(review["status"], "pending")
        self.assertEqual(checks, {"t1-001": "passed", "t2-001": "pending"})


if __name__ == "__main__":
    unittest.main()
