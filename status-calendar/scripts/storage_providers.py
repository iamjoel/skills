"""Storage contracts and the explicit registry of connectable data sources."""

from typing import Dict, Optional, Protocol, Tuple

from providers import supabase


class CalendarStorage(Protocol):
    @property
    def source(self) -> str:
        """Stable, non-secret identity of this calendar within the provider."""
        ...

    def read(self) -> Optional[dict]:
        """Return an independently editable snapshot, or None when the calendar is absent."""
        ...

    def commit(self, snapshot: dict, expected_revision: Optional[int]):
        """Create only if absent for None, otherwise compare-and-swap or raise Conflict."""
        ...


class StorageProvider(Protocol):
    label: str
    setup_asset: str

    def prompt_settings(self) -> dict: ...

    def authorize(self, payload: dict) -> Tuple[CalendarStorage, dict]:
        """Open a connection and return its private JSON binding for later use."""
        ...

    def restore(self, binding: dict) -> Tuple[CalendarStorage, dict]:
        """Reopen a saved binding, returning updated credentials if they rotated."""
        ...


DEFAULT_PROVIDER = "supabase"
PROVIDERS: Dict[str, StorageProvider] = {"supabase": supabase}

# Connections and chat cards created before storage providers had explicit IDs.
LEGACY_PROVIDER = "supabase"
LEGACY_CONNECTION_FILE = "supabase-session.json"


def get_provider(provider_id: str) -> StorageProvider:
    if not isinstance(provider_id, str) or provider_id not in PROVIDERS:
        supported = "、".join(provider.label for provider in PROVIDERS.values())
        raise ValueError(f"日历存储提供方未注册。已注册：{supported}。")
    return PROVIDERS[provider_id]
