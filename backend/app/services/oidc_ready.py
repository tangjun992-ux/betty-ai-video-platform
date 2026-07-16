"""
OIDC / SSO readiness — discovery + configuration probes (enterprise).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urljoin

import httpx


def oidc_env() -> dict[str, str]:
    return {
        "issuer": (os.getenv("OIDC_ISSUER") or "").strip().rstrip("/"),
        "client_id": (os.getenv("OIDC_CLIENT_ID") or "").strip(),
        "client_secret": (os.getenv("OIDC_CLIENT_SECRET") or "").strip(),
        "redirect_uri": (os.getenv("OIDC_REDIRECT_URI") or "").strip(),
    }


def oidc_configured() -> bool:
    e = oidc_env()
    return bool(e["issuer"] and e["client_id"] and e["client_secret"] and e["redirect_uri"])


@dataclass
class OidcStatus:
    configured: bool
    issuer: str
    client_id_set: bool
    redirect_uri: str
    discovery_ok: bool
    authorize_url: str
    token_url: str
    userinfo_url: str
    required_in_production: bool
    production_ok: bool
    blockers: list[str]

    def public_dict(self) -> dict:
        return {
            "configured": self.configured,
            "issuer": self.issuer,
            "client_id_set": self.client_id_set,
            "redirect_uri": self.redirect_uri,
            "discovery_ok": self.discovery_ok,
            "authorize_url": self.authorize_url,
            "token_url": self.token_url,
            "userinfo_url": self.userinfo_url,
            "required_in_production": self.required_in_production,
            "production_ok": self.production_ok,
            "blockers": self.blockers,
        }


def _discover(issuer: str) -> Optional[dict[str, Any]]:
    if not issuer:
        return None
    url = f"{issuer}/.well-known/openid-configuration"
    try:
        with httpx.Client(timeout=5.0) as c:
            r = c.get(url)
            if r.status_code >= 400:
                return None
            data = r.json()
            return data if isinstance(data, dict) else None
    except Exception:
        return None


def resolve_endpoints(issuer: str, *, discover: bool = True) -> dict[str, str]:
    """Prefer OIDC discovery; fall back to {issuer}/authorize|/token|/userinfo."""
    issuer = (issuer or "").rstrip("/")
    endpoints = {
        "authorize_url": f"{issuer}/authorize" if issuer else "",
        "token_url": f"{issuer}/token" if issuer else "",
        "userinfo_url": f"{issuer}/userinfo" if issuer else "",
        "discovery_ok": False,
    }
    if discover and issuer:
        meta = _discover(issuer)
        if meta:
            endpoints["authorize_url"] = meta.get("authorization_endpoint") or endpoints["authorize_url"]
            endpoints["token_url"] = meta.get("token_endpoint") or endpoints["token_url"]
            endpoints["userinfo_url"] = meta.get("userinfo_endpoint") or endpoints["userinfo_url"]
            endpoints["discovery_ok"] = True
    return endpoints


def oidc_status(*, discover: bool = False) -> OidcStatus:
    """Status probe. ``discover=True`` hits the IdP (use sparingly)."""
    from app.config import settings

    e = oidc_env()
    configured = oidc_configured()
    eps = resolve_endpoints(e["issuer"], discover=discover and configured)
    required = (os.getenv("OIDC_REQUIRED_IN_PRODUCTION") or "").strip().lower() in (
        "1", "true", "yes", "on",
    )
    blockers: list[str] = []
    if settings.is_production and required and not configured:
        blockers.append("OIDC_REQUIRED_IN_PRODUCTION set but OIDC_* env incomplete")
    return OidcStatus(
        configured=configured,
        issuer=e["issuer"],
        client_id_set=bool(e["client_id"]),
        redirect_uri=e["redirect_uri"],
        discovery_ok=bool(eps.get("discovery_ok")),
        authorize_url=str(eps.get("authorize_url") or ""),
        token_url=str(eps.get("token_url") or ""),
        userinfo_url=str(eps.get("userinfo_url") or ""),
        required_in_production=required,
        production_ok=not blockers,
        blockers=blockers,
    )
