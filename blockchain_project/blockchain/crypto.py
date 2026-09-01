# blockchain/crypto.py
"""
Cryptographic Utilities for the Educational Blockchain.

This module centralizes all cryptographic operations:
  - SHA-256 hashing
  - ECDSA key pair generation (SECP256K1 curve — same as Bitcoin)
  - Digital signature creation and verification
  - Key serialization / deserialization (PEM format)

Why SECP256K1?
  Bitcoin uses the same elliptic curve, so using it here reinforces
  the connection between this educational project and real-world blockchains.

Why PEM format?
  PEM is a widely used, human-readable encoding for cryptographic keys.
  It makes keys easy to store, transmit, and inspect.
"""

import hashlib
import base64

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def hash_sha256(data: str) -> str:
    """
    Compute the SHA-256 hash of a string.

    SHA-256 produces a fixed-length 256-bit (64 hex character) digest.
    Even a tiny change in the input produces a completely different hash,
    which is the property that makes blockchain tamper-evident.

    Args:
        data: The string to hash.

    Returns:
        The hexadecimal digest (64 characters).
    """
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Key Generation
# ---------------------------------------------------------------------------

def generate_key_pair():
    """
    Generate an ECDSA key pair using the SECP256K1 curve.

    Returns:
        A tuple (private_key, public_key) of cryptography key objects.
    """
    private_key = ec.generate_private_key(ec.SECP256K1(), default_backend())
    public_key = private_key.public_key()
    return private_key, public_key


# ---------------------------------------------------------------------------
# Key Serialization
# ---------------------------------------------------------------------------

def serialize_public_key(public_key) -> str:
    """
    Serialize a public key to a PEM-encoded string.

    The PEM string acts as the wallet address in this blockchain.

    Args:
        public_key: An EllipticCurvePublicKey object.

    Returns:
        PEM-encoded public key as a string.
    """
    pem_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return pem_bytes.decode("utf-8")


def serialize_private_key(private_key) -> str:
    """
    Serialize a private key to a PEM-encoded string.

    WARNING: The private key must NEVER be shared or transmitted.
    It is only stored locally in the wallet.

    Args:
        private_key: An EllipticCurvePrivateKey object.

    Returns:
        PEM-encoded private key as a string.
    """
    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem_bytes.decode("utf-8")


# ---------------------------------------------------------------------------
# Key Deserialization
# ---------------------------------------------------------------------------

def deserialize_public_key(pem_str: str):
    """
    Deserialize a PEM-encoded string back to a public key object.

    Args:
        pem_str: PEM-encoded public key string.

    Returns:
        An EllipticCurvePublicKey object.
    """
    return serialization.load_pem_public_key(
        pem_str.encode("utf-8"),
        backend=default_backend(),
    )


def deserialize_private_key(pem_str: str):
    """
    Deserialize a PEM-encoded string back to a private key object.

    Args:
        pem_str: PEM-encoded private key string.

    Returns:
        An EllipticCurvePrivateKey object.
    """
    return serialization.load_pem_private_key(
        pem_str.encode("utf-8"),
        password=None,
        backend=default_backend(),
    )


# ---------------------------------------------------------------------------
# Digital Signatures
# ---------------------------------------------------------------------------

def sign_data(private_key, data: str) -> str:
    """
    Sign data using the ECDSA algorithm with SHA-256.

    The private key owner creates a signature that anyone can verify
    using the corresponding public key, without knowing the private key.

    Args:
        private_key: The signer's EllipticCurvePrivateKey.
        data: The string data to sign.

    Returns:
        Base64-encoded signature string.
    """
    signature_bytes = private_key.sign(
        data.encode("utf-8"),
        ec.ECDSA(hashes.SHA256()),
    )
    return base64.b64encode(signature_bytes).decode("utf-8")


def verify_signature(public_key_pem: str, data: str, signature_b64: str) -> bool:
    """
    Verify a digital signature using the signer's public key.

    This is how the network confirms that a transaction was really
    authorized by the owner of the sending wallet.

    Args:
        public_key_pem: PEM-encoded public key of the signer.
        data: The original data that was signed.
        signature_b64: Base64-encoded signature to verify.

    Returns:
        True if the signature is valid, False otherwise.
    """
    try:
        public_key = deserialize_public_key(public_key_pem)
        signature_bytes = base64.b64decode(signature_b64)
        public_key.verify(
            signature_bytes,
            data.encode("utf-8"),
            ec.ECDSA(hashes.SHA256()),
        )
        return True
    except (InvalidSignature, Exception):
        return False
