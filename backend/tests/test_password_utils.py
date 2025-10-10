"""Tests for password hashing helpers."""

from backend.app.utils.passwords import hash_password, verify_password


def test_hash_and_verify_roundtrip():
    password = "SecretPass123!"
    encoded = hash_password(password)

    assert encoded.startswith("pbkdf2_sha256$")
    assert verify_password(password, encoded)
    assert not verify_password("WrongPassword", encoded)


def test_hash_requires_non_empty_password():
    try:
        hash_password("")
    except ValueError as exc:
        assert "must not be empty" in str(exc)
    else:
        raise AssertionError("hash_password should raise for empty password")
