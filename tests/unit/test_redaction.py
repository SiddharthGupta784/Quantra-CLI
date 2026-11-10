from __future__ import annotations

import pytest

from quantra.core.redaction import REDACTED, is_secret_key, redact


@pytest.mark.parametrize(
    "key",
    ["api_key", "openai_api_key", "X-Api-Key", "token", "access_token", "client_secret",
     "Authorization", "authorization", "api_key_env"],
)  # fmt: skip
def test_secret_looking_keys(key: str) -> None:
    assert is_secret_key(key)


@pytest.mark.parametrize(
    "key", ["endpoint", "model_name", "max_workers", "X-Request-Source", "authorized_users"]
)
def test_ordinary_keys(key: str) -> None:
    assert not is_secret_key(key)


def test_redact_hides_secret_values_and_keeps_others() -> None:
    assert redact("api_key", "sk-123") == REDACTED
    assert redact("endpoint", "http://x") == "http://x"


def test_redact_leaves_unset_secret_fields_visible() -> None:
    assert redact("api_key_env", None) is None


def test_redact_recurses_into_mappings_and_lists() -> None:
    value = {"headers": {"Authorization": "Bearer x", "Accept": "json"}, "items": [{"token": "t"}]}
    assert redact("agent", value) == {
        "headers": {"Authorization": REDACTED, "Accept": "json"},
        "items": [{"token": REDACTED}],
    }
