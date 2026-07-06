"""Microsoft Entra ID JWT token validation.

Usage:
- AUTH_ENABLED=false (default): nothing is validated, all dependencies
  return a demo principal with both roles (Customer + Operator). This way
  the "open" demo keeps working exactly as before.
- AUTH_ENABLED=true: every request must carry an `Authorization: Bearer <jwt>`.
  The signature is validated against the tenant JWKS, and
  `aud=api://{AUTH_CLIENT_ID}` and `iss=https://login.microsoftonline.com/{tenant}/v2.0`
  are required.

Expected roles (`roles` claim of the access token):
- Customer.Submit  → can create and query their own claims
- Operator.Review  → can view all claims, the review queue, etc.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, Request, status

logger = logging.getLogger(__name__)

AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "").lower() == "true"
TENANT_ID = os.environ.get("AUTH_TENANT_ID", "").strip()
CLIENT_ID = os.environ.get("AUTH_CLIENT_ID", "").strip()

ROLE_CUSTOMER = "Customer.Submit"
ROLE_OPERATOR = "Operator.Review"


@dataclass
class Principal:
    sub: str
    upn: str
    name: str
    roles: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @property
    def is_customer(self) -> bool:
        return ROLE_CUSTOMER in self.roles

    @property
    def is_operator(self) -> bool:
        return ROLE_OPERATOR in self.roles


# Principal used when AUTH_ENABLED=false. Has both roles so that any
# protected endpoint keeps working in open demo mode.
_DEMO_PRINCIPAL = Principal(
    sub="demo",
    upn="demo@local",
    name="Demo (auth disabled)",
    roles=[ROLE_CUSTOMER, ROLE_OPERATOR],
)


# ── JWKS cache ────────────────────────────────────────────────────────────────
_jwks_cache: dict = {}
_jwks_cache_ts: float = 0.0
_JWKS_TTL_SECONDS = 60 * 60  # 1h


def _jwks_url() -> str:
    return f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"


def _expected_issuer() -> str:
    return f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"


def _expected_audience() -> list[str]:
    # In v2.0 tokens issued by the app itself, the aud may be the bare GUID
    # (`{CLIENT_ID}`) or the identifier URI (`api://{CLIENT_ID}`). We accept both.
    return [f"api://{CLIENT_ID}", CLIENT_ID]


def _get_jwks(force_refresh: bool = False) -> dict:
    global _jwks_cache, _jwks_cache_ts
    now = time.time()
    if not force_refresh and _jwks_cache and now - _jwks_cache_ts < _JWKS_TTL_SECONDS:
        return _jwks_cache
    resp = httpx.get(_jwks_url(), timeout=10.0)
    resp.raise_for_status()
    _jwks_cache = resp.json()
    _jwks_cache_ts = now
    return _jwks_cache


def _validate_token(token: str) -> Principal:
    """Validate the JWT signature + standard claims and return a Principal."""
    import jwt
    from jwt.algorithms import RSAAlgorithm

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as e:
        logger.warning("Token without a valid header: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token"
        ) from e

    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_kid")

    jwks = _get_jwks()
    key_dict = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if key_dict is None:
        # Refresh in case the key was rotated
        jwks = _get_jwks(force_refresh=True)
        key_dict = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if key_dict is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unknown_kid")

    public_key = RSAAlgorithm.from_jwk(json.dumps(key_dict))

    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=_expected_audience(),
            issuer=_expected_issuer(),
            options={"require": ["exp", "iat"]},
        )
    except jwt.PyJWTError as e:
        logger.warning("Invalid JWT token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"invalid_token: {e}"
        ) from e

    roles = claims.get("roles") or []
    if not isinstance(roles, list):
        roles = []

    return Principal(
        sub=str(claims.get("sub") or claims.get("oid") or ""),
        upn=str(claims.get("upn") or claims.get("preferred_username") or claims.get("email") or ""),
        name=str(claims.get("name") or ""),
        roles=[str(r) for r in roles],
        raw=claims,
    )


def _extract_bearer(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


# ── FastAPI dependencies ──────────────────────────────────────────────────────

def get_principal(request: Request) -> Principal:
    """Base dependency: extract+validate the token or return the demo principal."""
    if not AUTH_ENABLED:
        return _DEMO_PRINCIPAL
    if not TENANT_ID or not CLIENT_ID:
        logger.error("AUTH_ENABLED=true but AUTH_TENANT_ID/AUTH_CLIENT_ID empty")
        raise HTTPException(status_code=500, detail="auth_misconfigured")
    token = _extract_bearer(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_bearer_token"
        )
    return _validate_token(token)


def require_authenticated(principal: Principal = Depends(get_principal)) -> Principal:
    return principal


def require_customer(principal: Principal = Depends(get_principal)) -> Principal:
    if not AUTH_ENABLED:
        return principal
    if not principal.is_customer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="role_customer_required"
        )
    return principal


def require_operator(principal: Principal = Depends(get_principal)) -> Principal:
    if not AUTH_ENABLED:
        return principal
    if not principal.is_operator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="role_operator_required"
        )
    return principal


def require_customer_or_operator(
    principal: Principal = Depends(get_principal),
) -> Principal:
    if not AUTH_ENABLED:
        return principal
    if not (principal.is_customer or principal.is_operator):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="role_required"
        )
    return principal


def enforce_self_or_operator(principal: Principal, customer_id: str) -> None:
    """If the principal is customer-only, require `customer_id` to match their UPN."""
    if not AUTH_ENABLED:
        return
    if principal.is_operator:
        return
    # In the demo the frontend uses the UPN as customer_id, so we compare
    # case-insensitive against several candidates from the token.
    candidates = {
        principal.upn.lower(),
        str(principal.raw.get("preferred_username", "")).lower(),
        str(principal.raw.get("email", "")).lower(),
    }
    if customer_id.lower() not in candidates:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="customer_id_mismatch",
        )
