"""RFC 8785 canonical JSON, and the hash over it that names an answer
(spec/the-analytics-engine-answers-behind-one-api, Q7, ruled 2026-10-12:
"SHA-256 over the canonical JSON of the inputs").

The JSON this package canonicalises holds no floating-point number: a
decimal is a string in its stated form (`"227.50"`), and an integer of 64
bits a string as protobuf's JSON writes one, so RFC 8785's number rule (the
ECMAScript form of an IEEE 754 double) never has to round anything. A whole
number is written as itself only below 2^53, which a double holds exactly.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

__all__ = ["answer_hash", "canonical", "decimal_text"]

#: The largest whole number RFC 8785 writes exactly, as a double holds it.
_EXACT = 2**53


def decimal_text(value: Decimal) -> str:
    """A decimal in its stated form, never in exponent notation: its sign, its
    integer digits ("0" for none) and as many places as its scale, so 150 at
    scale 2 is "1.50" and -5 at scale 3 is "-0.005". The same digits a
    `meridian.v1.Decimal`'s integer and scale give."""
    sign, digits, exponent = value.as_tuple()
    if not isinstance(exponent, int):
        raise ValueError(f"{value} is not a finite number")
    text = "".join(str(d) for d in digits) or "0"
    if exponent >= 0:
        whole = (text + "0" * exponent).lstrip("0") or "0"
        out = whole
    else:
        places = -exponent
        text = text.rjust(places + 1, "0")
        out = f"{text[:-places].lstrip('0') or '0'}.{text[-places:]}"
    negative = sign == 1 and any(c not in "0." for c in out)
    return f"-{out}" if negative else out


def _value(value: Any) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, Decimal):
        return decimal_text(value)
    if isinstance(value, int):
        if abs(value) >= _EXACT:
            raise ValueError(
                f"{value} is past what RFC 8785 writes exactly; "
                "write a 64-bit integer as a string"
            )
        return value
    if isinstance(value, float):
        raise TypeError("canonical JSON here carries no float: write a decimal as a string")
    if isinstance(value, Mapping):
        return {str(k): _value(v) for k, v in value.items()}
    if isinstance(value, Sequence):
        return [_value(v) for v in value]
    raise TypeError(f"{type(value).__name__} has no canonical JSON form")


def _write(value: Any, out: list[str]) -> None:
    if isinstance(value, dict):
        out.append("{")
        # RFC 8785 3.2.3: members sorted by their names' UTF-16 code units.
        for i, key in enumerate(sorted(value, key=lambda k: k.encode("utf-16-be"))):
            if i:
                out.append(",")
            out.append(json.dumps(key, ensure_ascii=False))
            out.append(":")
            _write(value[key], out)
        out.append("}")
    elif isinstance(value, list):
        out.append("[")
        for i, each in enumerate(value):
            if i:
                out.append(",")
            _write(each, out)
        out.append("]")
    else:
        # A string, true, false, null or a whole number below 2^53: Python's
        # JSON writes each as ECMAScript's JSON.stringify does (RFC 8785 3.2.2),
        # strings escaping only the quote, the backslash and control
        # characters, those with \b \f \n \r \t or a lower-case \u00XX.
        out.append(json.dumps(value, ensure_ascii=False))


def canonical(value: Any) -> bytes:
    """`value` as RFC 8785 canonical JSON, UTF-8: no whitespace, members
    sorted, strings escaped as ECMAScript escapes them. A `Decimal` is written
    as its stated text; a float is refused."""
    out: list[str] = []
    _write(_value(value), out)
    return "".join(out).encode("utf-8")


def answer_hash(inputs: Any) -> str:
    """`sha256:` and the lower-case hex of SHA-256 over the canonical JSON of
    `inputs` (Q7): two answers with the same hash are the same answer."""
    return "sha256:" + hashlib.sha256(canonical(inputs)).hexdigest()
