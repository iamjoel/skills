#!/usr/bin/env python3
"""Apply one UTF-8 JSON calendar edit from stdin."""

import argparse
from copy import deepcopy
import json
import sys

from calendar_backend import edit_active
from calendar_store import Conflict, data_directory, default_states, encode_json, validate, validate_date, validate_day_edit


def _validate_operation(op):
    if not isinstance(op, dict) or type(op.get("revision")) is not int or op["revision"] < 0:
        raise ValueError("请提供日历的当前修订号 revision。")
    op = op.copy()
    source = op.pop("source", "local")
    action = op.get("action")
    if action == "configure":
        if op.keys() != {"action", "revision", "states"} or not isinstance(op["states"], list):
            raise ValueError("配置操作需要提供 states 数组。")
    elif action == "day":
        if op.keys() != {"action", "revision", "date", "entries"} or not isinstance(op["entries"], list):
            raise ValueError("每日操作需要提供 date 和 entries 数组。")
        validate_date(op["date"])
    else:
        raise ValueError("action 只支持 configure 或 day。")
    return op, source


def _apply_changes(op, snapshot):
    if op["action"] == "configure":
        snapshot["states"] = op["states"]
    else:
        if snapshot["states"] is None:
            snapshot["states"] = default_states()
        validate_day_edit(snapshot["states"], op["entries"], snapshot["days"].get(op["date"], []))
        if op["entries"]:
            snapshot["days"][op["date"]] = op["entries"]
        else:
            snapshot["days"].pop(op["date"], None)


def edited_snapshot(op, snapshot, source):
    """Build the next revision for a conditional write through a connector."""
    op, expected_source = _validate_operation(op)
    if source != expected_source or snapshot["revision"] != op["revision"]:
        raise Conflict(snapshot["revision"])
    updated = deepcopy(snapshot)
    _apply_changes(op, updated)
    updated["revision"] += 1
    validate(updated)
    return updated


def apply_edit(op):
    op, source = _validate_operation(op)
    with edit_active(data_directory(), op["revision"], source) as snapshot:
        _apply_changes(op, snapshot)
    return {"revision": snapshot["revision"]}


def main():
    argparse.ArgumentParser(description="从标准输入读取一项 UTF-8 JSON 日历编辑").parse_args()
    try:
        operation = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        result = apply_edit(operation)
    except Conflict as exc:
        sys.stderr.buffer.write(encode_json({"error": "conflict", "revision": exc.revision}) + b"\n")
        return 3
    except (ValueError, OSError, RecursionError) as exc:
        sys.stderr.buffer.write(encode_json({"error": str(exc)}) + b"\n")
        return 1
    sys.stdout.buffer.write(encode_json(result) + b"\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
