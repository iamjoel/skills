"""Supabase user authentication. Credentials stay in the local process."""

import getpass
import json
import re
import subprocess
import sys
import time
import warnings
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID


def validate_settings(payload, *, prompt_for_email=False):
    if not isinstance(payload, dict):
        raise ValueError("需要 Supabase 项目地址、publishable key 和登录邮箱。")
    settings = {}
    for field in ("url", "key"):
        value = payload.get(field)
        if not isinstance(value, str):
            raise ValueError("请填写项目地址、publishable key 和登录邮箱。")
        settings[field] = value if field == "key" else value.strip()
    if not re.fullmatch(r"https://[a-z0-9]{20}\.supabase\.co/?", settings["url"]):
        raise ValueError("请使用 HTTPS 项目地址，格式为 https://项目编号.supabase.co。")
    settings["url"] = settings["url"].rstrip("/")
    if prompt_for_email:
        ref = payload.get("project_ref")
        if (not isinstance(ref, str) or not re.fullmatch(r"[a-z0-9]{20}", ref)
                or settings["url"] != f"https://{ref}.supabase.co"):
            raise ValueError("自动连接的项目编号与项目地址不匹配，请重新选择项目。")
    key = settings["key"]
    match = re.fullmatch(r"sb_publishable_([A-Za-z0-9_-]{10,200})", key)
    if not match or re.search(r"sb_secret_|sb_publishable_|sbp_|service_role", match[1], re.IGNORECASE):
        raise ValueError("请填写以 sb_publishable_ 开头的 Supabase 公开 key。")
    email = _local_input(settings["url"]) if prompt_for_email else payload.get("email")
    if not isinstance(email, str) or not re.fullmatch(r"[^@\s\x00-\x1f\x7f]+@[^@\s\x00-\x1f\x7f]+", email.strip()):
        raise ValueError("请填写 Supabase 项目中已注册的登录邮箱。")
    settings["email"] = email.strip()
    return settings


_LOGIN_DIALOG = """
on run arguments
    set projectURL to item 1 of arguments
    if (count of arguments) is 1 then
        set messageText to "输入此项目中已确认的日历账号邮箱。" & return & projectURL & return & "首次使用且尚无账号时，请先到该项目的 Authentication → Users 添加并确认用户。"
        set answerDialog to display dialog messageText with title "状态日历 · 登录邮箱" default answer "" buttons {"取消", "继续"} default button "继续" cancel button "取消"
    else
        set userEmail to item 2 of arguments
        set messageText to "输入此项目的日历账号密码" & return & projectURL & return & userEmail
        set answerDialog to display dialog messageText with title "状态日历 · 连接 Supabase" default answer "" with hidden answer buttons {"取消", "登录"} default button "登录" cancel button "取消"
    end if
    return text returned of answerDialog
end run
"""


def _local_input(project_url, email=None):
    if sys.stdin.isatty() or sys.stderr.isatty():
        prompt = (f"{project_url} 的日历账号密码："
                  if email is not None else
                  f"{project_url} · 日历账号邮箱（隐藏输入；首次使用请先在此项目的 Authentication → Users 添加并确认用户）：")
        with warnings.catch_warnings():
            # getpass normally falls back to visible input if terminal echo cannot be disabled.
            warnings.simplefilter("error", getpass.GetPassWarning)
            try:
                value = getpass.getpass(prompt)
            except KeyboardInterrupt:
                raise ValueError("已取消登录。") from None
            except (getpass.GetPassWarning, OSError, EOFError):
                raise ValueError("当前终端无法隐藏输入。请在本机交互终端重新连接。") from None
    elif sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["/usr/bin/osascript", "-e", _LOGIN_DIALOG, project_url] + ([email] if email is not None else []),
                stdin=subprocess.DEVNULL, capture_output=True, timeout=180,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise ValueError("未能完成系统登录输入，请在本机交互终端重新连接。") from None
        if result.returncode:
            if b"(-128)" in result.stderr:
                raise ValueError("已取消登录。")
            raise ValueError("无法打开系统登录窗口，请在本机交互终端重新连接。")
        try:
            value = result.stdout.decode("utf-8").removesuffix("\n")
        except UnicodeDecodeError:
            raise ValueError("无法读取系统登录窗口的输入，请重新连接。") from None
    else:
        raise ValueError("请在本机交互终端运行连接命令，以隐藏方式输入日历账号信息。")
    if not value:
        raise ValueError("请输入日历账号密码。" if email is not None else "请输入日历账号邮箱。")
    return value


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _session_request(settings, grant, body):
    request = Request(
        f"{settings['url']}/auth/v1/token?grant_type={grant}",
        headers={"apikey": settings["key"], "Content-Type": "application/json"},
        data=json.dumps(body).encode("utf-8"), method="POST",
    )
    try:
        with build_opener(_NoRedirect()).open(request, timeout=20) as response:
            result = json.load(response)
    except HTTPError as error:
        status = error.code
        error.close()
        if status == 429:
            raise ValueError("Supabase 登录请求过于频繁，请稍后重试。") from None
        if grant == "refresh_token" and status in (400, 401, 403):
            raise ValueError("日历登录已过期，请重新连接 Supabase。") from None
        if grant == "password" and status in (400, 401, 403, 422):
            raise ValueError("Supabase 登录失败，请检查项目和日历账号凭据。首次使用且尚无账号时，请先在该项目的 Authentication → Users 添加并确认用户。") from None
        raise ValueError(f"Supabase 登录服务返回 HTTP {status}，请检查项目或稍后重试。") from None
    except (OSError, HTTPException, URLError, ValueError):
        raise ValueError("无法读取 Supabase 登录响应，请检查网络和项目地址。") from None
    if not isinstance(result, dict) or not isinstance(result.get("user"), dict):
        raise ValueError("Supabase 未返回账号信息，请重新连接。")
    expiry = result.get("expires_at")
    if expiry is None and type(result.get("expires_in")) is int:
        expiry = int(time.time()) + result["expires_in"]
    session = {
        "access_token": result.get("access_token"),
        "refresh_token": result.get("refresh_token"),
        "user_id": result["user"].get("id"),
        "expires_at": expiry,
    }
    _validate_session(session)
    return session


def _validate_session(session):
    if not isinstance(session, dict) or type(session.get("expires_at")) is not int:
        raise ValueError("登录会话无效，请重新连接 Supabase。")
    for field in ("access_token", "refresh_token"):
        if not isinstance(session.get(field), str) or not re.fullmatch(r"[!-~]+", session[field]):
            raise ValueError("登录令牌无效，请重新连接 Supabase。")
    try:
        UUID(str(session.get("user_id")))
    except ValueError:
        raise ValueError("登录账号标识无效，请重新连接 Supabase。") from None


def sign_in(settings):
    settings = validate_settings(settings)
    return _session_request(settings, "password", {
        "email": settings["email"], "password": _local_input(settings["url"], settings["email"]),
    })


def fresh_session(settings, session):
    settings = validate_settings(settings)
    _validate_session(session)
    if session["expires_at"] > time.time() + 60:
        return session
    renewed = _session_request(settings, "refresh_token", {"refresh_token": session["refresh_token"]})
    if renewed["user_id"] != session["user_id"]:
        raise ValueError("刷新后账号发生变化，请重新连接。")
    return renewed
