"""Deterministic JSON canonicalization for cbc-event hashes.

The implementation follows the RFC 8785 shape for the value types used by the
protocol: sorted object keys, no insignificant whitespace, UTF-8 strings, and
finite numbers. Unsupported values are rejected instead of being silently
coerced.
"""
from __future__ import annotations

import json
import math
from decimal import Decimal
from typing import Any


class CanonicalizationError(ValueError):
    """Raised when a value has no stable canonical representation."""


def _number(value: int | float) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalizationError("NaN and Infinity are not canonical")
        if value == 0:
            return "0"
        sign = "-" if value < 0 else ""
        decimal = Decimal(repr(abs(value)))
        digits = "".join(str(digit) for digit in decimal.as_tuple().digits)
        exponent = decimal.as_tuple().exponent
        # Strip representation-only trailing zeroes; Decimal keeps "100.0".
        while len(digits) > 1 and digits.endswith("0"):
            digits = digits[:-1]
            exponent += 1
        point = len(digits) + exponent
        if 0 < point <= 21:
            if point >= len(digits):
                text = digits + "0" * (point - len(digits))
            else:
                text = digits[:point] + "." + digits[point:]
        elif -6 < point <= 0:
            text = "0." + "0" * (-point) + digits
        else:
            fraction = digits[1:]
            text = digits[0] + ("." + fraction if fraction else "") + "e" + ("+" if point - 1 >= 0 else "") + str(point - 1)
        return sign + text
    raise CanonicalizationError(f"unsupported number type: {type(value).__name__}")


def _string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _encode(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return _number(value)
    if isinstance(value, str):
        return _string(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise CanonicalizationError("object keys must be strings")
        keys = sorted(value, key=lambda key: key.encode("utf-16-be", "surrogatepass"))
        return "{" + ",".join(_string(key) + ":" + _encode(value[key]) for key in keys) + "}"
    raise CanonicalizationError(f"unsupported value type: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Return the canonical JSON text for a supported value."""
    return _encode(value)


def canonical_bytes(value: Any) -> bytes:
    """Return canonical JSON encoded as UTF-8."""
    return canonical_json(value).encode("utf-8")
