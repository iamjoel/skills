"""Supabase calendar provider."""

from . import auth
from .store import SupabaseStore


label = "Supabase"
setup_asset = "providers/supabase/setup"


def prompt_settings():
    return {
        "url": input("项目 URL："),
        "key": input("Publishable key："),
        "email": input("Auth 邮箱："),
    }


def authorize(payload):
    local_login = isinstance(payload, dict) and payload.get("local_login") is True
    settings = auth.validate_settings(payload, prompt_for_email=local_login)
    session = auth.sign_in(settings)
    return SupabaseStore(settings, session), {"settings": settings, "session": session}


def restore(binding):
    if not isinstance(binding, dict) or "session" not in binding:
        raise ValueError("云端登录信息不完整，请重新连接 Supabase。")
    settings = auth.validate_settings(binding.get("settings"))
    session = auth.fresh_session(settings, binding["session"])
    if settings != binding["settings"] or session != binding["session"]:
        binding = dict(binding, settings=settings, session=session)
    return SupabaseStore(settings, session), binding
