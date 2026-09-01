# tests/test_transaction.py
"""
Tests for the Transaction class.

Covers:
  - Valid signed transaction passes verification
  - Modified transaction fails verification
  - Unsigned transaction fails verification
  - Mining reward transaction is valid
  - Transaction serialization roundtrip
"""

from blockchain.transaction import Transaction
from blockchain.wallet import Wallet


class TestTransactionSignature:
    """Test digital signature creation and verification."""

    def test_valid_signature(self):
        """A properly signed transaction should pass verification."""
        wallet = Wallet()
        tx = Transaction(
            sender=wallet.address,
            receiver="someone",
            amount=10.0,
        )
        wallet.sign_transaction(tx)
        assert tx.is_valid() is True

    def test_modified_transaction_fails(self):
        """Modifying a signed transaction should invalidate the signature."""
        wallet = Wallet()
        tx = Transaction(
            sender=wallet.address,
            receiver="someone",
            amount=10.0,
        )
        wallet.sign_transaction(tx)

        # Tamper with the amount
        tx.amount = 99999.0

        assert tx.is_valid() is False

    def test_unsigned_transaction_fails(self):
        """A transaction without a signature should be invalid."""
        tx = Transaction(
            sender="some_public_key",
            receiver="someone",
            amount=10.0,
        )
        assert tx.is_valid() is False

    def test_wrong_signer_fails(self):
        """A transaction signed by the wrong wallet should be invalid."""
        alice = Wallet()
        bob = Wallet()
        tx = Transaction(
            sender=alice.address,
            receiver="someone",
            amount=10.0,
        )
        # Bob tries to sign Alice's transaction
        tx.sign(bob.private_key)
        assert tx.is_valid() is False


class TestMiningReward:
    """Test mining reward transactions."""

    def test_system_transaction_is_valid(self):
        """Mining reward transactions (sender='SYSTEM') are always valid."""
        tx = Transaction(
            sender="SYSTEM",
            receiver="some_miner_address",
            amount=10.0,
        )
        assert tx.is_valid() is True

    def test_system_transaction_no_signature_needed(self):
        """Mining rewards don't need a signature."""
        tx = Transaction(
            sender="SYSTEM",
            receiver="some_miner_address",
            amount=10.0,
            signature="",
        )
        assert tx.is_valid() is True


class TestTransactionSerialization:
    """Test Transaction to/from dictionary conversion."""

    def test_roundtrip(self):
        """A transaction serialized and deserialized should be identical."""
        wallet = Wallet()
        tx = Transaction(
            sender=wallet.address,
            receiver="receiver_address",
            amount=25.0,
        )
        wallet.sign_transaction(tx)

        data = tx.to_dict()
        restored = Transaction.from_dict(data)

        assert restored.sender == tx.sender
        assert restored.receiver == tx.receiver
        assert restored.amount == tx.amount
        assert restored.timestamp == tx.timestamp
        assert restored.signature == tx.signature
        assert restored.is_valid() is True

    def test_hash_is_deterministic(self):
        """Same transaction data should produce the same hash."""
        tx = Transaction(
            sender="A",
            receiver="B",
            amount=10.0,
            timestamp="2024-01-01T00:00:00",
        )
        assert tx.calculate_hash() == tx.calculate_hash()
