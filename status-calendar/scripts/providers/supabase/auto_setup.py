"""Finish an agent-mediated Supabase setup using a selected project and its inspection result."""

import json
import re
import sys

from calendar_backend import connect
from calendar_store import data_directory, encode_json
from connect_cloud import return_view


def advance(directory, evidence):
    if not isinstance(evidence, dict):
        raise ValueError("需要所选项目的检查结果。")
    continuation = return_view(evidence)
    project_ref = evidence.get("project_ref")
    if not isinstance(project_ref, str) or not re.fullmatch(r"[a-z0-9]{20}", project_ref):
        raise ValueError("请通过 Supabase 连接器选择目标项目。")
    status = evidence.get("schema_status")
    if status == "missing":
        return {"next": "confirm_migration", "project_ref": project_ref, **continuation}
    if status == "review":
        return {"next": "review_schema", "project_ref": project_ref, **continuation}
    if status != "ready":
        raise ValueError("请在所选项目中重新执行日历表检查。")

    # Only the public project key reaches the adapter. Login happens on the
    # user's device and the connector is never used to read calendar entries.
    result = connect(directory, {
        "provider": "supabase", "local_login": True, "project_ref": project_ref,
        "url": evidence.get("url"), "key": evidence.get("key"),
    })
    return {"next": "render", **continuation, **result}


if __name__ == "__main__":
    try:
        result = advance(data_directory(), json.load(sys.stdin))
        sys.stdout.buffer.write(encode_json(result) + b"\n")
    except (OSError, ValueError, EOFError) as error:
        sys.exit(str(error))
