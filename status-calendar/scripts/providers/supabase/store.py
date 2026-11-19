"""Read and conditionally save one authenticated user's Supabase calendar."""

import hashlib
import json
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

from calendar_store import Conflict, encode_json, validate


class CloudError(ValueError):
    """A cloud request, identity check or response validation failed."""


class TableNotReady(CloudError):
    """The calendar table is absent from the project's Data API schema."""


class _AlreadyExists(Exception):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _user_id(session):
    try:
        return str(UUID(session["user_id"]))
    except (KeyError, TypeError, AttributeError, ValueError):
        raise CloudError("登录用户标识无效，请重新登录。") from None


def _request(settings, session, method, filters, payload=None):
    action = "读取" if method == "GET" else "写入"
    try:
        origin = urlsplit(settings["url"])
        if (origin.scheme != "https" or not origin.hostname or origin.username is not None
                or origin.password is not None or origin.path not in ("", "/") or origin.query or origin.fragment):
            raise CloudError("云端项目地址需要是 HTTPS 根地址。")
        url = origin.geturl().rstrip("/") + "/rest/v1/status_calendars?" + urlencode(filters)
        headers = {"Accept": "application/json", "apikey": settings["key"],
                   "Authorization": "Bearer " + session["access_token"]}
        data = None
        if payload is not None:
            headers.update({"Content-Type": "application/json", "Prefer": "return=representation"})
            data = encode_json(payload)
        req = Request(url, data=data, headers=headers, method=method)
        with build_opener(_NoRedirect()).open(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        with error:
            try:
                body = json.loads(error.read(65536))
                code = body.get("code") if isinstance(body, dict) else None
            except (ValueError, OSError, HTTPException, RecursionError):
                code = None
        if error.code == 404 and code in ("PGRST205", "42P01"):
            raise TableNotReady("项目的数据 API 尚未找到日历表。请在聊天中说「自动配置 Supabase」，重新检查日历表及其 API 设置。") from None
        if method == "POST" and error.code == 409 and code == "23505":
            raise _AlreadyExists from None
        if error.code in (401, 403):
            raise CloudError(f"云端日历{action}被拒绝，请检查登录状态与数据表权限。") from None
        raise CloudError(f"云端日历{action}失败（HTTP {error.code}）。") from None
    except CloudError:
        raise
    except (KeyError, ValueError, TypeError, OSError, URLError, HTTPException, RecursionError):
        raise CloudError(f"云端日历{action}失败，请检查项目连接后重新读取日历。") from None


def _check_snapshot(snapshot):
    if (isinstance(snapshot, dict) and type(snapshot.get("revision")) is int
            and snapshot["revision"] == 0 and "states" in snapshot
            and snapshot["states"] is None and snapshot.get("days") == {}):
        return
    validate(snapshot)
    if snapshot["revision"] < 0:
        raise ValueError("日历修订号必须为非负整数。")


def _one_row(rows, user_id):
    if rows == []:
        return None
    try:
        if not isinstance(rows, list) or len(rows) != 1 or rows[0]["user_id"] != user_id:
            raise ValueError
        snapshot = {key: rows[0][key] for key in ("revision", "states", "days")}
        _check_snapshot(snapshot)
    except (KeyError, ValueError, TypeError, RecursionError):
        raise CloudError("云端日历格式或所属用户不匹配，请重新读取。") from None
    return snapshot


class SupabaseStore:
    def __init__(self, settings, session):
        self._settings = settings
        self._session = session
        self._user_id = _user_id(session)
        # Existing chat cards identify their source by this exact owner string.
        owner = settings["url"] + "/" + session["user_id"]
        self.source = hashlib.sha256(owner.encode("utf-8")).hexdigest()

    def read(self):
        filters = {"user_id": "eq." + self._user_id, "select": "user_id,revision,states,days"}
        rows = _request(self._settings, self._session, "GET", filters)
        return _one_row(rows, self._user_id)

    def commit(self, snapshot, expected_revision):
        """Insert at the original revision, or compare-and-swap an existing row."""
        _check_snapshot(snapshot)
        row = {key: snapshot[key] for key in ("revision", "states", "days")}
        filters = {"select": "user_id,revision,states,days"}
        if expected_revision is None:
            method = "POST"
            payload = dict(row, user_id=self._user_id)
        else:
            if type(expected_revision) is not int or expected_revision < 0 or row["revision"] != expected_revision + 1:
                raise ValueError("更新云端日历需要使用下一修订号。")
            method = "PATCH"
            filters.update({"user_id": "eq." + self._user_id, "revision": f"eq.{expected_revision}"})
            payload = row

        try:
            rows = _request(self._settings, self._session, method, filters, payload)
            saved = _one_row(rows, self._user_id)
        except _AlreadyExists:
            saved = None
        if saved is None:
            # A racing insert or a stale update must never become an unconditional save.
            current = self.read()
            raise Conflict(current["revision"] if current is not None else 0)
        if saved != row:
            raise CloudError("云端返回的日历与本次编辑不一致，请重新读取。")
        return saved
