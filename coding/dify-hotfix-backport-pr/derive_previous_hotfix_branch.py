#!/usr/bin/env python3
"""Derive the previous Dify hotfix branch from a target hotfix branch."""

from __future__ import annotations

import json
import re
import sys


HOTFIX_RE = re.compile(r"^(?:(?P<remote>[^/]+)/)?(?P<prefix>hotfix/[0-9]+\.[0-9]+\.[0-9]+-fix\.)(?P<num>[0-9]+)$")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: derive_previous_hotfix_branch.py <hotfix/x.y.z-fix.N>", file=sys.stderr)
        return 2

    raw_branch = sys.argv[1].strip()
    match = HOTFIX_RE.match(raw_branch)
    if not match:
        print(f"error: unsupported hotfix branch format: {raw_branch}", file=sys.stderr)
        return 2

    number = int(match.group("num"))
    if number == 0:
        print(f"error: {raw_branch} has no previous fix branch; ask for the base tag or branch", file=sys.stderr)
        return 3

    remote = match.group("remote")
    prefix = match.group("prefix")
    target_branch = f"{prefix}{number}"
    previous_branch = f"{prefix}{number - 1}"

    result = {
        "target_branch": target_branch,
        "previous_branch": previous_branch,
        "target_remote_ref": f"{remote}/{target_branch}" if remote else target_branch,
        "previous_remote_ref": f"{remote}/{previous_branch}" if remote else previous_branch,
        "target_fix_number": number,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
