"""Unit tests for the ECDSA primitives in ``core.crypto_keys`` (ID-05).

Strict TDD: this file was written BEFORE ``backend/core/crypto_keys.py``
existed. The RED run proves the contract; the GREEN run implements it.

The DER expectations below are hand-derived from the ASN.1 rules (a SEQUENCE
of two minimal-length INTEGERs, each prefixed with ``0x00`` when its high bit
is set) instead of being captured from the library, so a regression in the
encoder breaks these tests instead of silently redefining them.
"""
import base64

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from core.crypto_keys import (
    InvalidPublicKey,
    InvalidSignatureFormat,
    canonical_message,
    decode_spki_b64,
    load_p256_public_key,
    normalize_to_der,
    verify_signature,
)

# A known (r, s) pair: 32 bytes each with a clear high bit, so both DER
# INTEGERs are exactly 32 bytes and the SEQUENCE content is 68 bytes ("30 44").
KNOWN_R_HEX = "01" * 32
KNOWN_S_HEX = "02" * 32
KNOWN_DER_HEX = "3044" + "0220" + KNOWN_R_HEX + "0220" + KNOWN_S_HEX

# A second known pair whose r has its high bit set: the DER INTEGER needs the
# leading zero byte and becomes 33 bytes, so the content is 69 bytes ("30 45").
LEADING_ZERO_R_HEX = "80" + "00" * 31
LEADING_ZERO_S_HEX = "01" * 32
LEADING_ZERO_DER_HEX = (
    "3045" + "0221" + "00" + LEADING_ZERO_R_HEX + "0220" + LEADING_ZERO_S_HEX
)


def _p1363(r_hex: str, s_hex: str) -> bytes:
    """Build the raw IEEE P1363 blob (r || s) that WebCrypto produces."""
    return bytes.fromhex(r_hex + s_hex)


def _new_p256_key():
    return ec.generate_private_key(ec.SECP256R1())


def _spki(public_key) -> bytes:
    return public_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


# ---------------------------------------------------------------------------
# P1363 -> DER normalisation
# ---------------------------------------------------------------------------


def test_normalize_to_der_matches_the_known_der_vector():
    """A 64-byte P1363 blob becomes exactly the hand-derived DER encoding."""
    der = normalize_to_der(_p1363(KNOWN_R_HEX, KNOWN_S_HEX))

    assert der == bytes.fromhex(KNOWN_DER_HEX)
    assert der[0] == 0x30


def test_normalize_to_der_matches_the_leading_zero_der_vector():
    """A coordinate whose high bit is set keeps its mandatory leading zero."""
    der = normalize_to_der(_p1363(LEADING_ZERO_R_HEX, LEADING_ZERO_S_HEX))

    assert der == bytes.fromhex(LEADING_ZERO_DER_HEX)


def test_normalize_to_der_leaves_a_der_signature_unchanged():
    """A signature that already is DER is canonicalised to the same bytes."""
    der = bytes.fromhex(KNOWN_DER_HEX)

    assert normalize_to_der(der) == der


def test_normalize_to_der_round_trips_r_and_s():
    """decode_dss_signature(normalize_to_der(p1363)) recovers the original pair."""
    r = int(KNOWN_R_HEX, 16)
    s = int(KNOWN_S_HEX, 16)

    decoded = decode_dss_signature(normalize_to_der(_p1363(KNOWN_R_HEX, KNOWN_S_HEX)))

    assert decoded == (r, s)


@pytest.mark.parametrize(
    ("signature", "expected_length"),
    [
        (b"\x01" * 63, 63),
        (b"\x01" * 65, 65),
        (b"\x01" * 32, 32),
        (b"", 0),
    ],
)
def test_normalize_to_der_rejects_a_signature_that_is_neither_p1363_nor_der(
    signature, expected_length
):
    """A malformed signature is a typed error naming the byte count, not a 500."""
    with pytest.raises(InvalidSignatureFormat) as excinfo:
        normalize_to_der(signature)

    assert str(expected_length) in str(excinfo.value)


def test_normalize_to_der_rejects_garbage_that_looks_like_der():
    """A blob with a DER SEQUENCE tag but a broken body is still a format error."""
    broken = bytes.fromhex("30440220") + b"\x01" * 32

    with pytest.raises(InvalidSignatureFormat) as excinfo:
        normalize_to_der(broken)

    assert str(len(broken)) in str(excinfo.value)


# ---------------------------------------------------------------------------
# Public key loading
# ---------------------------------------------------------------------------


def test_load_p256_public_key_accepts_a_p256_spki_key():
    """A P-256 SPKI DER blob loads as an EllipticCurvePublicKey."""
    key = load_p256_public_key(_spki(_new_p256_key().public_key()))

    assert isinstance(key, ec.EllipticCurvePublicKey)
    assert key.curve.name == "secp256r1"
    assert key.key_size == 256


def test_load_p256_public_key_rejects_an_rsa_key():
    """An RSA key is refused with a reason that names RSA."""
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    with pytest.raises(InvalidPublicKey) as excinfo:
        load_p256_public_key(_spki(rsa_key.public_key()))

    assert "RSA" in str(excinfo.value)


def test_load_p256_public_key_rejects_another_curve():
    """A P-384 key is refused with a reason that names the curve."""
    p384 = ec.generate_private_key(ec.SECP384R1())

    with pytest.raises(InvalidPublicKey) as excinfo:
        load_p256_public_key(_spki(p384.public_key()))

    assert "secp384r1" in str(excinfo.value)


def test_load_p256_public_key_rejects_garbage_bytes():
    """Bytes that are not an SPKI blob are refused with a named reason."""
    with pytest.raises(InvalidPublicKey) as excinfo:
        load_p256_public_key(b"not-a-public-key")

    assert "SPKI" in str(excinfo.value)


def test_decode_spki_b64_returns_the_der_bytes():
    """A base64 SPKI blob decodes back to the exact DER bytes."""
    der = _spki(_new_p256_key().public_key())

    assert decode_spki_b64(base64.b64encode(der).decode()) == der


def test_decode_spki_b64_rejects_malformed_base64():
    """Malformed base64 is a typed error naming base64, never a 500."""
    with pytest.raises(InvalidPublicKey) as excinfo:
        decode_spki_b64("not base64!!")

    assert "base64" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def test_verify_signature_accepts_a_p1363_signature():
    """The raw 64-byte P1363 form produced by WebCrypto verifies."""
    private_key = _new_p256_key()
    message = b"peak-auth-v1\nchallenge\nnonce\nuser@example.com\norigin\ndeployment\n"
    der_signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der_signature)
    p1363_signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")

    verify_signature(private_key.public_key(), p1363_signature, message)


def test_verify_signature_accepts_a_der_signature():
    """A DER-encoded signature verifies through the same entry point."""
    private_key = _new_p256_key()
    message = b"peak-auth-v1\nchallenge\nnonce\nuser@example.com\norigin\ndeployment\n"
    der_signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))

    verify_signature(private_key.public_key(), der_signature, message)


def test_verify_signature_rejects_a_signature_from_another_key():
    """A signature made by a different private key is refused."""
    signer = _new_p256_key()
    other = _new_p256_key()
    message = b"peak-auth-v1\nchallenge\nnonce\nuser@example.com\norigin\ndeployment\n"
    der_signature = signer.sign(message, ec.ECDSA(hashes.SHA256()))

    with pytest.raises(InvalidSignature):
        verify_signature(other.public_key(), der_signature, message)


def test_verify_signature_rejects_a_signature_over_another_message():
    """A signature over a different message is refused."""
    private_key = _new_p256_key()
    der_signature = private_key.sign(b"another message", ec.ECDSA(hashes.SHA256()))

    with pytest.raises(InvalidSignature):
        verify_signature(
            private_key.public_key(),
            der_signature,
            b"peak-auth-v1\nchallenge\nnonce\nuser@example.com\norigin\ndeployment\n",
        )


def test_verify_signature_rejects_a_malformed_signature():
    """A malformed signature is a format error, not a verification failure."""
    private_key = _new_p256_key()

    with pytest.raises(InvalidSignatureFormat):
        verify_signature(private_key.public_key(), b"\x01" * 17, b"message")


# ---------------------------------------------------------------------------
# Canonical signed message
# ---------------------------------------------------------------------------


def test_canonical_message_uses_the_six_protocol_lines():
    """The signed message is the protocol version and five server-supplied values."""
    message = canonical_message(
        challenge_id="challenge-1",
        nonce="nonce-1",
        email="user@example.com",
        origin="http://localhost:7700",
        deployment_id="deployment-1",
    )

    assert message == (
        b"peak-auth-v1\n"
        b"challenge-1\n"
        b"nonce-1\n"
        b"user@example.com\n"
        b"http://localhost:7700\n"
        b"deployment-1\n"
    )


def test_canonical_message_binds_the_deployment_id():
    """Two deployments never produce the same signed message."""
    common = {
        "challenge_id": "challenge-1",
        "nonce": "nonce-1",
        "email": "user@example.com",
        "origin": "http://localhost:7700",
    }

    first = canonical_message(deployment_id="deployment-a", **common)
    second = canonical_message(deployment_id="deployment-b", **common)

    assert first != second
    assert b"deployment-a" in first
    assert b"deployment-b" in second
