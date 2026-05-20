from __future__ import annotations

import time

from azure.core.credentials import AccessToken

from agentverse.credentials import CachedTokenCredential


class FakeCredential:
    def __init__(self) -> None:
        self.calls = 0

    def get_token(self, *scopes: str, **kwargs: object) -> AccessToken:
        self.calls += 1
        return AccessToken(f"token-{self.calls}", int(time.time()) + 3600)


def test_cached_token_credential_reuses_unexpired_token() -> None:
    fake = FakeCredential()
    credential = CachedTokenCredential(fake)

    first = credential.get_token("scope-a")
    second = credential.get_token("scope-a")

    assert first.token == second.token == "token-1"
    assert fake.calls == 1


def test_cached_token_credential_keeps_scopes_separate() -> None:
    fake = FakeCredential()
    credential = CachedTokenCredential(fake)

    first = credential.get_token("scope-a")
    second = credential.get_token("scope-b")

    assert first.token == "token-1"
    assert second.token == "token-2"
    assert fake.calls == 2
