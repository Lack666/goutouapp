"""Signed Bearer credential verification without HTTP or model credentials."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import jwt
import pytest

from app.auth.jwt_verifier import (
    CredentialConfigurationError,
    CredentialVerificationError,
    JWTBearerVerifier,
)
from app.core.config import Settings

SECRET = "phase4b-synthetic-secret-with-more-than-32-bytes"


def settings(**overrides):
    return Settings(
        app_env="test",
        auth_jwt_secret=SECRET,
        auth_jwt_issuer="test-issuer",
        auth_jwt_audience="test-api",
        _env_file=None,
        **overrides,
    )


def claims(user_id=None, **overrides):
    value = {
        "sub": str(user_id or uuid4()),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iss": "test-issuer",
        "aud": "test-api",
    }
    value.update(overrides)
    return value


def test_verified_signature_and_subject():
    user_id = uuid4()
    token = jwt.encode(claims(user_id), SECRET, algorithm="HS256")
    assert JWTBearerVerifier(settings()).verify(token).user_id == user_id


@pytest.mark.parametrize(
    "alterations",
    [
        {"exp": datetime.now(UTC) - timedelta(seconds=1)},
        {"exp": None},
        {"sub": None},
        {"sub": "not-a-uuid"},
        {"iss": "foreign-issuer"},
        {"iss": None},
        {"aud": "foreign-api"},
        {"aud": None},
        {"nbf": datetime.now(UTC) + timedelta(hours=1)},
    ],
)
def test_invalid_claims_rejected(alterations):
    value = claims(**alterations)
    value = {key: item for key, item in value.items() if item is not None}
    token = jwt.encode(value, SECRET, algorithm="HS256")
    with pytest.raises(CredentialVerificationError):
        JWTBearerVerifier(settings()).verify(token)


def test_wrong_signature_and_algorithm_rejected_without_leaking_secret():
    verifier = JWTBearerVerifier(settings())
    for token in (
        jwt.encode(claims(), "another-signing-key-with-over-32-bytes", algorithm="HS256"),
        jwt.encode(claims(), SECRET + "additional-synthetic-key-material", algorithm="HS512"),
        jwt.encode(claims(), key="", algorithm="none"),
        "not.a.jwt",
    ):
        with pytest.raises(CredentialVerificationError) as caught:
            verifier.verify(token)
        assert SECRET not in str(caught.value)


def test_missing_or_short_secret_disables_verifier():
    for value in (None, "short"):
        config = Settings(auth_jwt_secret=value, _env_file=None)
        with pytest.raises(CredentialConfigurationError):
            JWTBearerVerifier(config)


def test_example_secret_is_only_an_empty_placeholder():
    example = (Path(__file__).resolve().parents[3] / ".env.example").read_text(encoding="utf-8")
    assert "AUTH_JWT_SECRET=\n" in example.replace("\r\n", "\n")
    assert SECRET not in example
