

import time

_store: dict[str, tuple[float, object]] = {}
TTL_SECONDS = 30


def cache_get(key: str):
    entry = _store.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if time.time() > expires_at:
        _store.pop(key, None)
        return None
    return value


def cache_set(key: str, value: object):
    _store[key] = (time.time() + TTL_SECONDS, value)


def cache_clear():
    _store.clear()
