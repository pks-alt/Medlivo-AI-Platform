"""Verify Google identity; application roles ALWAYS come from the database.

No browser cookie/session flow is implemented in this milestone. A future BFF
must keep tokens server-side and handle login state, nonce, CSRF and sessions.
"""
from dataclasses import dataclass
import re
from typing import Callable
import jwt


class AuthenticationError(Exception):
    pass


@dataclass(frozen=True)
class Identity:
    provider: str
    subject: str
    email: str


class GoogleIdentityVerifier:
    def __init__(self, client_id: str, hosted_domain: str, *, key_resolver: Callable | None = None):
        self.client_id = client_id
        self.hosted_domain = hosted_domain
        # The key origin is fixed. Never use token-controlled jku/x5u URLs.
        jwks = jwt.PyJWKClient(
            "https://www.googleapis.com/oauth2/v3/certs",
            cache_jwk_set=True, lifespan=300, cache_keys=False, timeout=5,
        )
        self._key = key_resolver or (lambda token: jwks.get_signing_key_from_jwt(token).key)

    def verify(self, token: str) -> Identity:
        if not isinstance(token, str) or not 1 <= len(token) <= 8192:
            raise AuthenticationError("Authentication required")
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256" or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", str(header.get("kid", ""))):
                raise AuthenticationError("Authentication required")
            claims = jwt.decode(
                token, self._key(token), algorithms=["RS256"], audience=self.client_id,
                issuer=["accounts.google.com", "https://accounts.google.com"],
                options={"require": ["exp", "iat", "iss", "aud", "sub", "email", "email_verified", "hd"], "strict_aud": True},
                leeway=0,
            )
            if claims.get("email_verified") is not True or claims.get("hd") != self.hosted_domain:
                raise AuthenticationError("Authentication required")
            if "azp" in claims and claims["azp"] != self.client_id:
                raise AuthenticationError("Authentication required")
            subject = claims["sub"]
            email = claims["email"]
            if not isinstance(subject, str) or not 1 <= len(subject) <= 255:
                raise AuthenticationError("Authentication required")
            if not isinstance(email, str) or not 3 <= len(email) <= 320 or email.strip() != email:
                raise AuthenticationError("Authentication required")
            email = email.lower()
            if not email.endswith("@" + self.hosted_domain):
                raise AuthenticationError("Authentication required")
            return Identity("google", subject, email)
        except AuthenticationError:
            raise
        except (jwt.PyJWTError, ValueError, TypeError, KeyError, OSError):
            # Never include the token, claims, network URL or library message.
            raise AuthenticationError("Authentication required") from None
