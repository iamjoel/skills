#!/usr/bin/env python3
"""Connect the calendar using public settings from the chat. Prompt locally for the password."""

import argparse
from datetime import date
import json
import sys

from calendar_backend import connect
from calendar_store import data_directory, encode_json
from storage_providers import DEFAULT_PROVIDER, get_provider


def return_view(payload):
    if payload.get("resume") not in ("month", "configure"):
        raise ValueError("连接后只能返回月历或状态配置。")
    month = payload.get("month")
    if not isinstance(month, str) or len(month) != 7 or date.fromisoformat(month + "-01").isoformat()[:7] != month:
        raise ValueError("请重新打开日历，选择有效月份后连接。")
    return {"resume": payload["resume"], "month": month}


def main():
    parser = argparse.ArgumentParser(description="连接状态日历的数据源")
    parser.add_argument("--interactive", action="store_true", help="在本机终端输入连接信息")
    parser.add_argument("--provider", help="交互模式使用的存储提供方标识")
    args = parser.parse_args()
    if args.interactive:
        provider_id = DEFAULT_PROVIDER if args.provider is None else args.provider
        payload = {**get_provider(provider_id).prompt_settings(), "provider": provider_id}
    else:
        if args.provider is not None:
            parser.error("--provider 仅用于交互模式；聊天直接使用表单指定的提供方。")
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict) or payload.get("action") != "connect":
            raise ValueError("需要聊天中确认的云存储连接请求。")
        continuation = return_view(payload)
    result = connect(data_directory(), payload)
    if not args.interactive:
        result.update(continuation)
    sys.stdout.buffer.write(encode_json(result) + b"\n")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, EOFError) as error:
        sys.exit(str(error))
