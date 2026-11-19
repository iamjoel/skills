#!/usr/bin/env python3
"""Render one chat view from the active calendar without starting a service."""

import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile
from uuid import uuid4

from calendar_backend import active_provider_id, read_active
from calendar_store import body_parts_for, data_directory, default_states
from storage_providers import DEFAULT_PROVIDER, get_provider


ASSETS = Path(__file__).resolve().parents[1] / "assets"


def calendar_month(value):
    try:
        first = date.fromisoformat(value + "-01")
        if first.isoformat()[:7] == value:
            return value
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("月份格式为 YYYY-MM")


def render(mode, month, directory, provider=None, *, connector_snapshot=None):
    if provider is not None and mode != "storage":
        raise ValueError("--provider 仅用于选择连接表单。")
    data = {"mode": mode, "month": month}
    styles, views, mounts = [], [], []

    def include(asset, mount):
        styles.append((ASSETS / (asset + ".css")).read_text(encoding="utf-8"))
        views.append((ASSETS / (asset + ".js")).read_text(encoding="utf-8"))
        mounts.append(mount)

    if mode != "storage":
        snapshot, source = read_active(data_directory(), connector_snapshot)
        data.update(revision=snapshot["revision"], source=source,
                    states=snapshot["states"] if snapshot["states"] is not None else default_states())
        data["bodyParts"] = body_parts_for(data["states"])
    if mode == "configure":
        data["usedIds"] = sorted({entry["stateId"] for entries in snapshot["days"].values() for entry in entries})
        include("inline-config", "renderStatusConfig(view, data, submitEdit);")
    elif mode == "month":
        data["days"] = {key: entries for key, entries in snapshot["days"].items() if key[:7] == month}
        include("inline-month", 'window.renderStatusMonth(view, data, (date, entries) => submitEdit({ action: "day", date, entries }));')
    if mode == "storage" or data.get("source") == "local":
        if mode == "storage" and provider is None:
            provider = active_provider_id(data_directory())
        provider_id = DEFAULT_PROVIDER if provider is None else provider
        data["provider"] = provider_id
        data["resume"] = "configure" if mode == "configure" else "month"
        include(get_provider(provider_id).setup_asset, 'renderStorageSetup(root.querySelector("[data-storage]"), data);')

    # JSON sits inside a script element even when its MIME type is application/json.
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", r"\u003c")
    parts = {
        "ID": "status-calendar-" + uuid4().hex,
        "STYLES": "\n".join(styles),
        "DATA": payload,
        "VIEW": "\n".join(views),
        "MOUNT": "\n".join(mounts),
    }
    template = (ASSETS / "inline-card.html").read_text(encoding="utf-8")
    fragment = re.sub(r"__CALENDAR_(\w+)__", lambda match: parts[match[1]], template)
    if len(fragment.encode("utf-8")) > 1_000_000:
        raise ValueError("当前视图超过聊天组件的 1 MB 上限。")
    directory.mkdir(parents=True, exist_ok=True)
    # Each reply gets its own snapshot so earlier chat messages keep their view.
    with NamedTemporaryFile(mode="w", encoding="utf-8", prefix=f"status-calendar-{mode}-",
                            suffix=".html", dir=directory, delete=False) as output:
        output.write(fragment)
        return Path(output.name).resolve()


def main():
    parser = argparse.ArgumentParser(description="生成聊天内的状态日历")
    parser.add_argument("mode", choices=["configure", "month", "storage"])
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--month", type=calendar_month, default=date.today().strftime("%Y-%m"))
    parser.add_argument("--provider", help="storage 视图使用的存储提供方标识")
    args = parser.parse_args()
    try:
        print(render(args.mode, args.month, args.output_dir, args.provider))
    except (OSError, ValueError) as error:
        sys.exit(f"日历生成失败。{error}")


if __name__ == "__main__":
    main()
