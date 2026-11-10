"""Secret redaction for anything that prints configuration (``--print-config``, error tables).

Secrets never belong in YAML (TDD section 5), but values can still reach the screen by mistake:
a user pasting a key into the wrong file, or a header copied from a curl command. Redaction is by
key name, so it also covers fields we have not thought of yet.
"""

from __future__ import annotations

import re
from typing import Any

REDACTED = "***"

# Case-insensitive match on the key name: *key*, *token*, *secret*, or Authorization.
_SECRET_KEY = re.compile(r"key|token|secret|^authorization$", re.IGNORECASE)


def is_secret_key(key: object) -> bool:
    """True when a field or header name looks like it holds a credential."""
    return bool(_SECRET_KEY.search(str(key)))


def redact(key: object, value: Any) -> Any:
    """Return ``value`` unless ``key`` is secret-like; nested mappings are redacted by key."""
    if is_secret_key(key):
        return None if value is None else REDACTED  # an unset value is not a secret
    if isinstance(value, dict):
        return {k: redact(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(key, item) for item in value]
    return value
