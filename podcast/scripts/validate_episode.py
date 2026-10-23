#!/usr/bin/env python3
"""Validate and export a health-podcast episode using only the standard library.

Validation checks structure, references, and recorded review status. It cannot
establish medical accuracy or the semantic equivalence of TTS normalization.
"""

import argparse
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlsplit


ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
SPEAKER_NAMES = {"male": "阿衡", "female": "知夏"}
REVIEW_NAMES = {"evidence": "证据", "editorial": "编辑"}


def review_content_sha256(data: Any) -> str:
    """Hash all episode content except top-level review metadata.

    Reviewers record this digest only after reviewing this exact content. Any
    edit outside ``reviews`` requires a fresh review and an updated digest.
    """
    data = _object(data, "episode")
    payload = {key: value for key, value in data.items() if key != "reviews"}
    try:
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    except (TypeError, ValueError, UnicodeError) as error:
        raise ValueError("无法计算审稿内容 SHA256: {}".format(error)) from error


def _fail(field: str, message: str) -> None:
    raise ValueError("{}: {}".format(field, message))


def _object(value: Any, field: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        _fail(field, "必须是对象")
    return value


def _string(value: Any, field: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        _fail(field, "必须是字符串")
    if not allow_empty and not value.strip():
        _fail(field, "不能为空")
    return value


def _list(value: Any, field: str, nonempty: bool = False) -> List[Any]:
    if not isinstance(value, list):
        _fail(field, "必须是列表")
    if nonempty and not value:
        _fail(field, "不能为空")
    return value


def _identifier(value: Any, field: str) -> str:
    value = _string(value, field)
    if not ID_PATTERN.fullmatch(value):
        _fail(field, "必须匹配 [A-Za-z0-9][A-Za-z0-9_-]{0,63}")
    return value


def _collection(data: Dict[str, Any], key: str, nonempty: bool = False) -> Tuple[List[Any], set]:
    items = _list(data.get(key), key, nonempty=nonempty)
    identifiers = set()
    for index, item in enumerate(items):
        field = "{}[{}]".format(key, index)
        item = _object(item, field)
        identifier = _identifier(item.get("id"), field + ".id")
        if identifier in identifiers:
            _fail(field + ".id", "重复 ID {}".format(identifier))
        identifiers.add(identifier)
    return items, identifiers


def _references(value: Any, field: str, known: set, nonempty: bool = False) -> List[str]:
    values = _list(value, field, nonempty=nonempty)
    seen = set()
    for index, reference in enumerate(values):
        reference = _identifier(reference, "{}[{}]".format(field, index))
        if reference not in known:
            _fail(field, "引用不存在的 ID {}".format(reference))
        if reference in seen:
            _fail(field, "重复引用 {}".format(reference))
        seen.add(reference)
    return values


def _iso_date(value: Any, field: str) -> None:
    value = _string(value, field)
    if not DATE_PATTERN.fullmatch(value):
        _fail(field, "必须是 YYYY-MM-DD 日期")
    try:
        date.fromisoformat(value)
    except ValueError:
        _fail(field, "不是有效日期")


def _review_time(value: str, field: str) -> None:
    """Accept a calendar date or an ISO 8601 datetime for review metadata."""
    if DATE_PATTERN.fullmatch(value):
        _iso_date(value, field)
        return
    if "T" not in value:
        _fail(field, "必须是 ISO 日期或带 T 的 ISO 日期时间")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        _fail(field, "不是有效 ISO 日期时间")


def validate_episode(data: Any, require_reviews: bool = False) -> List[str]:
    """Return nonfatal warnings, or raise ValueError for an invalid episode.

    ``require_reviews=True`` additionally blocks rendering until both recorded
    reviews pass. A passed status is metadata, not proof of medical correctness.
    Once both pass, all claims and chapters must be used and both hosts must speak.
    """
    data = _object(data, "episode")
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        _fail("schema_version", "必须是整数 1")
    _string(data.get("title"), "title")
    if data.get("language") != "zh-CN":
        _fail("language", "必须是 zh-CN")
    if "target_minutes" in data:
        value = data["target_minutes"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            _fail("target_minutes", "必须是有限的正数")

    warnings = ["自动校验不判断医学真伪；审核 passed 仅表示已记录审稿结果。"]
    sources, source_ids = _collection(data, "sources")
    claims, claim_ids = _collection(data, "claims")
    chapters, chapter_ids = _collection(data, "chapters", nonempty=True)
    turns, _ = _collection(data, "turns", nonempty=True)
    for key, items in (("sources", sources), ("claims", claims)):
        if not items:
            message = "{} 为空；正式健康节目必须登记来源和关键结论。".format(key)
            if require_reviews:
                _fail(key, message)
            warnings.append(message)

    urls = {}
    for index, source in enumerate(sources):
        field = "sources[{}]".format(index)
        _string(source.get("title"), field + ".title")
        _string(source.get("type"), field + ".type")
        url = _string(source.get("url"), field + ".url")
        try:
            parts = urlsplit(url)
            valid_url = parts.scheme in ("http", "https") and bool(parts.netloc) and bool(parts.hostname)
        except ValueError:
            valid_url = False
        if not valid_url or any(character.isspace() or ord(character) < 32 for character in url):
            _fail(field + ".url", "必须是有效的 HTTP(S) URL，且不含空白或控制字符")
        if url in urls:
            warnings.append("来源 {} 与 {} 使用相同 URL，不能作为独立证据计数。".format(source["id"], urls[url]))
        else:
            urls[url] = source["id"]
        _iso_date(source.get("accessed_at"), field + ".accessed_at")

    for index, claim in enumerate(claims):
        field = "claims[{}]".format(index)
        for name in ("text", "population", "outcome", "limitations", "applicability", "certainty"):
            _string(claim.get(name), field + "." + name)
        _references(claim.get("source_ids"), field + ".source_ids", source_ids, nonempty=True)

    for index, chapter in enumerate(chapters):
        _string(chapter.get("title"), "chapters[{}].title".format(index))

    used_claims = set()
    used_chapters = set()
    speakers = set()
    chapter_sequence = []
    for index, turn in enumerate(turns):
        field = "turns[{}]".format(index)
        speaker = turn.get("speaker")
        if speaker not in ("male", "female"):
            _fail(field + ".speaker", "必须是 male 或 female")
        speakers.add(speaker)
        chapter_id = _identifier(turn.get("chapter_id"), field + ".chapter_id")
        if chapter_id not in chapter_ids:
            _fail(field + ".chapter_id", "引用不存在的章节 {}".format(chapter_id))
        used_chapters.add(chapter_id)
        if not chapter_sequence or chapter_sequence[-1] != chapter_id:
            chapter_sequence.append(chapter_id)
        _string(turn.get("text"), field + ".text")
        if "tts_text" in turn:
            _string(turn["tts_text"], field + ".tts_text")
            warnings.append("回合 {} 使用 tts_text；须核对数字、单位、药名与否定词，自动比对不能证明语义一致。".format(turn["id"]))
        used_claims.update(_references(turn.get("claim_ids"), field + ".claim_ids", claim_ids))
        if "pause_after_ms" in turn:
            pause = turn["pause_after_ms"]
            if type(pause) is not int or not 0 <= pause <= 2000:
                _fail(field + ".pause_after_ms", "必须是 0 到 2000 的整数")

    reviews = _object(data.get("reviews"), "reviews")
    content_digest = review_content_sha256(data)
    pending = []
    for key, name in REVIEW_NAMES.items():
        field = "reviews." + key
        review = _object(reviews.get(key), field)
        status = review.get("status")
        if status not in ("pending", "passed"):
            _fail(field + ".status", "必须是 pending 或 passed")
        reviewer = _string(review.get("reviewer"), field + ".reviewer", allow_empty=status == "pending")
        reviewed_at = _string(review.get("reviewed_at"), field + ".reviewed_at", allow_empty=status == "pending")
        _string(review.get("notes"), field + ".notes", allow_empty=status == "pending")
        if reviewed_at.strip():
            _review_time(reviewed_at, field + ".reviewed_at")
        if status == "pending":
            pending.append(name)
            if "content_sha256" in review:
                _string(review["content_sha256"], field + ".content_sha256", allow_empty=True)
        else:
            bound_digest = _string(review.get("content_sha256"), field + ".content_sha256")
            if bound_digest != content_digest:
                _fail(field + ".content_sha256", "审稿所绑定的内容与当前稿件不一致，须重新审稿并记录当前 SHA256")

    if pending:
        message = "{}审稿尚未通过；不可合成或交付音频。".format("、".join(pending))
        if require_reviews:
            _fail("reviews", message)
        warnings.append(message)

    missing_claims = sorted(claim_ids - used_claims)
    missing_chapters = sorted(chapter_ids - used_chapters)
    missing_speakers = sorted({"male", "female"} - speakers)
    completeness = []
    if missing_claims:
        completeness.append("未被回合引用的结论：{}".format(", ".join(missing_claims)))
    if missing_chapters:
        completeness.append("未使用的章节：{}".format(", ".join(missing_chapters)))
    if missing_speakers:
        completeness.append("缺少主持人发言：{}".format(", ".join(missing_speakers)))
    expected_sequence = [chapter["id"] for chapter in chapters]
    if chapter_sequence != expected_sequence:
        completeness.append("章节出现顺序必须与 chapters 一致且每章连续；当前为 {}，应为 {}".format(
            " → ".join(chapter_sequence), " → ".join(expected_sequence)))
    if completeness:
        message = "；".join(completeness)
        if not pending:
            _fail("episode", message)
        warnings.append("草稿尚不完整：" + message)
    return warnings


def load_episode(path: Union[str, Path], require_reviews: bool = False) -> Tuple[Dict[str, Any], List[str]]:
    """Load UTF-8 JSON, preserving a useful ValueError-based public interface."""
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("无法读取 episode JSON {}: {}".format(path, error)) from error
    return data, validate_episode(data, require_reviews=require_reviews)


def _inline(value: str) -> str:
    return " ".join(value.splitlines()).replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def _source_link(source: Dict[str, Any]) -> str:
    url = source["url"].replace("<", "%3C").replace(">", "%3E")
    return "[{}](<{}>)".format(_inline(source["title"]), url)


def export_text(data: Any, output_dir: Union[str, Path],
                speaker_names: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Export text and evidence; refuse to overwrite different existing content.

    Returns a mapping of output names to absolute file paths. No timestamps are
    inferred: chapter timing belongs to the renderer after actual synthesis.
    """
    warnings = validate_episode(data)
    names = dict(SPEAKER_NAMES)
    if speaker_names is not None:
        _object(speaker_names, "speaker_names")
        for speaker in names:
            if speaker in speaker_names:
                names[speaker] = _string(speaker_names[speaker], "speaker_names." + speaker)
    chapter_map = {chapter["id"]: chapter for chapter in data["chapters"]}
    source_map = {source["id"]: source for source in data["sources"]}
    pending = any(data["reviews"][key]["status"] != "passed" for key in REVIEW_NAMES)
    notice = "制作状态：{}。审稿记录不构成医学正确性的自动证明。".format("草稿，尚不可合成音频" if pending else "已记录证据与编辑审稿通过")
    transcript = ["# " + _inline(data["title"]), "", notice, ""]
    last_chapter = None
    for turn in data["turns"]:
        if turn["chapter_id"] != last_chapter:
            transcript.extend(["## " + _inline(chapter_map[turn["chapter_id"]]["title"]), ""])
            last_chapter = turn["chapter_id"]
        transcript.extend(["**{}**：{}".format(_inline(names[turn["speaker"]]), turn["text"]), ""])

    notes = ["# " + _inline(data["title"]), "", notice, "", "## 章节", "", "以下按脚本章节列出；尚未根据实际生成音频标注时间。", ""]
    notes.extend("{}. {}".format(index + 1, _inline(chapter["title"])) for index, chapter in enumerate(data["chapters"]))
    notes.extend(["", "## 主要结论、局限与适用范围", ""])
    if not data["claims"]:
        notes.extend(["本稿尚未登记关键结论。", ""])
    for claim in data["claims"]:
        notes.extend([
            "### {}：{}".format(claim["id"], _inline(claim["text"])), "",
            "- 研究人群：" + _inline(claim["population"]),
            "- 观察结果：" + _inline(claim["outcome"]),
            "- 证据说明：" + _inline(claim["certainty"]),
            "- 局限：" + _inline(claim["limitations"]),
            "- 适用范围：" + _inline(claim["applicability"]),
            "- 来源：" + "；".join(_source_link(source_map[identifier]) for identifier in claim["source_ids"]), "",
        ])
    notes.extend(["## 来源", ""])
    for source in data["sources"]:
        notes.append("- {}：{}；类型：{}；查阅日期：{}。".format(source["id"], _source_link(source), _inline(source["type"]), source["accessed_at"]))
    notes.extend(["", "## 审稿记录", ""])
    for key, name in REVIEW_NAMES.items():
        review = data["reviews"][key]
        notes.append("- {}：{}；审稿者：{}；日期：{}；备注：{}。".format(name, review["status"], _inline(review["reviewer"]) or "待登记", review["reviewed_at"] or "待登记", _inline(review["notes"]) or "无"))
    evidence = {
        "schema_version": data["schema_version"],
        "title": data["title"],
        "language": data["language"],
        "sources": data["sources"],
        "claims": data["claims"],
        "reviews": data["reviews"],
        "review_content_sha256": review_content_sha256(data),
        "turn_claim_map": [{"turn_id": turn["id"], "claim_ids": turn["claim_ids"]} for turn in data["turns"]],
        "tts_normalizations": [{"turn_id": turn["id"], "text": turn["text"], "tts_text": turn["tts_text"], "semantic_equivalence": "requires_review"} for turn in data["turns"] if "tts_text" in turn],
        "warnings": warnings,
    }
    payloads = {
        "transcript.md": "\n".join(transcript).rstrip() + "\n",
        "show-notes.md": "\n".join(notes).rstrip() + "\n",
        "evidence.json": json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    }
    directory = Path(output_dir).expanduser().absolute()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        for name, content in payloads.items():
            target = directory / name
            if target.is_symlink():
                _fail(str(target), "拒绝写入符号链接")
            if target.exists() and (not target.is_file() or target.read_text(encoding="utf-8") != content):
                _fail(str(target), "已有内容不同，请使用新的导出目录")
        for name, content in payloads.items():
            target = directory / name
            try:
                with target.open("x", encoding="utf-8", newline="\n") as handle:
                    handle.write(content)
            except FileExistsError:
                if target.is_symlink() or target.read_text(encoding="utf-8") != content:
                    _fail(str(target), "已有内容不同，请使用新的导出目录")
    except (OSError, UnicodeError) as error:
        raise ValueError("导出失败 {}: {}".format(directory, error)) from error
    return {name: str(directory / name) for name in payloads}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode", type=Path, help="episode JSON 文件")
    parser.add_argument("--for-render", action="store_true", help="要求证据与编辑审稿均通过")
    parser.add_argument("--export-dir", type=Path, help="导出文字稿、节目说明和结论台账")
    arguments = parser.parse_args()
    try:
        data, warnings = load_episode(arguments.episode, require_reviews=arguments.for_render)
        exports = export_text(data, arguments.export_dir) if arguments.export_dir else {}
        print(json.dumps({"valid": True, "title": data["title"], "for_render": arguments.for_render, "review_content_sha256": review_content_sha256(data), "counts": {key: len(data[key]) for key in ("sources", "claims", "chapters", "turns")}, "warnings": warnings, "exports": exports}, ensure_ascii=False, indent=2))
        return 0
    except ValueError as error:
        print("校验失败：{}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
