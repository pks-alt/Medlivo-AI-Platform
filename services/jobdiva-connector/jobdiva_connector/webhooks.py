from __future__ import annotations

import hmac
import hashlib


def verify_signature(
    *,
    body: bytes,
    received_signature: str,
    shared_secret: str,
) -> bool:
    """Generic HMAC verifier placeholder.

    Replace the digest/header contract only after JobDiva confirms the exact
    webhook-signature algorithm and header format.
    """
    digest = hmac.new(
        shared_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, received_signature)
