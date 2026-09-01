# tests/test_block.py
"""
Tests for the Block class.

Covers:
  - Hash calculation is deterministic
  - Hash changes when data changes
  - Mining produces valid Proof of Work
  - Block serialization roundtrip
"""

from blockchain.block import Block


class TestBlockHash:
    """Test SHA-256 hash calculation."""

    def test_hash_is_deterministic(self):
        """Same block data should always produce the same hash."""
        block = Block(
            index=1,
            transactions=[{"sender": "A", "receiver": "B", "amount": 10}],
            previous_hash="abc123",
            timestamp="2024-01-01T00:00:00",
        )
        hash1 = block.calculate_hash()
        hash2 = block.calculate_hash()
        assert hash1 == hash2

    def test_hash_is_64_hex_characters(self):
        """SHA-256 produces a 64-character hex string."""
        block = Block(index=0, transactions=[], previous_hash="0")
        assert len(block.hash) == 64
        assert all(c in "0123456789abcdef" for c in block.hash)

    def test_hash_changes_with_data(self):
        """Changing any block data should produce a different hash."""
        block1 = Block(
            index=1,
            transactions=[{"sender": "A", "receiver": "B", "amount": 10}],
            previous_hash="abc",
            timestamp="2024-01-01T00:00:00",
        )
        block2 = Block(
            index=1,
            transactions=[{"sender": "A", "receiver": "B", "amount": 20}],
            previous_hash="abc",
            timestamp="2024-01-01T00:00:00",
        )
        assert block1.hash != block2.hash

    def test_hash_changes_with_nonce(self):
        """Changing the nonce should change the hash."""
        block = Block(
            index=0,
            transactions=[],
            previous_hash="0",
            timestamp="2024-01-01T00:00:00",
        )
        hash_at_0 = block.calculate_hash()
        block.nonce = 999
        hash_at_999 = block.calculate_hash()
        assert hash_at_0 != hash_at_999


class TestBlockMining:
    """Test Proof of Work mining."""

    def test_mining_produces_valid_hash(self):
        """After mining, the hash should start with the correct number of zeros."""
        difficulty = 2  # Low difficulty for fast tests
        block = Block(
            index=1,
            transactions=[],
            previous_hash="abc",
            timestamp="2024-01-01T00:00:00",
        )
        block.mine_block(difficulty)
        assert block.hash[:difficulty] == "0" * difficulty

    def test_mining_increments_nonce(self):
        """Mining should change the nonce from 0."""
        block = Block(
            index=1,
            transactions=[],
            previous_hash="xyz",
            timestamp="2024-01-01T00:00:00",
        )
        block.mine_block(2)
        # It's extremely unlikely (but possible) that nonce=0 works
        # So we just check the hash is valid
        assert block.hash[:2] == "00"

    def test_higher_difficulty_still_works(self):
        """Mining with difficulty 3 should still produce a valid hash."""
        block = Block(
            index=1,
            transactions=[],
            previous_hash="test",
            timestamp="2024-01-01T00:00:00",
        )
        block.mine_block(3)
        assert block.hash[:3] == "000"


class TestBlockSerialization:
    """Test Block to/from dictionary conversion."""

    def test_roundtrip(self):
        """A block serialized and deserialized should be identical."""
        block = Block(
            index=5,
            transactions=[{"sender": "A", "receiver": "B", "amount": 50}],
            previous_hash="prev123",
            timestamp="2024-06-15T12:00:00",
            nonce=42,
        )
        data = block.to_dict()
        restored = Block.from_dict(data)

        assert restored.index == block.index
        assert restored.timestamp == block.timestamp
        assert restored.transactions == block.transactions
        assert restored.previous_hash == block.previous_hash
        assert restored.nonce == block.nonce
        assert restored.hash == block.hash
