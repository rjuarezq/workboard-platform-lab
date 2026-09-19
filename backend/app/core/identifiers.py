"""Domain identifier generation compatible with Python 3.11."""

from secrets import randbits
from time import time_ns
from uuid import UUID

_TIMESTAMP_MASK = (1 << 48) - 1


def uuid7() -> UUID:
    """Generate an RFC 9562 UUIDv7 using a UTC Unix timestamp and secure randomness."""
    timestamp_ms = (time_ns() // 1_000_000) & _TIMESTAMP_MASK
    random_a = randbits(12)
    random_b = randbits(62)
    value = (timestamp_ms << 80) | (0x7 << 76) | (random_a << 64) | (0b10 << 62) | random_b
    return UUID(int=value)
