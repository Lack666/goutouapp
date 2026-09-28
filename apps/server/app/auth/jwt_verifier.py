"""Verify a signed Bearer JWT before an actor can be issued."""

from dataclasses import dataclass
from uuid import UUID

import jwt

from app.core.config import Settings

ALGORITHMS = ["HS256"]
MAX_CREDENTIAL_LENGTH = 8192


class CredentialConfigurationError(Exception):
    """The server cannot verify credentials with its current configuration."""


class CredentialVerificationError(Exception):
    """A credential is missing, malformed, expired or untrusted."""


@dataclass(frozen=True)
class VerifiedIdentity:
    user_id: UUID


class JWTBearerVerifier:
    def __init__(self, settings: Settings) -> None:
        secret = settings.auth_jwt_secret
        if (
            secret is None
            or len(secret.get_secret_value().encode("utf-8")) < 32
            or not settings.auth_jwt_issuer
            or not settings.auth_jwt_audience
        ):
            raise CredentialConfigurationError
        self._secret = secret.get_secret_value()
        self._issuer = settings.auth_jwt_issuer
        self._audience = settings.auth_jwt_audience

    def verify(self, credential: str) -> VerifiedIdentity:
        if not isinstance(credential, str) or not 1 <= len(credential) <= MAX_CREDENTIAL_LENGTH:
            raise CredentialVerificationError
        try:
            claims = jwt.decode(
                credential,
                self._secret,
                algorithms=ALGORITHMS,
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["sub", "exp", "iss", "aud"]},
            )
            subject = claims["sub"]
            if not isinstance(subject, str):
                raise ValueError
            return VerifiedIdentity(user_id=UUID(subject))
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            raise CredentialVerificationError from None
