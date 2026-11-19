#!/usr/bin/env python3
"""Open a local status calendar backed by an atomically saved JSON file."""

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from calendar_backend import edit_active, read_active
from calendar_store import Conflict, body_parts_for, data_directory, default_states, encode_json, validate, validate_day_edit


HOST = "127.0.0.1"
DEFAULT_PORT = "17845"
ASSETS = Path(__file__).resolve().parents[1] / "assets"
FILES = {
    "/": ("index.html", "text/html"),
    "/index.html": ("index.html", "text/html"),
    "/style.css": ("style.css", "text/css"),
    "/app.js": ("app.js", "text/javascript"),
    "/month.css": ("month.css", "text/css"),
    "/month.js": ("month.js", "text/javascript"),
    "/inline-month.css": ("inline-month.css", "text/css"),
    "/inline-month.js": ("inline-month.js", "text/javascript"),
}


class InvalidDayEdit(ValueError):
    pass


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def json_reply(self, status, value):
        self.reply(status, encode_json(value), "application/json")

    def calendar_reply(self, snapshot, source):
        presets = default_states()
        states = snapshot["states"] if snapshot["states"] is not None else presets
        self.json_reply(200, {**snapshot, "source": source, "defaultStates": presets, "bodyParts": body_parts_for(states)})

    def local_request(self):
        host = self.server.address
        if self.headers.get("Host") == host and self.headers.get("Origin", "http://" + host) == "http://" + host:
            return True
        self.json_reply(403, {"error": "请通过本地日历地址访问。"})
        return False

    def do_GET(self):
        if not self.local_request():
            return
        path = urlsplit(self.path).path
        if path == "/api/instance":
            self.json_reply(200, {"instance": self.server.instance})
        elif path == "/api/calendar":
            try:
                snapshot, source = read_active(self.server.data_dir)
            except (ValueError, OSError):
                self.json_reply(500, {"error": "无法读取日历，请在聊天中检查存储连接。"})
                return
            self.calendar_reply(snapshot, source)
        elif path in FILES:
            name, content_type = FILES[path]
            try:
                content = (ASSETS / name).read_bytes()
            except OSError:
                self.json_reply(404, {"error": "日历页面文件缺失。"})
                return
            self.reply(200, content, content_type)
        else:
            self.json_reply(404, {"error": "页面不存在。"})

    def do_PUT(self):
        if not self.local_request():
            return
        if urlsplit(self.path).path != "/api/calendar":
            self.json_reply(404, {"error": "页面不存在。"})
            return
        if self.headers.get_content_type() != "application/json":
            self.json_reply(415, {"error": "请使用 JSON 格式保存。"})
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
            if length < 0:
                raise ValueError("请求长度有误。")
            snapshot = json.loads(self.rfile.read(length).decode("utf-8"))
            validate(snapshot)
        except (ValueError, RecursionError):
            self.json_reply(400, {"error": "无法保存，请检查日期、状态名称、颜色和图标。"})
            return
        try:
            source = snapshot.get("source", "local")
            with edit_active(self.server.data_dir, snapshot["revision"], source) as saved:
                for day, entries in snapshot["days"].items():
                    previous = saved["days"].get(day, [])
                    if entries != previous:
                        try:
                            validate_day_edit(snapshot["states"], entries, previous)
                        except ValueError as exc:
                            raise InvalidDayEdit(str(exc)) from exc
                saved["states"] = snapshot["states"]
                saved["days"] = snapshot["days"]
        except InvalidDayEdit as exc:
            self.json_reply(400, {"error": str(exc)})
            return
        except Conflict:
            self.json_reply(409, {"error": "日历已更新，请刷新后重试。"})
            return
        except (OSError, ValueError):
            self.json_reply(500, {"error": "写入日历失败，请检查存储连接。"})
            return
        self.calendar_reply(saved, source)


def instance_running(port, instance):
    conn = http.client.HTTPConnection(HOST, port, timeout=0.5)
    try:
        conn.request("GET", "/api/instance")
        response = conn.getresponse()
        return response.status == 200 and json.loads(response.read(1024)) == {"instance": instance}
    except (OSError, ValueError, http.client.HTTPException):
        return False
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="打开本地状态日历")
    parser.add_argument("--no-open", action="store_true", help="仅启动服务并输出地址")
    parser.add_argument("--serve", action="store_true", help="在前台运行服务")
    args = parser.parse_args()
    try:
        port = int(os.environ.get("STATUS_CALENDAR_PORT", DEFAULT_PORT))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        parser.error("STATUS_CALENDAR_PORT 需要是 1 到 65535 之间的整数。")
    data_dir = data_directory()
    instance = hashlib.sha256(encode_json([str(ASSETS), str(data_dir)])).hexdigest()
    if args.serve:
        with ThreadingHTTPServer((HOST, port), Handler) as server:
            server.address = f"{HOST}:{port}"
            server.instance = instance
            server.data_dir = data_dir
            server.serve_forever()
        return

    if not instance_running(port, instance):
        options = {"start_new_session": True} if os.name != "nt" else {"creationflags": subprocess.DETACHED_PROCESS}
        child = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--serve"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options,
        )
        deadline = time.monotonic() + 5
        while not instance_running(port, instance):
            if child.poll() is not None or time.monotonic() >= deadline:
                sys.exit(f"本地服务启动失败。请检查端口 {port}，或指定其他 STATUS_CALENDAR_PORT 后重试。")
            time.sleep(0.05)
    url = f"http://{HOST}:{port}/"
    print(url, flush=True)
    if not args.no_open and not webbrowser.open(url):
        print("请在浏览器中打开上方地址。", file=sys.stderr)


if __name__ == "__main__":
    main()
