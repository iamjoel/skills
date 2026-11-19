"""Prepare and verify SQL for a private calendar accessed through the user's connector."""

import argparse
import base64
from datetime import date
import json
from pathlib import Path
import sys

from calendar_backend import bind_connector, connector_project
from calendar_store import Conflict, data_directory, encode_json, read_calendar, validate
from render_card import calendar_month, render
from save_edit import edited_snapshot
from .private_binding import source_for, validate_ref


def _revision(value):
    if type(value) is not int or not 0 <= value < 2**63:
        raise ValueError("日历修订号无效，请重新读取。")
    return value


def _validate_snapshot(value):
    if not isinstance(value, dict) or value.keys() != {"revision", "states", "days"}:
        raise ValueError("云端日历快照字段不完整。")
    revision = _revision(value["revision"])
    if value["states"] is None and revision == 0 and value["days"] == {}:
        return value
    validate(value)
    return value


def _one_result(project_ref, payload, fields):
    validate_ref(project_ref)
    rows = payload.get("rows") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise ValueError("需要来自所选项目的一行完整查询结果。")
    row = rows[0]
    if row.keys() != fields | {"project_ref"} or row["project_ref"] != project_ref:
        raise ValueError("查询结果与当前项目或操作不匹配，请重新读取。")
    return row


def _snapshot(project_ref, payload, *, allow_missing=False):
    snapshot = _one_result(project_ref, payload, {"snapshot"})["snapshot"]
    if snapshot is None:
        if allow_missing:
            return None
        raise ValueError("项目尚无日历记录，请先完成初始化。")
    return _validate_snapshot(snapshot)


def read_plan(project_ref):
    validate_ref(project_ref)
    sql = f"""select '{project_ref}'::text as project_ref,
       (select jsonb_build_object('revision', revision, 'states', states, 'days', days)
        from public.status_calendars where id is true) as snapshot"""
    return {"project_ref": project_ref, "sql": sql}


def _write_plan(project_ref, snapshot, previous_revision):
    validate_ref(project_ref)
    _validate_snapshot(snapshot)
    # Only base64 data, a validated project ref, and integers enter the SQL text.
    encoded = base64.b64encode(encode_json(snapshot)).decode("ascii")
    columns = "(doc->>'revision')::bigint, nullif(doc->'states', 'null'::jsonb), doc->'days'"
    if previous_revision is None:
        operation = f"""insert into public.status_calendars (id, revision, states, days)
      select true, {columns} from incoming
      on conflict (id) do nothing"""
    else:
        previous_revision = _revision(previous_revision)
        if snapshot["revision"] != previous_revision + 1:
            raise ValueError("更新云端日历需要下一修订号。")
        operation = f"""update public.status_calendars
      set (revision, states, days) = (select {columns} from incoming)
      where id is true and revision = {previous_revision}"""
    sql = f"""with incoming as (
    select convert_from(decode('{encoded}', 'base64'), 'UTF8')::jsonb as doc
), written as (
    {operation}
    returning revision
)
select '{project_ref}'::text as project_ref, count(*) = 1 as saved, max(revision) as revision
from written"""
    return {"project_ref": project_ref, "sql": sql, "expected_revision": snapshot["revision"]}


def import_plan(directory, project_ref, payload):
    if _snapshot(project_ref, payload, allow_missing=True) is not None:
        raise ValueError("项目已有日历，请直接绑定已有记录。")
    local = read_calendar(directory)
    return {**_write_plan(project_ref, local, None),
            "imported_days": sum(bool(entries) for entries in local["days"].values())}


def _require_binding(directory, project_ref):
    if connector_project(directory) != project_ref:
        raise ValueError("当前日历绑定的项目已变化，请重新打开日历。")


def edit_plan(directory, project_ref, payload):
    _require_binding(directory, project_ref)
    current = _snapshot(project_ref, payload)
    updated = edited_snapshot(payload.get("operation"), current, source_for(project_ref))
    return _write_plan(project_ref, updated, current["revision"])


def check_receipt(project_ref, payload):
    row = _one_result(project_ref, payload, {"saved", "revision"})
    expected = _revision(payload.get("expected_revision"))
    if row["saved"] is False and row["revision"] is None:
        return {"project_ref": project_ref, "saved": False, "next": "read"}
    if row["saved"] is not True or _revision(row["revision"]) != expected:
        raise ValueError("写入回执与提交的修订号不匹配，请重新读取。")
    return {"project_ref": project_ref, "saved": True, "revision": expected}


def bind_result(directory, project_ref, payload):
    snapshot = _snapshot(project_ref, payload)
    imported_revision = payload.get("imported_revision")
    if imported_revision is not None:
        _revision(imported_revision)
        if snapshot["revision"] < imported_revision:
            raise ValueError("读取的云端修订早于首次上传的修订，请重新读取。")
    bind_connector(directory, project_ref, expected_local_revision=imported_revision)
    return {"connected": True, "project_ref": project_ref, "revision": snapshot["revision"],
            "recorded_days": sum(bool(entries) for entries in snapshot["days"].values())}


def main():
    parser = argparse.ArgumentParser(description="通过已授权的 Supabase 连接器管理私人日历")
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("target")
    for action in ("read", "import", "edit", "receipt", "bind", "render"):
        command = commands.add_parser(action)
        command.add_argument("--project-ref", required=True)
        if action == "render":
            command.add_argument("--mode", required=True, choices=["month", "configure"])
            command.add_argument("--month", type=calendar_month, default=date.today().strftime("%Y-%m"))
            command.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    directory = data_directory()
    if args.action == "target":
        result = {"project_ref": connector_project(directory)}
    elif args.action == "read":
        result = read_plan(args.project_ref)
    else:
        payload = json.load(sys.stdin)
        ref = args.project_ref
        if args.action == "import":
            result = import_plan(directory, ref, payload)
        elif args.action == "edit":
            result = edit_plan(directory, ref, payload)
        elif args.action == "receipt":
            result = check_receipt(ref, payload)
        elif args.action == "bind":
            result = bind_result(directory, ref, payload)
        else:
            _require_binding(directory, ref)
            snapshot = _snapshot(ref, payload)
            path = render(args.mode, args.month, args.output_dir,
                          connector_snapshot=(source_for(ref), snapshot))
            print(path)
            return 0
    sys.stdout.buffer.write(encode_json(result) + b"\n")
    return 3 if result.get("saved") is False else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Conflict as exc:
        sys.stderr.buffer.write(encode_json({"error": "conflict", "revision": exc.revision}) + b"\n")
        sys.exit(3)
    except (ValueError, OSError, RecursionError) as exc:
        sys.stderr.buffer.write(encode_json({"error": str(exc)}) + b"\n")
        sys.exit(1)
