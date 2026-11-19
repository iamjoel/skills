"""Non-secret project identity for a private calendar accessed through Supabase MCP."""

import re


def validate_ref(project_ref):
    if not isinstance(project_ref, str) or not re.fullmatch(r"[a-z0-9]{20}", project_ref):
        raise ValueError("请使用所选 Supabase 项目的 20 位项目编号。")
    return project_ref


def source_for(project_ref):
    return "supabase-private:" + validate_ref(project_ref)


def project_in(saved):
    if saved is None or saved[0] != "supabase" or saved[1].get("mode") != "private_connector":
        return None
    return validate_ref(saved[1].get("project_ref"))
