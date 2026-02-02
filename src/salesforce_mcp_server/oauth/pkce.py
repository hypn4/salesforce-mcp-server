"""PKCE (Proof Key for Code Exchange) utilities.

Implements RFC 7636 for secure OAuth 2.0 authorization code exchange.
MCP clients are required to use PKCE with the S256 challenge method.
"""

from __future__ import annotations

import base64
import hashlib
import secrets


def generate_pkce_pair() -> tuple[str, str]:
    """Generate a PKCE code_verifier and code_challenge pair.

    The code_verifier is a cryptographically random string that is
    sent to the token endpoint. The code_challenge is a SHA-256 hash
    of the verifier that is sent to the authorization endpoint.

    Per RFC 7636:
    - code_verifier: 43-128 characters of unreserved URI characters
    - code_challenge: BASE64URL(SHA256(code_verifier))

    Returns:
        tuple[str, str]: (code_verifier, code_challenge)

    Example:
        >>> verifier, challenge = generate_pkce_pair()
        >>> verify_pkce(verifier, challenge)
        True
    """
    # Generate a 32-byte random value (produces 43 characters when base64url encoded)
    code_verifier = secrets.token_urlsafe(32)

    # Compute S256 challenge: BASE64URL(SHA256(code_verifier))
    code_challenge = compute_challenge(code_verifier)

    return code_verifier, code_challenge


def compute_challenge(code_verifier: str) -> str:
    """Compute the S256 code_challenge from a code_verifier.

    Args:
        code_verifier: The code verifier string

    Returns:
        str: BASE64URL(SHA256(code_verifier)) without padding
    """
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """Verify a PKCE code_verifier against a code_challenge.

    This is used by the authorization server to verify that the
    client presenting the authorization code is the same client
    that initiated the authorization request.

    Args:
        code_verifier: The verifier submitted at the token endpoint
        code_challenge: The challenge submitted at the authorization endpoint

    Returns:
        bool: True if the verifier matches the challenge

    Example:
        >>> verifier, challenge = generate_pkce_pair()
        >>> verify_pkce(verifier, challenge)
        True
        >>> verify_pkce("wrong_verifier", challenge)
        False
    """
    expected_challenge = compute_challenge(code_verifier)

    # Use constant-time comparison to prevent timing attacks
    return secrets.compare_digest(expected_challenge, code_challenge)
