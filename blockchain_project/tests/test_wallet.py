# tests/test_wallet.py
"""
Tests for the Wallet class.

Covers:
  - Key pair generation
  - Public key is valid PEM
  - Transaction signing
  - Signature verification
  - Different wallets produce different keys
  - Wallet cannot sign transactions from other wallets
  - Wallet serialization roundtrip
"""

from blockchain.wallet import Wallet
from blockchain.transaction import Transaction

import pytest


class TestKeyGeneration:
    """Test ECDSA key pair generation."""

    def test_keys_are_generated(self):
        """A new wallet should have a private key, public key, and address."""
        wallet = Wallet()
        assert wallet.private_key is not None
        assert wallet.public_key is not None
        assert wallet.address is not None

    def test_address_is_pem(self):
        """The wallet address should be a PEM-encoded public key."""
        wallet = Wallet()
        assert wallet.address.startswith("-----BEGIN PUBLIC KEY-----")
        assert wallet.address.strip().endswith("-----END PUBLIC KEY-----")

    def test_private_key_is_pem(self):
        """The private key PEM should be properly formatted."""
        wallet = Wallet()
        pem = wallet.get_private_key_pem()
        assert pem.startswith("-----BEGIN PRIVATE KEY-----")
        assert pem.strip().endswith("-----END PRIVATE KEY-----")

    def test_unique_keys(self):
        """Two wallets should have different key pairs."""
        wallet1 = Wallet()
        wallet2 = Wallet()
        assert wallet1.address != wallet2.address
        assert wallet1.get_private_key_pem() != wallet2.get_private_key_pem()


class TestTransactionSigning:
    """Test transaction signing with wallets."""

    def test_sign_transaction(self):
        """A wallet should be able to sign its own transaction."""
        wallet = Wallet()
        tx = Transaction(
            sender=wallet.address,
            receiver="receiver",
            amount=10.0,
        )
        wallet.sign_transaction(tx)
        assert tx.signature != ""
        assert tx.is_valid() is True

    def test_cannot_sign_others_transaction(self):
        """A wallet should not sign a transaction from a different sender."""
        alice = Wallet()
        bob = Wallet()
        tx = Transaction(
            sender=alice.address,
            receiver="receiver",
            amount=10.0,
        )
        with pytest.raises(ValueError, match="not the sender"):
            bob.sign_transaction(tx)


class TestWalletSerialization:
    """Test wallet persistence."""

    def test_roundtrip(self):
        """A wallet should survive serialization and deserialization."""
        wallet = Wallet()
        data = wallet.to_dict()
        restored = Wallet.from_dict(data)

        assert restored.address == wallet.address
        assert restored.get_private_key_pem() == wallet.get_private_key_pem()

    def test_restored_wallet_can_sign(self):
        """A restored wallet should still be able to sign transactions."""
        wallet = Wallet()
        data = wallet.to_dict()
        restored = Wallet.from_dict(data)

        tx = Transaction(
            sender=restored.address,
            receiver="someone",
            amount=5.0,
        )
        restored.sign_transaction(tx)
        assert tx.is_valid() is True
