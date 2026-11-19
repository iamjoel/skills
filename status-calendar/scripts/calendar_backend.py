"""Select a store, import local history on first connection, and guard calendar edits."""

from contextlib import contextmanager
import json

from typing import Tuple

from calendar_store import Conflict, validate, write_lock, write_private_json
from providers.local import LocalStore
from providers.supabase import private_binding
from storage_providers import CalendarStorage, LEGACY_CONNECTION_FILE, LEGACY_PROVIDER, get_provider


def connection_file(directory):
    return directory / "storage-connection.json"


def _configured(directory):
    # A migration publishes the new file before removing the old one.
    return (directory / LEGACY_CONNECTION_FILE).exists() or connection_file(directory).exists()


def _saved_binding(directory):
    """Return (provider ID, opaque binding, legacy format), or None on first use."""
    for path, legacy in ((connection_file(directory), False), (directory / LEGACY_CONNECTION_FILE, True)):
        try:
            with path.open(encoding="utf-8") as source:
                value = json.load(source)
        except FileNotFoundError:
            continue
        except ValueError:
            raise ValueError("日历存储连接无法读取，请重新连接。") from None
        if legacy and isinstance(value, dict):
            return LEGACY_PROVIDER, value, True
        if isinstance(value, dict) and isinstance(value.get("binding"), dict):
            provider_id = value.get("provider")
            get_provider(provider_id)
            return provider_id, value["binding"], False
        raise ValueError("日历存储连接信息不完整，请重新连接。")
    return None


def active_provider_id(directory):
    if not _configured(directory):
        return None
    with write_lock(directory):
        binding = _saved_binding(directory)
        return binding[0] if binding else None


def _save_binding(directory, provider_id, binding):
    # Publish before retiring a legacy file. Readers always prefer the new file.
    write_private_json(connection_file(directory), {"provider": provider_id, "binding": binding})
    (directory / LEGACY_CONNECTION_FILE).unlink(missing_ok=True)


def connector_project(directory):
    return private_binding.project_in(_saved_binding(directory))


def bind_connector(directory, project_ref, expected_local_revision=None):
    """Publish the project identity after a verified cloud read."""
    binding = {"mode": "private_connector", "project_ref": private_binding.validate_ref(project_ref)}
    with write_lock(directory):
        if expected_local_revision is not None:
            revision = LocalStore(directory).read()["revision"]
            if type(expected_local_revision) is not int or revision != expected_local_revision:
                raise Conflict(revision)
        _save_binding(directory, "supabase", binding)


def _active_store(directory) -> Tuple[CalendarStorage, str]:
    saved = _saved_binding(directory)
    if saved is None:
        store = LocalStore(directory)
        return store, store.source
    if private_binding.project_in(saved) is not None:
        raise ValueError("请在聊天中使用已授权的 Supabase 连接器读取或保存此私人日历。")
    provider_id, binding, legacy = saved
    store, refreshed = get_provider(provider_id).restore(binding)
    if legacy or refreshed != binding:
        _save_binding(directory, provider_id, refreshed)
    # Retain the identity printed on existing cards. New providers may use the
    # same account identifier as one another, so scope their IDs in the router.
    source = store.source if provider_id == LEGACY_PROVIDER else f"{provider_id}:{store.source}"
    return store, source


def _read_existing(store):
    snapshot = store.read()
    if snapshot is None:
        raise ValueError("已连接的数据源中没有日历，请重新连接。")
    return snapshot


def read_active(directory, connector_snapshot=None):
    if connector_snapshot is not None:
        source, snapshot = connector_snapshot
        project = connector_project(directory)
        if project is None or source != private_binding.source_for(project):
            raise ValueError("数据来源与目前绑定的日历项目不符，请重新读取。")
        return snapshot, source
    # A first-use read can render a local calendar without creating any files.
    if not _configured(directory):
        store = LocalStore(directory)
        return store.read(), store.source
    with write_lock(directory):
        store, source = _active_store(directory)
        return _read_existing(store), source


def connect(directory, payload):
    if not isinstance(payload, dict):
        raise ValueError("需要日历存储连接信息。")
    provider_id = payload.get("provider", LEGACY_PROVIDER)
    store, binding = get_provider(provider_id).authorize(payload)
    with write_lock(directory):
        imported = False
        imported_days = 0
        created = False
        if store.read() is None:
            # Import from the original local file, even when switching accounts.
            local = LocalStore(directory).read()
            try:
                store.commit(local, expected_revision=None)
                created = True
                imported = bool(local["states"] is not None or local["days"])
                imported_days = sum(bool(entries) for entries in local["days"].values())
            except Conflict:
                # Another device created the calendar first. Keep its contents.
                _read_existing(store)
        _save_binding(directory, provider_id, binding)
    return {"connected": True, "imported": imported, "imported_days": imported_days,
            "calendar": "created" if created else "existing"}


@contextmanager
def edit_active(directory, expected_revision, source):
    with write_lock(directory):
        store, current_source = _active_store(directory)
        snapshot = _read_existing(store)
        if source != current_source or expected_revision != snapshot["revision"]:
            raise Conflict(snapshot["revision"])
        yield snapshot
        snapshot["revision"] += 1
        validate(snapshot)
        store.commit(snapshot, expected_revision=expected_revision)
