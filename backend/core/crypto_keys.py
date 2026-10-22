"""ECDSA primitives for the passwordless identity layer.

The browser signs with WebCrypto ``ECDSA``/``P-256``, whose ``sign()`` returns
the raw IEEE P1363 form: 64 bytes, ``r || s``. ``cryptography``'s
``EllipticCurvePublicKey.verify()`` accepts DER only and rejects the raw form,
so every signature is normalised before it reaches ``verify()``.

The conversion is done with ``encode_dss_signature`` / ``decode_dss_signature``
from the library. This module never hand-rolls a DER encoder: the library
already performs the minimal-length integer encoding and the mandatory
leading-zero byte correctly, and a hand-rolled encoder reintroduces exactly
the defects the design exists to prevent.

A signature that is neither 64 bytes nor a parseable DER encoding is refused
with a typed error naming the byte count, so the caller can answer 400 instead
of leaking a 500.
"""
import base64
import binascii

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)

__all__ = [
    "CryptoKeyError",
    "InvalidPublicKey",
    "InvalidSignature",
    "InvalidSignatureFormat",
    "PROTOCOL_VERSION",
    "canonical_message",
    "decode_spki_b64",
    "load_p256_public_key",
    "normalize_to_der",
    "verify_signature",
]

#: Version tag of the signed-message protocol. Bumping it invalidates every
#: signature produced under an older protocol.
PROTOCOL_VERSION = "peak-auth-v1"

#: Length in bytes of the raw IEEE P1363 form of a P-256 signature (``r || s``).
P1363_SIGNATURE_LENGTH = 64

#: Length in bytes of one P-256 coordinate.
COORDINATE_LENGTH = 32

#: The only curve the identity layer accepts.
REQUIRED_CURVE_NAME = "secp256r1"


class CryptoKeyError(Exception):
    """Base class for the typed errors this module raises."""


class InvalidSignatureFormat(CryptoKeyError):
    """The signature is neither a 64-byte P1363 blob nor a parseable DER encoding."""


class InvalidPublicKey(CryptoKeyError):
    """The public key bytes are not a usable P-256 SPKI key."""


def _format_error(length: int) -> str:
    """The message of every rejected signature — it names the byte count."""
    return (
        f"expected a {P1363_SIGNATURE_LENGTH}-byte IEEE P1363 signature or a "
        f"DER-encoded ECDSA signature, got {length} bytes"
    )


def normalize_to_der(signature: bytes) -> bytes:
    """Return the DER encoding of ``signature``.

    A 64-byte blob is the raw IEEE P1363 form produced by WebCrypto and is
    converted from its two coordinates. Anything else is parsed as DER and
    re-emitted, which both validates and canonicalises it.
    """
    if len(signature) == P1363_SIGNATURE_LENGTH:
        r = int.from_bytes(signature[:COORDINATE_LENGTH], "big")
        s = int.from_bytes(signature[COORDINATE_LENGTH:], "big")
        try:
            return encode_dss_signature(r, s)
        except ValueError as exc:
            raise InvalidSignatureFormat(_format_error(len(signature))) from exc

    try:
        r, s = decode_dss_signature(signature)
    except ValueError as exc:
        raise InvalidSignatureFormat(_format_error(len(signature))) from exc

    return encode_dss_signature(r, s)


def decode_spki_b64(value: str) -> bytes:
    """Decode a base64-encoded SPKI public key into its DER bytes."""
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidPublicKey(f"public key is not valid base64: {exc}") from exc


def load_p256_public_key(spki_der: bytes) -> ec.EllipticCurvePublicKey:
    """Load an SPKI DER public key and require it to be a P-256 EC key.

    Anything else — an RSA key, another curve, or bytes that are not an SPKI
    blob at all — is refused with a reason the caller can name to the client.
    """
    try:
        key = serialization.load_der_public_key(spki_der)
    except (ValueError, TypeError) as exc:
        raise InvalidPublicKey(
            f"public key is not a valid SPKI DER blob: {exc}"
        ) from exc

    if not isinstance(key, ec.EllipticCurvePublicKey):
        raise InvalidPublicKey(
            f"public key must be an ECDSA P-256 key, got {type(key).__name__}"
        )
    if key.curve.name != REQUIRED_CURVE_NAME:
        raise InvalidPublicKey(
            f"public key must use the {REQUIRED_CURVE_NAME} curve, "
            f"got {key.curve.name}"
        )
    if key.key_size != 256:
        raise InvalidPublicKey(
            f"public key must be 256-bit, got {key.key_size} bits"
        )
    return key


def canonical_message(
    *,
    challenge_id: str,
    nonce: str,
    email: str,
    origin: str,
    deployment_id: str,
) -> bytes:
    """Build the canonical message the browser signs.

    Every value is server-supplied: the browser signs them verbatim and never
    invents one of them. ``deployment_id`` is a per-deployment uuid4 held by
    the server, so a signature captured on one deployment never verifies on
    another.
    """
    return (
        f"{PROTOCOL_VERSION}\n"
        f"{challenge_id}\n"
        f"{nonce}\n"
        f"{email}\n"
        f"{origin}\n"
        f"{deployment_id}\n"
    ).encode("utf-8")


def verify_signature(
    public_key: ec.EllipticCurvePublicKey,
    signature: bytes,
    message: bytes,
) -> None:
    """Verify ``signature`` over ``message``.

    Raises ``InvalidSignatureFormat`` when the signature encoding is malformed
    and ``InvalidSignature`` when the signature does not match the message.
    """
    der = normalize_to_der(signature)
    public_key.verify(der, message, ec.ECDSA(hashes.SHA256()))
