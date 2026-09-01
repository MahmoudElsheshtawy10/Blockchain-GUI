# tests/test_blockchain.py
"""
Tests for the Blockchain class.

Covers:
  - Genesis Block exists
  - New blocks can be added via mining
  - Chain validation works
  - Tampering is detected (hash mismatch)
  - Tampering is detected (previous_hash mismatch)
  - Balance calculation is correct
  - Mining reward works
  - Persistence (save/load)
"""

import os
import tempfile

from blockchain.blockchain import Blockchain
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet


class TestGenesisBlock:
    """Test Genesis Block creation."""

    def test_genesis_exists(self):
        """A new blockchain should have exactly one block (Genesis)."""
        bc = Blockchain(difficulty=2)
        assert len(bc.chain) == 1

    def test_genesis_index_is_zero(self):
        """The Genesis Block should have index 0."""
        bc = Blockchain(difficulty=2)
        assert bc.chain[0].index == 0

    def test_genesis_previous_hash(self):
        """The Genesis Block's previous_hash should be '0'."""
        bc = Blockchain(difficulty=2)
        assert bc.chain[0].previous_hash == "0"

    def test_genesis_is_mined(self):
        """The Genesis Block should satisfy Proof of Work."""
        bc = Blockchain(difficulty=2)
        assert bc.chain[0].hash[:2] == "00"


class TestBlockchainMining:
    """Test mining and block addition."""

    def test_mine_adds_block(self):
        """Mining should add a new block to the chain."""
        bc = Blockchain(difficulty=2, mining_reward=10.0)
        wallet = Wallet()

        # Add a dummy transaction to trigger mining
        tx = Transaction(sender="SYSTEM", receiver=wallet.address, amount=0)
        bc.pending_transactions.append(tx)

        bc.mine_pending_transactions(wallet.address)
        assert len(bc.chain) == 2

    def test_blocks_are_linked(self):
        """Each block's previous_hash should match the previous block's hash."""
        bc = Blockchain(difficulty=2, mining_reward=10.0)
        wallet = Wallet()

        tx = Transaction(sender="SYSTEM", receiver=wallet.address, amount=0)
        bc.pending_transactions.append(tx)
        bc.mine_pending_transactions(wallet.address)

        assert bc.chain[1].previous_hash == bc.chain[0].hash

    def test_mining_reward(self):
        """The miner should receive the mining reward."""
        bc = Blockchain(difficulty=2, mining_reward=10.0)
        wallet = Wallet()

        tx = Transaction(sender="SYSTEM", receiver=wallet.address, amount=0)
        bc.pending_transactions.append(tx)
        bc.mine_pending_transactions(wallet.address)

        balance = bc.get_balance(wallet.address)
        assert balance == 10.0


class TestChainValidation:
    """Test blockchain validation."""

    def test_valid_chain(self):
        """A properly constructed chain should be valid."""
        bc = Blockchain(difficulty=2, mining_reward=10.0)
        wallet = Wallet()

        tx = Transaction(sender="SYSTEM", receiver=wallet.address, amount=0)
        bc.pending_transactions.append(tx)
        bc.mine_pending_transactions(wallet.address)

        is_valid, message = bc.is_chain_valid()
        assert is_valid is True

    def test_tamper_detection_hash(self):
        """Tampering with block data should be detected via hash mismatch."""
        bc = Blockchain(difficulty=2, mining_reward=10.0)
        alice = Wallet()
        bob = Wallet()

        # Give Alice coins
        tx1 = Transaction(sender="SYSTEM", receiver=alice.address, amount=0)
        bc.pending_transactions.append(tx1)
        bc.mine_pending_transactions(alice.address)

        # Alice sends to Bob
        tx2 = Transaction(sender=alice.address, receiver=bob.address, amount=5.0)
        alice.sign_transaction(tx2)
        bc.add_transaction(tx2)
        bc.mine_pending_transactions(alice.address)

        # Tamper with block
        bc.tamper_block(2, 99999.0)

        is_valid, message = bc.is_chain_valid()
        assert is_valid is False
        assert "hash does not match" in message

    def test_tamper_detection_recomputed(self):
        """Even if the attacker recalculates the hash, the chain link breaks."""
        bc = Blockchain(difficulty=2, mining_reward=10.0)
        wallet = Wallet()

        tx = Transaction(sender="SYSTEM", receiver=wallet.address, amount=0)
        bc.pending_transactions.append(tx)
        bc.mine_pending_transactions(wallet.address)

        # Manually tamper and recalculate hash
        bc.chain[1].transactions[0]["amount"] = 99999
        bc.chain[1].hash = bc.chain[1].calculate_hash()

        is_valid, message = bc.is_chain_valid()
        # The PoW check or the chain link (if more blocks exist) will fail
        assert is_valid is False


class TestBalances:
    """Test balance calculation."""

    def test_initial_balance_is_zero(self):
        """A new wallet should have zero balance."""
        bc = Blockchain(difficulty=2)
        wallet = Wallet()
        assert bc.get_balance(wallet.address) == 0.0

    def test_balance_after_mining(self):
        """Miner should receive the mining reward."""
        bc = Blockchain(difficulty=2, mining_reward=10.0)
        wallet = Wallet()

        tx = Transaction(sender="SYSTEM", receiver=wallet.address, amount=0)
        bc.pending_transactions.append(tx)
        bc.mine_pending_transactions(wallet.address)

        assert bc.get_balance(wallet.address) == 10.0

    def test_balance_after_transfer(self):
        """Balances should update correctly after a transfer."""
        bc = Blockchain(difficulty=2, mining_reward=10.0)
        alice = Wallet()
        bob = Wallet()

        # Mine to give Alice coins
        tx1 = Transaction(sender="SYSTEM", receiver=alice.address, amount=0)
        bc.pending_transactions.append(tx1)
        bc.mine_pending_transactions(alice.address)

        # Alice sends 3 to Bob
        tx2 = Transaction(sender=alice.address, receiver=bob.address, amount=3.0)
        alice.sign_transaction(tx2)
        bc.add_transaction(tx2)
        bc.mine_pending_transactions(alice.address)

        # Alice: 10 (reward) - 3 (sent) + 10 (second mining reward) = 17
        # Bob: 3
        assert bc.get_balance(alice.address) == 17.0
        assert bc.get_balance(bob.address) == 3.0

    def test_insufficient_balance_rejected(self):
        """Transactions with insufficient balance should be rejected."""
        bc = Blockchain(difficulty=2, mining_reward=10.0)
        alice = Wallet()
        bob = Wallet()

        # Alice has 0 coins, tries to send 100
        tx = Transaction(sender=alice.address, receiver=bob.address, amount=100.0)
        alice.sign_transaction(tx)
        success, message = bc.add_transaction(tx)

        assert success is False
        assert "Insufficient balance" in message


class TestPersistence:
    """Test saving and loading the blockchain."""

    def test_save_and_load(self):
        """The blockchain should survive save/load roundtrip."""
        bc = Blockchain(difficulty=2, mining_reward=10.0)
        wallet = Wallet()

        tx = Transaction(sender="SYSTEM", receiver=wallet.address, amount=0)
        bc.pending_transactions.append(tx)
        bc.mine_pending_transactions(wallet.address)

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            bc.save_chain(filepath)

            # Load into new blockchain
            bc2 = Blockchain(difficulty=2)
            assert bc2.load_chain(filepath) is True
            assert len(bc2.chain) == len(bc.chain)
            assert bc2.chain[-1].hash == bc.chain[-1].hash
        finally:
            os.unlink(filepath)

    def test_load_nonexistent_file(self):
        """Loading from a nonexistent file should return False."""
        bc = Blockchain(difficulty=2)
        assert bc.load_chain("nonexistent_file.json") is False
