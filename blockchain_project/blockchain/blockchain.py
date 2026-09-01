# blockchain/blockchain.py
"""
Blockchain Class for the Educational Blockchain.

The Blockchain is the core data structure — an ordered list of Blocks
where each block is linked to the previous one via its hash.

Key concepts implemented here:
  - Genesis Block:  The very first block in the chain (index 0).
  - Mining:         Proof of Work — finding a nonce that produces a valid hash.
  - Difficulty:     How many leading zeros the hash must have.
  - Validation:     Checking that no block has been tampered with.
  - Balances:       Calculating how many coins each address owns.
  - Persistence:    Saving/loading the chain to/from JSON.

Why is tampering detected?
  If you change a transaction in block #2, its hash changes.
  Block #3 stores the old hash of block #2 as 'previous_hash'.
  Now block #3's previous_hash doesn't match block #2's new hash.
  The validation function catches this immediately.
"""

import json
import os
from typing import Optional

from blockchain.block import Block
from blockchain.transaction import Transaction


class Blockchain:
    """
    The main Blockchain data structure.

    Attributes:
        chain (list[Block]): The ordered list of mined blocks.
        pending_transactions (list[Transaction]): Transactions waiting to be mined.
        difficulty (int): Number of leading zeros required in block hashes.
        mining_reward (float): Coins awarded to the miner of each block.
    """

    def __init__(self, difficulty: int = 4, mining_reward: float = 10.0):
        """
        Initialize a new Blockchain.

        If no existing chain is loaded, a Genesis Block is created.

        Args:
            difficulty: Number of leading zeros for Proof of Work (default 4).
            mining_reward: Coins awarded per mined block (default 10.0).
        """
        self.chain: list[Block] = []
        self.pending_transactions: list[Transaction] = []
        self.difficulty = difficulty
        self.mining_reward = mining_reward

        # Create the Genesis Block
        self.chain.append(self.create_genesis_block())

    def create_genesis_block(self) -> Block:
        """
        Create the Genesis Block — the first block in the blockchain.

        The Genesis Block is special because:
          - It has index 0
          - It has no previous block, so previous_hash is "0"
          - It contains no real transactions
          - It is mined like any other block (Proof of Work)

        Returns:
            The mined Genesis Block.
        """
        genesis = Block(
            index=0,
            transactions=[],
            previous_hash="0",
        )
        genesis.mine_block(self.difficulty)
        return genesis

    def get_latest_block(self) -> Block:
        """
        Get the most recent block in the chain.

        Returns:
            The last Block in the chain list.
        """
        return self.chain[-1]

    def add_transaction(self, transaction: Transaction) -> tuple[bool, str]:
        """
        Add a transaction to the pending pool after validation.

        Validation checks:
          1. Sender and receiver must be specified.
          2. Amount must be positive.
          3. The transaction must have a valid digital signature.
          4. The sender must have sufficient balance (except SYSTEM).

        Args:
            transaction: The transaction to add.

        Returns:
            Tuple of (success: bool, message: str).
        """
        # Basic field validation
        if not transaction.sender or not transaction.receiver:
            return False, "Transaction must have a sender and receiver."

        if transaction.amount <= 0:
            return False, "Transaction amount must be positive."

        # Mining rewards bypass signature and balance checks
        if transaction.sender != "SYSTEM":
            # Verify digital signature
            if not transaction.is_valid():
                return False, "Transaction signature is invalid."

            # Check balance
            balance = self.get_balance(transaction.sender)
            if balance < transaction.amount:
                return (
                    False,
                    f"Insufficient balance. Have: {balance}, Need: {transaction.amount}",
                )

        self.pending_transactions.append(transaction)
        return True, "Transaction added to pending pool."

    def mine_pending_transactions(
        self,
        miner_address: str,
        progress_callback=None,
    ) -> Block:
        """
        Mine all pending transactions into a new block.

        Steps:
          1. Create a mining reward transaction for the miner.
          2. Bundle all pending transactions into a new block.
          3. Mine the block (Proof of Work).
          4. Add the mined block to the chain.
          5. Clear the pending transactions.

        The mining reward is added to PENDING transactions so the miner
        receives the reward in the NEXT block. This is a simplification
        for educational purposes.

        Args:
            miner_address: Public key address of the miner.
            progress_callback: Optional function called during mining
                               with (nonce, hash) for GUI updates.

        Returns:
            The newly mined Block.
        """
        # Create mining reward transaction
        reward_tx = Transaction(
            sender="SYSTEM",
            receiver=miner_address,
            amount=self.mining_reward,
        )

        # Bundle transactions (include reward + all pending)
        all_transactions = [reward_tx] + self.pending_transactions
        transaction_dicts = [tx.to_dict() for tx in all_transactions]

        # Create the new block
        block = Block(
            index=len(self.chain),
            transactions=transaction_dicts,
            previous_hash=self.get_latest_block().hash,
        )

        # Mine the block (Proof of Work)
        if progress_callback:
            # Mine with progress reporting for GUI
            target = "0" * self.difficulty
            while block.hash[:self.difficulty] != target:
                block.nonce += 1
                block.hash = block.calculate_hash()
                # Report progress every 1000 nonces to avoid GUI lag
                if block.nonce % 1000 == 0:
                    progress_callback(block.nonce, block.hash)
            # Final callback with the valid hash
            progress_callback(block.nonce, block.hash)
        else:
            block.mine_block(self.difficulty)

        # Add to chain and clear pending
        self.chain.append(block)
        self.pending_transactions = []

        return block

    def get_balance(self, address: str) -> float:
        """
        Calculate the balance of a wallet address.

        Scans ALL confirmed transactions in the blockchain:
          - Incoming transactions (receiver == address) ADD to balance
          - Outgoing transactions (sender == address) SUBTRACT from balance

        Args:
            address: The public key PEM string of the wallet.

        Returns:
            The current balance as a float.
        """
        balance = 0.0

        for block in self.chain:
            for tx_dict in block.transactions:
                if tx_dict["receiver"] == address:
                    balance += tx_dict["amount"]
                if tx_dict["sender"] == address:
                    balance -= tx_dict["amount"]

        return balance

    def is_chain_valid(self) -> tuple[bool, str]:
        """
        Validate the entire blockchain.

        Performs four checks on every block (except Genesis):
          1. Stored hash matches recalculated hash.
          2. previous_hash matches the actual previous block's hash.
          3. All transactions have valid digital signatures.
          4. Hash satisfies the Proof of Work difficulty requirement.

        Returns:
            Tuple of (is_valid: bool, message: str).
            If invalid, the message explains which check failed and where.
        """
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            # Check 1: Hash integrity
            recalculated = current_block.calculate_hash()
            if current_block.hash != recalculated:
                return (
                    False,
                    f"Block #{current_block.index}: hash does not match "
                    f"its calculated hash. The block data has been tampered with.",
                )

            # Check 2: Chain link integrity
            if current_block.previous_hash != previous_block.hash:
                return (
                    False,
                    f"Block #{current_block.index}: previous_hash does not match "
                    f"Block #{previous_block.index}'s hash. The chain link is broken.",
                )

            # Check 3: Transaction signatures
            for tx_dict in current_block.transactions:
                tx = Transaction.from_dict(tx_dict)
                if not tx.is_valid():
                    return (
                        False,
                        f"Block #{current_block.index}: contains a transaction "
                        f"with an invalid signature.",
                    )

            # Check 4: Proof of Work
            target = "0" * self.difficulty
            if current_block.hash[:self.difficulty] != target:
                return (
                    False,
                    f"Block #{current_block.index}: hash does not satisfy "
                    f"the Proof of Work requirement (difficulty {self.difficulty}).",
                )

        return True, "Blockchain is valid. All checks passed."

    def tamper_block(self, block_index: int, new_amount: float) -> str:
        """
        Intentionally modify a block's transaction data for demonstration.

        This is NOT a normal blockchain operation — it's used to show
        students how the blockchain detects tampering.

        Args:
            block_index: Index of the block to tamper with.
            new_amount: New amount to set on the first non-reward transaction.

        Returns:
            Description of what was changed.
        """
        if block_index <= 0 or block_index >= len(self.chain):
            return "Cannot tamper: invalid block index."

        block = self.chain[block_index]

        # Find the first non-reward transaction
        for tx in block.transactions:
            if tx["sender"] != "SYSTEM":
                old_amount = tx["amount"]
                tx["amount"] = new_amount
                # NOTE: We intentionally do NOT recalculate the hash.
                # This is what makes the tampering detectable!
                return (
                    f"Tampered Block #{block_index}: "
                    f"changed amount from {old_amount} to {new_amount}. "
                    f"Hash was NOT recalculated — validation will now fail."
                )

        return f"Block #{block_index} has no user transactions to tamper with."

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_chain(self, filepath: str = "data/blockchain.json") -> None:
        """
        Save the blockchain to a JSON file.

        Args:
            filepath: Path to the JSON file (relative or absolute).
        """
        # Ensure directory exists
        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)

        data = {
            "difficulty": self.difficulty,
            "mining_reward": self.mining_reward,
            "chain": [block.to_dict() for block in self.chain],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_chain(self, filepath: str = "data/blockchain.json") -> bool:
        """
        Load a blockchain from a JSON file.

        Replaces the current chain if the file exists and is valid.

        Args:
            filepath: Path to the JSON file.

        Returns:
            True if the chain was loaded successfully, False otherwise.
        """
        if not os.path.exists(filepath):
            return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.difficulty = data.get("difficulty", self.difficulty)
            self.mining_reward = data.get("mining_reward", self.mining_reward)
            self.chain = [Block.from_dict(b) for b in data["chain"]]
            return True
        except (json.JSONDecodeError, KeyError, Exception) as e:
            print(f"Error loading blockchain: {e}")
            return False

    def to_dict(self) -> dict:
        """
        Serialize the entire blockchain to a dictionary.

        Used for network transmission between nodes.

        Returns:
            Dictionary with chain data, difficulty, and mining reward.
        """
        return {
            "difficulty": self.difficulty,
            "mining_reward": self.mining_reward,
            "chain": [block.to_dict() for block in self.chain],
            "length": len(self.chain),
        }

    def replace_chain(self, chain_data: list[dict]) -> bool:
        """
        Replace the current chain with a new one (used in consensus).

        Only replaces if the new chain is longer AND valid.

        Args:
            chain_data: List of block dictionaries from another node.

        Returns:
            True if the chain was replaced, False otherwise.
        """
        new_chain = [Block.from_dict(b) for b in chain_data]

        # The new chain must be longer
        if len(new_chain) <= len(self.chain):
            return False

        # Temporarily swap chains to validate
        old_chain = self.chain
        self.chain = new_chain
        is_valid, _ = self.is_chain_valid()

        if is_valid:
            return True  # Keep the new chain
        else:
            self.chain = old_chain  # Revert
            return False

    def __repr__(self) -> str:
        return f"Blockchain(blocks={len(self.chain)}, difficulty={self.difficulty})"
