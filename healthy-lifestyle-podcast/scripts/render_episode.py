#!/usr/bin/env python3
"""Local VoxCPM2 podcast rendering. Standard library only; no package installation."""
import argparse
import base64
import contextlib
import datetime as dt
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import wave

from validate_episode import export_text, load_episode

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHOW = ROOT / "assets" / "show.json"
GEN_KEYS = ("seed", "max_steps", "inference_timesteps", "cfg_value", "temperature")
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def file_hash(path):
    return digest(Path(path).read_bytes())


def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".write-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, data):
    atomic_bytes(path, (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode())


def managed_directory(path):
    """Only reuse directories explicitly owned by this renderer."""
    path.mkdir(parents=True, exist_ok=True)
    marker = path / ".podcast-render.json"
    if marker.is_symlink():
        raise ValueError("生成目录标记不能是符号链接")
    if marker.exists():
        if read_json(marker) != {"managed_by": "podcast-renderer", "schema_version": 1}:
            raise ValueError("输出目录属于其他工具或不同版本")
    elif any(path.iterdir()):
        raise ValueError("输出目录非空且不是本工具的生成目录，请换用新的目录")
    else:
        write_json(marker, {"managed_by": "podcast-renderer", "schema_version": 1})


@contextlib.contextmanager
def directory_lock(path):
    lock = path / ".podcast.lock"
    if lock.is_symlink():
        raise ValueError("生成目录锁不能是符号链接")
    with lock.open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("该目录已有配音或定稿操作运行，请等待完成")
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def executable(name, fallback=None):
    value = shutil.which(name)
    if value:
        return str(Path(value).resolve())
    if fallback and Path(fallback).is_file() and os.access(fallback, os.X_OK):
        return str(Path(fallback).resolve())
    return None


def voxcpm():
    return executable("voxcpm", Path.home() / ".local/bin/voxcpm")


def ffmpeg():
    override = os.environ.get("FFMPEG_BINARY")
    if override:
        return executable(override)
    return executable("ffmpeg")


def load_show(path):
    path = Path(path).expanduser().resolve()
    data = read_json(path)
    if data.get("schema_version") != 1 or set(data.get("speakers", {})) != {"male", "female"}:
        raise ValueError("show.json 需要 schema_version=1 和 male/female 两个角色")
    for role, speaker in data["speakers"].items():
        for key in ("name", "style", "reference", "audition_text"):
            if not isinstance(speaker.get(key), str) or not speaker[key].strip():
                raise ValueError("{} 缺少 {}".format(role, key))
    limits = {"seed": (0, 2147483647), "max_steps": (1, 4000),
              "inference_timesteps": (1, 100), "segment_target_chars": (10, 100),
              "segment_max_chars": (10, 100), "within_turn_pause_ms": (0, 2000),
              "turn_pause_ms": (0, 2000), "chapter_pause_ms": (0, 4000),
              "request_timeout_seconds": (1, 3600), "retries": (0, 3)}
    tts = data.get("tts", {})
    for key, bounds in limits.items():
        val = tts.get(key)
        if type(val) is not int or not bounds[0] <= val <= bounds[1]:
            raise ValueError("tts.{} 必须是 {}..{} 的整数".format(key, *bounds))
    for key in ("cfg_value", "temperature"):
        val = tts.get(key)
        if type(val) not in (int, float) or not 0 <= val <= 20:
            raise ValueError("tts.{} 必须是有限的 0..20 数值".format(key))
    if tts["segment_target_chars"] > tts["segment_max_chars"]:
        raise ValueError("segment_target_chars 不能大于 segment_max_chars")
    return path, data


def reference_path(show_path, speaker):
    ref = Path(speaker["reference"]).expanduser()
    return (show_path.parent / ref).resolve() if not ref.is_absolute() else ref.resolve()


def wav_info(value, reference=False):
    source = io.BytesIO(value) if isinstance(value, bytes) else str(value)
    with wave.open(source, "rb") as wav:
        info = {"channels": wav.getnchannels(), "sample_width": wav.getsampwidth(),
                "sample_rate": wav.getframerate(), "frames": wav.getnframes()}
        payload = wav.readframes(info["frames"])
        if (wav.getcomptype() != "NONE" or info["channels"] != 1
                or info["sample_width"] != 2 or info["frames"] <= 0):
            raise ValueError("音频必须非空、单声道、16-bit PCM WAV")
        if len(payload) != info["frames"] * 2:
            raise ValueError("WAV 数据长度不完整")
        if not reference and info["sample_rate"] != 48000:
            raise ValueError("生成音频必须为 48 kHz WAV")
        info["seconds"] = info["frames"] / info["sample_rate"]
        return info


def split_text(text, target=50, maximum=80):
    """Keep punctuation; only split on linguistic boundaries, never drop a suffix."""
    text = text.strip()
    if not text:
        raise ValueError("口播文本为空")
    sentences = re.findall(r".+?(?:[。！？!?；;]+|$)", text, flags=re.S)
    pieces = []
    for sentence in sentences:
        sentence = sentence.strip()
        while len(sentence) > maximum:
            candidates = [m.end() for m in re.finditer(r"[，、：:]|(?<!\d),(?!\d)|\s+", sentence[:maximum])]
            candidates = [n for n in candidates if n >= maximum // 3]
            if not candidates:
                raise ValueError("长句缺少自然断点，请先改写：" + sentence[:35])
            end = candidates[-1]
            pieces.append(sentence[:end].strip())
            sentence = sentence[end:].strip()
        if sentence:
            pieces.append(sentence)
    result = []
    for piece in pieces:
        if result and len(result[-1]) + len(piece) <= target:
            result[-1] += piece
        else:
            result.append(piece)
    if re.sub(r"\s+", "", "".join(result)) != re.sub(r"\s+", "", text):
        raise ValueError("分段后文本与原文不一致")
    return result


def make_plan(episode, show):
    order = [chapter["id"] for chapter in episode["chapters"]]
    used = [turn["chapter_id"] for turn in episode["turns"]]
    collapsed = [ch for i, ch in enumerate(used) if i == 0 or ch != used[i - 1]]
    if collapsed != order:
        raise ValueError("章节须按 chapters 顺序连续出现，且不能回到已结束章节")
    config = show["tts"]
    result = []
    for turn_index, turn in enumerate(episode["turns"]):
        chunks = split_text(turn.get("tts_text", turn["text"]),
                            config["segment_target_chars"], config["segment_max_chars"])
        next_turn = episode["turns"][turn_index + 1] if turn_index + 1 < len(episode["turns"]) else None
        for index, text in enumerate(chunks):
            pause = config["within_turn_pause_ms"]
            if index == len(chunks) - 1:
                default = config["chapter_pause_ms"] if next_turn and next_turn["chapter_id"] != turn["chapter_id"] else config["turn_pause_ms"]
                pause = turn.get("pause_after_ms", default) if next_turn else 0
            result.append({"id": "{}-{:03d}".format(turn["id"], index + 1),
                           "turn_id": turn["id"], "speaker": turn["speaker"],
                           "chapter_id": turn["chapter_id"], "text": text,
                           "pause_after_ms": pause})
    return result


def engine_identity():
    install = Path.home() / ".local/share/voxcpm/manifest.json"
    if install.is_file():
        return {"installation_manifest_sha256": file_hash(install), "installation": read_json(install)}
    binary = voxcpm()
    return {"launcher": binary, "launcher_sha256": file_hash(binary) if binary else None}


def local_endpoint(value):
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost") or parsed.path not in ("", "/") or parsed.username or parsed.query or parsed.fragment:
        raise ValueError("只支持 http://127.0.0.1:端口 的本机 TTS 服务")
    return value.rstrip("/")


def server_ready(endpoint):
    try:
        with OPENER.open(endpoint + "/v1/audio/speech/models", timeout=2) as response:
            return "voxcpm" in response.read(65536).decode().lower()
    except (OSError, urllib.error.URLError, UnicodeError):
        return False


@contextlib.contextmanager
def service(endpoint, log_dir):
    endpoint = local_endpoint(endpoint)
    if server_ready(endpoint):
        yield endpoint
        return
    binary = voxcpm()
    if not binary:
        raise ValueError("未找到 voxcpm；请检查本机既有安装")
    port = urllib.parse.urlparse(endpoint).port or 80
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / "voxcpm-server.log").open("ab") as log:
        process = subprocess.Popen([binary, "serve", "--port", str(port)],
                                   stdout=log, stderr=log, start_new_session=True)
        try:
            deadline = time.monotonic() + 180
            while not server_ready(endpoint):
                if process.poll() is not None:
                    raise RuntimeError("VoxCPM2 启动失败；查看 " + str(log_dir / "voxcpm-server.log"))
                if time.monotonic() > deadline:
                    raise RuntimeError("VoxCPM2 启动超时；查看服务日志")
                time.sleep(0.5)
            yield endpoint
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()


def synthesize(endpoint, text, speaker, config, reference=None):
    payload = {key: config[key] for key in GEN_KEYS}
    payload.update({"model": "voxcpm2", "input": "({}){}".format(speaker["style"], text),
                    "response_format": "wav"})
    if reference is not None:
        payload["reference_audio"] = base64.b64encode(Path(reference).read_bytes()).decode("ascii")
    request = urllib.request.Request(endpoint + "/v1/audio/speech", data=canonical(payload),
                                     headers={"Content-Type": "application/json"}, method="POST")
    last_error = None
    for attempt in range(config["retries"] + 1):
        try:
            with OPENER.open(request, timeout=config["request_timeout_seconds"]) as response:
                result = response.read()
            wav_info(result)
            return result
        except (OSError, ValueError, EOFError, wave.Error, urllib.error.URLError) as exc:
            last_error = exc
            if attempt < config["retries"]:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError("TTS 片段生成失败：{}".format(last_error))


def safe_segment(root, filename):
    result = (Path(root) / filename).resolve()
    if not result.is_relative_to(Path(root).resolve()):
        raise ValueError("片段路径越出输出目录")
    return result


def assemble(root, segments, output):
    fd, temporary = tempfile.mkstemp(prefix=".assembly-", suffix=".wav", dir=str(Path(output).parent))
    os.close(fd)
    try:
        with wave.open(temporary, "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(48000)
            for segment in segments:
                path = safe_segment(root, segment["file"])
                if file_hash(path) != segment["sha256"]:
                    raise ValueError("片段哈希不匹配：" + segment["id"])
                wav_info(path)
                with wave.open(str(path), "rb") as source:
                    target.writeframes(source.readframes(source.getnframes()))
                target.writeframes(b"\x00\x00" * (48000 * segment["pause_after_ms"] // 1000))
        wav_info(Path(temporary))
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def fingerprint(manifest):
    return digest(canonical({key: manifest[key] for key in ("inputs", "segments")}))


def review_record(manifest, old=None, redone=()):
    old = old or {}
    same = old.get("manifest_fingerprint") == manifest["fingerprint"] and not redone
    prior = {item["id"]: item for item in old.get("segments", [])}
    result = {"schema_version": 1, "manifest_fingerprint": manifest["fingerprint"],
              "status": old.get("status", "pending") if same else "pending",
              "reviewer": old.get("reviewer", "") if same else "",
              "reviewed_at": old.get("reviewed_at", "") if same else "",
              "notes": old.get("notes", "") if same else "请实际逐段及整集回听后填写；文件检查不能代替内容检查。",
              "segments": []}
    for segment in manifest["segments"]:
        prev = prior.get(segment["id"], {})
        reusable = prev.get("sha256") == segment["sha256"] and segment["id"] not in redone
        result["segments"].append({"id": segment["id"], "sha256": segment["sha256"],
                                  "status": prev.get("status", "pending") if reusable else "pending",
                                  "notes": prev.get("notes", "") if reusable else ""})
    return result


def render(args):
    output = Path(args.output_dir).expanduser().resolve()
    managed_directory(output)
    with directory_lock(output):
        return _render(args)


def _render(args):
    source = Path(args.episode).expanduser().resolve()
    episode, warnings = load_episode(source, require_reviews=True)
    show_path, show = load_show(args.show)
    planned = make_plan(episode, show)
    redo = set(args.redo or [])
    if redo - {s["id"] for s in planned}:
        raise ValueError("--redo 包含不存在的片段 ID")
    refs = {role: reference_path(show_path, value) for role, value in show["speakers"].items()}
    for value in refs.values():
        wav_info(value, reference=True)
    inputs = {"episode_sha256": file_hash(source), "show_sha256": file_hash(show_path),
              "reference_sha256": {role: file_hash(path) for role, path in refs.items()},
              "engine": engine_identity()}
    output = Path(args.output_dir).expanduser().resolve()
    managed_directory(output)
    review_path = output / "audio-review.json"
    old_review = read_json(review_path) if review_path.is_file() else None
    invalidation_path = output / "invalidated-segments.json"
    invalidated = set(read_json(invalidation_path)) if invalidation_path.is_file() else set()
    invalidated.intersection_update({segment["id"] for segment in planned})
    invalidated.update(redo)
    forced_redo = set(invalidated)
    write_json(invalidation_path, sorted(invalidated))
    if old_review and forced_redo:
        old_review.update(status="pending", reviewer="", reviewed_at="", notes="有片段要求重做；请回听本次结果。")
        for check in old_review.get("segments", []):
            if check.get("id") in forced_redo:
                check.update(status="pending", notes="已要求重做，旧片段与听审不能继续使用。")
        write_json(review_path, old_review)
    manifest = {"schema_version": 1, "complete": False, "created_at": now(),
                "source_path": str(source), "show_path": str(show_path), "inputs": inputs,
                "warnings": warnings, "segments": []}
    (output / "draft.wav").unlink(missing_ok=True)
    write_json(output / "render-manifest.json", manifest)
    atomic_bytes(output / "episode.json", source.read_bytes())
    names = {role: value["name"] for role, value in show["speakers"].items()}
    export_text(episode, output / ("script-" + inputs["episode_sha256"][:12]), speaker_names=names)
    with contextlib.ExitStack() as stack:
        started = False
        for segment in planned:
            role = segment["speaker"]
            signature = {"text": segment["text"], "speaker": show["speakers"][role],
                         "reference_sha256": inputs["reference_sha256"][role],
                         "parameters": {key: show["tts"][key] for key in GEN_KEYS}, "engine": inputs["engine"]}
            cache_key = digest(canonical(signature))
            relative = "segments/{}-{}.wav".format(segment["id"], cache_key[:20])
            path = safe_segment(output, relative)
            usable = False
            if path.is_file() and segment["id"] not in forced_redo:
                try:
                    wav_info(path)
                    usable = True
                except (ValueError, wave.Error, EOFError):
                    pass
            try:
                if not usable:
                    if not started:
                        stack.enter_context(service(args.endpoint, output))
                        started = True
                    result = synthesize(args.endpoint, segment["text"], show["speakers"][role], show["tts"], refs[role])
                    atomic_bytes(path, result)
                    invalidated.discard(segment["id"])
                    write_json(invalidation_path, sorted(invalidated))
                info = wav_info(path)
                entry = dict(segment, file=relative, sha256=file_hash(path), cache_key=cache_key,
                             seconds=info["seconds"], status="generated")
                if info["seconds"] >= show["tts"]["max_steps"] * 0.16 * 0.9:
                    entry["warning"] = "接近生成上限，重点回听末尾是否截断"
                manifest["segments"].append(entry)
                write_json(output / "render-manifest.json", manifest)
                print(json.dumps({"segment": segment["id"], "cached": usable, "seconds": info["seconds"]}, ensure_ascii=False), flush=True)
            except Exception as exc:
                manifest["failure"] = {"segment": segment["id"], "message": str(exc)}
                write_json(output / "render-manifest.json", manifest)
                raise
    manifest["complete"] = True
    manifest["fingerprint"] = fingerprint(manifest)
    assemble(output, manifest["segments"], output / "draft.wav")
    manifest["seconds"] = wav_info(output / "draft.wav")["seconds"]
    write_json(output / "render-manifest.json", manifest)
    write_json(review_path, review_record(manifest, old_review, forced_redo))
    return {"draft": str(output / "draft.wav"), "seconds": manifest["seconds"],
            "audio_review": str(review_path), "status": "pending_audio_review"}


def timestamp(seconds):
    seconds = int(seconds)
    return "{:02d}:{:02d}".format(seconds // 60, seconds % 60)


def finalize(args):
    root = Path(args.render_dir).expanduser().resolve()
    marker = root / ".podcast-render.json"
    if not marker.is_file() or read_json(marker) != {"managed_by": "podcast-renderer", "schema_version": 1}:
        raise ValueError("这不是本工具的生成目录")
    with directory_lock(root):
        return _finalize(args)


def _finalize(args):
    root = Path(args.render_dir).expanduser().resolve()
    invalidation_path = root / "invalidated-segments.json"
    if invalidation_path.is_file() and read_json(invalidation_path):
        raise ValueError("仍有待重做片段，请恢复 render 后再定稿")
    manifest = read_json(root / "render-manifest.json")
    if not manifest.get("complete") or manifest.get("fingerprint") != fingerprint(manifest):
        raise ValueError("生成记录未完成或已改变，请重新 render")
    source, show_path = Path(manifest["source_path"]), Path(manifest["show_path"])
    episode, _ = load_episode(source, require_reviews=True)
    _, show = load_show(show_path)
    current = {"episode_sha256": file_hash(source), "show_sha256": file_hash(show_path),
               "reference_sha256": {role: file_hash(reference_path(show_path, value)) for role, value in show["speakers"].items()},
               "engine": engine_identity()}
    if current != manifest["inputs"] or file_hash(root / "episode.json") != current["episode_sha256"]:
        raise ValueError("脚本、配置、声音或引擎已变化，请重新审稿和 render")
    expected = make_plan(episode, show)
    if len(expected) != len(manifest["segments"]):
        raise ValueError("片段数量与当前脚本不符")
    for planned, actual in zip(expected, manifest["segments"]):
        if any(planned[key] != actual.get(key) for key in planned):
            raise ValueError("片段顺序或文本与脚本不符")
    review = read_json(root / "audio-review.json")
    if review.get("manifest_fingerprint") != manifest["fingerprint"] or review.get("status") != "passed":
        raise ValueError("当前版本尚未完成整体回听")
    for key in ("reviewer", "reviewed_at", "notes"):
        if not isinstance(review.get(key), str) or not review[key].strip():
            raise ValueError("整体听审缺少 " + key)
    try:
        value = review["reviewed_at"]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            dt.date.fromisoformat(value)
        elif "T" in value:
            dt.datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
        else:
            raise ValueError("Invalid date")
    except ValueError:
        raise ValueError("听审日期格式应为 ISO 日期或日期时间")
    checks = review.get("segments", [])
    if len(checks) != len(expected) or len({x.get("id") for x in checks}) != len(expected):
        raise ValueError("逐段听审记录缺失或重复")
    checked = {x["id"]: x for x in checks}
    for segment in manifest["segments"]:
        item = checked.get(segment["id"], {})
        if item.get("status") != "passed" or item.get("sha256") != segment["sha256"]:
            raise ValueError("片段尚未完成当前版本回听：" + segment["id"])
        if file_hash(safe_segment(root, segment["file"])) != segment["sha256"]:
            raise ValueError("片段文件已改变：" + segment["id"])
    delivery = root / ("delivery-" + manifest["fingerprint"][:12])
    if delivery.exists():
        raise ValueError("该版本定稿目录已存在；请直接使用，修改后重新 render")
    staging = Path(tempfile.mkdtemp(prefix=".delivery-", dir=str(root)))
    try:
        assemble(root, manifest["segments"], staging / "episode.wav")
        export_text(episode, staging, speaker_names={role: value["name"] for role, value in show["speakers"].items()})
        atomic_bytes(staging / "episode.json", source.read_bytes())
        write_json(staging / "render-manifest.json", manifest)
        write_json(staging / "audio-review.json", review)
        chapter_times, offset = [], 0.0
        for segment in manifest["segments"]:
            if not chapter_times or chapter_times[-1][0] != segment["chapter_id"]:
                chapter_times.append((segment["chapter_id"], offset))
            offset += segment["seconds"] + segment["pause_after_ms"] / 1000
        titles = {ch["id"]: ch["title"] for ch in episode["chapters"]}
        with (staging / "show-notes.md").open("a", encoding="utf-8") as stream:
            stream.write("\n## 实测章节时间\n\n")
            for chapter, seconds in chapter_times:
                stream.write("- {} {}\n".format(timestamp(seconds), titles[chapter]))
            stream.write("\n实测总时长：{} 秒。\n".format(round(offset, 3)))
        encoder = ffmpeg()
        formats = ["wav"]
        if encoder:
            subprocess.run([encoder, "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(staging / "episode.wav"),
                            "-map_metadata", "-1", "-codec:a", "libmp3lame", "-b:a", "128k", str(staging / "episode.mp3")],
                           check=True, capture_output=True, timeout=180)
            if not (staging / "episode.mp3").stat().st_size:
                raise ValueError("MP3 编码输出为空")
            formats.append("mp3")
        report = {"status": "complete", "seconds": round(offset, 3), "formats": formats,
                  "mp3_note": "已编码" if encoder else "未发现 FFmpeg，交付无损 WAV；未安装依赖。"}
        write_json(staging / "delivery.json", report)
        os.replace(staging, delivery)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return dict(report, delivery=str(delivery))


def audition(args):
    _, show = load_show(args.show)
    speaker = show["speakers"][args.speaker]
    text = args.text or speaker["audition_text"]
    if len(text) > show["tts"]["segment_max_chars"]:
        raise ValueError("试音文本过长，请使用一段短文")
    output = Path(args.output).expanduser().resolve()
    if output.exists():
        raise ValueError("试音输出已存在，请换文件名")
    output.parent.mkdir(parents=True, exist_ok=True)
    config = dict(show["tts"])
    if args.seed is not None:
        config["seed"] = args.seed
    with service(args.endpoint, output.parent):
        result = synthesize(args.endpoint, text, speaker, config)
    atomic_bytes(output, result)
    return {"audio": str(output), "speaker": speaker["name"], "seconds": wav_info(result)["seconds"],
            "status": "pending_listening", "text": text, "seed": config["seed"]}


def doctor(args):
    show_path, show = load_show(args.show)
    result = {"voxcpm": voxcpm(), "ffmpeg": ffmpeg(), "afconvert": executable("afconvert"), "references": {}}
    for role, speaker in show["speakers"].items():
        path = reference_path(show_path, speaker)
        try:
            result["references"][role] = dict(wav_info(path, reference=True), path=str(path), sha256=file_hash(path))
        except (OSError, ValueError, wave.Error, EOFError) as exc:
            result["references"][role] = {"path": str(path), "issue": str(exc)}
    if result["voxcpm"]:
        check = subprocess.run([result["voxcpm"], "doctor"], capture_output=True, text=True)
        result["installation_ok"] = check.returncode == 0
        result["installation_details"] = check.stdout + check.stderr
    else:
        result["installation_ok"] = False
    result["ready_for_render"] = result["installation_ok"] and all("issue" not in x for x in result["references"].values())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show", default=str(DEFAULT_SHOW), help="节目配置，可在子命令前指定")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8808", type=local_endpoint)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    p = sub.add_parser("plan")
    p.add_argument("episode")
    p = sub.add_parser("render")
    p.add_argument("episode")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--redo", action="append", default=[])
    p = sub.add_parser("finalize")
    p.add_argument("render_dir")
    p = sub.add_parser("audition")
    p.add_argument("--speaker", choices=("male", "female"), required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--text")
    p.add_argument("--seed", type=int)
    args = parser.parse_args()
    try:
        if args.command == "plan":
            episode, warnings = load_episode(args.episode)
            _, show = load_show(args.show)
            result = {"warnings": warnings, "segments": make_plan(episode, show), "status": "plan_only"}
        else:
            result = {"render": render, "finalize": finalize, "audition": audition, "doctor": doctor}[args.command](args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, RuntimeError, wave.Error, EOFError, subprocess.SubprocessError, KeyError, TypeError) as exc:
        print("错误：{}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
