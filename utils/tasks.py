import asyncio

_bg: set = set()


def spawn(coro):
    """Fon vazifasi (GC dan himoyalangan)."""
    t = asyncio.create_task(coro)
    _bg.add(t)
    t.add_done_callback(_bg.discard)
    return t
