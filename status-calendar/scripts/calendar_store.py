"""Local storage shared by the web calendar and chat edits."""

from contextlib import contextmanager
from copy import deepcopy
from datetime import date
import json
import os
from pathlib import Path
import re
import tempfile


BODY_PARTS = (
    ("🐻", "胸部"), ("🪽", "背部"), ("🏋️", "肩部"), ("💪", "手臂"),
    ("🧘", "腹部"), ("🦵", "腿部"), ("🍑", "臀部"),
)


def body_parts_for(states):
    """Read the calendar's body-part legend; older calendars have no saved legend."""
    default = [list(part) for part in BODY_PARTS]
    for state in states or ():
        if state.get("id") == "short-gym":
            return state.get("bodyParts", default)
    return default


def default_states():
    return [
        {"id": "short-gym", "kind": "gym", "label": "力量训练不足 1 小时", "color": "#BFDFF5",
         "emoji": "", "bodyParts": body_parts_for(None)},
        {"id": "long-gym", "kind": "gym", "label": "力量训练 ≥ 1 小时", "color": "#285888", "emoji": ""},
        {"id": "short-run", "kind": "run", "label": "跑步不足 5 公里或其他有氧", "color": "#BFE4AC", "emoji": ""},
        {"id": "mid-run", "kind": "run", "label": "跑步 5 至 10 公里（含两端）", "color": "#286443", "emoji": ""},
        {"id": "over-ten-run", "kind": "run", "label": "跑步 > 10 公里", "color": "#123C2C", "emoji": ""},
    ]


def workout_states_for(snapshot):
    """Apply the five workout bands, retaining custom states and referenced legacy ranges."""
    updated = default_states()
    expected_kinds = {state["id"]: state["kind"] for state in updated}
    used = {entry["stateId"] for entries in snapshot["days"].values() for entry in entries}
    for state in snapshot["states"] or ():
        ident = state["id"]
        if ident in expected_kinds:
            if state["kind"] != expected_kinds[ident]:
                raise ValueError("已有自定义状态与运动档位的标识重复，请先检查状态配置。")
        elif ident == "long-run" and state["kind"] == "run":
            if ident in used:
                hint = "（旧记录，距离未细分）"
                label = state["label"].removesuffix(hint) + hint
                updated.append(dict(state, label=label, archived=True))
        else:
            updated.append(deepcopy(state))
    return updated


def data_directory():
    data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return Path(os.environ.get("STATUS_CALENDAR_DATA_DIR") or data_home / "status-calendar").expanduser().resolve()


def encode_json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")


def validate_date(day_key):
    try:
        if isinstance(day_key, str) and date.fromisoformat(day_key).isoformat() == day_key:
            return
    except ValueError:
        pass
    raise ValueError("每日记录需要使用有效的 YYYY-MM-DD 日期。")


def _validate_legend(parts):
    if not isinstance(parts, list) or not parts:
        raise ValueError("请提供锻炼部位图例。")
    for part in parts:
        if (not isinstance(part, list) or len(part) != 2
                or not all(isinstance(item, str) and item.strip() for item in part)):
            raise ValueError("每个锻炼部位需要一个图标和名称。")
    if len({part[0] for part in parts}) != len(parts) or len({part[1] for part in parts}) != len(parts):
        raise ValueError("每个锻炼部位的图标和名称必须唯一。")


def _validate_record_parts(entry, state, allowed):
    parts = entry.get("parts")
    if (state["kind"] != "gym" or not isinstance(parts, list) or len(parts) > 3
            or not all(isinstance(icon, str) and icon in allowed for icon in parts)
            or len(parts) != len(set(parts)) or entry.get("emoji")):
        raise ValueError("力量训练每天可选最多 3 个不同的部位图标。")


def validate_day_edit(states, entries, previous_entries):
    """Check newly recorded workout choices while retaining historical entries as recorded."""
    by_id = {state["id"]: state for state in states}
    legend = body_parts_for(states)
    allowed = {part[0] for part in legend}
    selected = {"gym": [], "run": []}
    date_parts = set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("stateId"), str) or entry["stateId"] not in by_id:
            raise ValueError("每日记录引用了无效的状态。")
        state = by_id[entry["stateId"]]
        if "parts" in entry:
            _validate_record_parts(entry, state, allowed)
            date_parts.update(entry["parts"])
        if state.get("archived") and entry not in previous_entries:
            raise ValueError("旧运动档位只用于保留历史记录，请选择当前档位。")
        group = state["kind"]
        if group in selected:
            selected[group].append(entry)
        if "over-ten-run" in by_id and entry not in previous_entries:
            mark = entry.get("emoji")
            if not isinstance(mark, str):
                raise ValueError("每日记录引用了无效的图标。")
            if group == "gym" and mark and mark not in allowed:
                raise ValueError("请选择图例中的力量训练部位。")
            if group != "gym" and any(part.removesuffix("\ufe0f") in mark for part in allowed):
                raise ValueError("部位图标只能用于力量训练。")
    if len(date_parts) > 3:
        raise ValueError("每天最多可选 3 个锻炼部位。")
    if "over-ten-run" in by_id:
        for group, group_entries in selected.items():
            if len(group_entries) > 1:
                old = [item for item in previous_entries if by_id.get(item["stateId"], {}).get("kind") == group]
                if group_entries != old:
                    raise ValueError("每天每类运动请选择一个档位。")


def validate(snapshot):
    if not isinstance(snapshot, dict) or type(snapshot.get("revision")) is not int:
        raise ValueError("缺少配置版本，请刷新日历。")
    states = snapshot.get("states")
    days = snapshot.get("days")
    if not isinstance(states, list) or not isinstance(days, dict):
        raise ValueError("状态列表或每日记录格式有误。")
    by_id = {}
    for state in states:
        if not isinstance(state, dict) or not all(
            isinstance(state.get(key), str) for key in ("id", "label", "kind", "color", "emoji")
        ):
            raise ValueError("每个状态需要名称、颜色、图标和类型。")
        state_id = state["id"]
        if not state_id.strip() or state_id in by_id or not state["label"].strip():
            raise ValueError("请为每个状态设置名称和唯一标识。")
        if state["kind"] not in ("run", "gym", "custom") or not re.fullmatch(r"#[0-9a-fA-F]{6}", state["color"]):
            raise ValueError("状态类型或背景颜色有误。")
        if "bodyParts" in state:
            if state_id != "short-gym" or state["kind"] != "gym":
                raise ValueError("部位图例应保存在力量训练配置中。")
            _validate_legend(state["bodyParts"])
        by_id[state_id] = state
    allowed = {part[0] for part in body_parts_for(states)}
    for day_key, records in days.items():
        validate_date(day_key)
        if not isinstance(records, list):
            raise ValueError("每日记录需要使用状态列表。")
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("stateId"), str):
                raise ValueError("每日记录缺少状态。")
            if record["stateId"] not in by_id or not isinstance(record.get("emoji"), str):
                raise ValueError("每日记录引用了无效的状态或图标。")
            if "parts" in record:
                _validate_record_parts(record, by_id[record["stateId"]], allowed)


@contextmanager
def write_lock(data_dir):
    # Separate service ports can share a data directory. Lock a stable inode
    # because the calendar file itself is replaced on every successful write.
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (data_dir / "calendar.lock").open("a+b") as lock:
        if os.name == "nt":
            import msvcrt
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)
        yield  # Closing the file releases the lock on both platforms.


def read_calendar(data_dir):
    try:
        with (data_dir / "calendar.json").open(encoding="utf-8") as saved:
            snapshot = json.load(saved)
        validate(snapshot)
        return snapshot
    except FileNotFoundError:
        return {"revision": 0, "states": None, "days": {}}


def write_private_json(path, value):
    payload = encode_json(value)
    staging = tempfile.NamedTemporaryFile(dir=path.parent, delete=False)
    staging_path = Path(staging.name)
    try:
        with staging:
            staging.write(payload)
            staging.flush()
            os.fsync(staging.fileno())
        os.replace(staging_path, path)
    finally:
        staging_path.unlink(missing_ok=True)


def write_calendar(data_dir, snapshot):
    write_private_json(data_dir / "calendar.json", snapshot)


class Conflict(Exception):
    def __init__(self, revision):
        super().__init__("日历已更新，请重新读取后再保存。")
        self.revision = revision
