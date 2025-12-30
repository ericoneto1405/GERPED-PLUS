import os
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    import pytz
except Exception:  # pragma: no cover - fallback quando pytz não está disponível
    pytz = None


DEFAULT_TIMEZONE = os.getenv('APP_TIMEZONE', 'America/Sao_Paulo')


def now_utc() -> datetime:
    """Fonte única de tempo: agora em UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


def utcnow() -> datetime:
    """Agora em UTC (naive) para persistência em campos sem timezone."""
    return now_utc().replace(tzinfo=None)


def _get_timezone(tz_name: Optional[str] = None):
    name = tz_name or DEFAULT_TIMEZONE
    return pytz.timezone(name) if pytz else timezone(timedelta(hours=-3))


def to_local(value: datetime, tz_name: Optional[str] = None) -> datetime:
    """Converte datetime para o fuso local configurado (assume UTC se naive)."""
    if value is None or not isinstance(value, datetime):
        return value
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_get_timezone(tz_name))


def local_now(tz_name: Optional[str] = None) -> datetime:
    """Agora no fuso local (timezone-aware), derivado da fonte UTC."""
    return to_local(now_utc(), tz_name)


def local_now_naive(tz_name: Optional[str] = None) -> datetime:
    """Agora no fuso local (naive), derivado da fonte UTC."""
    return local_now(tz_name).replace(tzinfo=None)
