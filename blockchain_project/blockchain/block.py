# blockchain/block.py
"""
Block Class for the Educational Blockchain.

A Block is the fundamental unit of a blockchain. Each block contains:
  - index:          Position in the chain (0 for Genesis Block)
  - timestamp:      When the block was created (ISO 8601)
  - transactions:   List of transactions included in this block
  - previous_hash:  Hash of the previous block (creates the chain link)
  - nonce:          Number changed during mining to find a valid hash
  - hash:           SHA-256 hash of this block's contents

How are blocks connected?
  Each block stores the hash of the previous block. If someone modifies
  a past block, its hash changes, which breaks the link to the next block.
  This is the core security mechanism of blockchain.
"""

import json
from datetime import datetime, timezone

from blockchain.crypto import hash_sha256


class Block:
    """
    Represents a single block in the blockchain.

    Attributes:
        index (int): Block position in the chain.
        timestamp (str): ISO 8601 timestamp of block creation.
        transactions (list): List of transaction dictionaries.
        previous_hash (str): Hash of the previous block.
        nonce (int): Value incremented during mining.
        hash (str): SHA-256 hash of this block.
    """

    def __init__(
        self,
        index: int,
        transactions: list,
        previous_hash: str,
        timestamp: str = None,
        nonce: int = 0,
        block_hash: str = None,
    ):
        """
        Initialize a new Block.

        Args:
            index: Block number in the chain.
            transactions: List of transaction dicts to include.
            previous_hash: Hash of the previous block.
            timestamp: ISO 8601 string (auto-generated if None).
            nonce: Starting nonce value (default 0).
            block_hash: Pre-computed hash (used when loading from JSON).
        """
        self.index = index
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        # If a hash was provided (e.g., from JSON), use it; otherwise compute it
        self.hash = block_hash if block_hash else self.calculate_hash()

    def calculate_hash(self) -> str:
        """
        Calculate the SHA-256 hash of this block.

        The hash is computed from ALL important block data:
          index + timestamp + transactions + previous_hash + nonce

        Transactions are serialized with sorted keys to ensure
        the same data always produces the same hash (deterministic).

        Returns:
            The 64-character hexadecimal SHA-256 hash.
        """
        # Build a single string from all block data
        block_string = json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "transactions": self.transactions,
                "previous_hash": self.previous_hash,
                "nonce": self.nonce,
            },
            sort_keys=True,  # Deterministic key ordering
        )
        return hash_sha256(block_string)

    def mine_block(self, difficulty: int) -> None:
        """
        Mine this block using Proof of Work.

        The mining process increments the nonce until the block's hash
        starts with a specific number of leading zeros (the 'difficulty').

        For example, difficulty=4 means the hash must start with "0000".

        This is computationally expensive on purpose — it's what makes
        the blockchain resistant to tampering.

        Args:
            difficulty: Number of leading zeros required in the hash.
        """
        target = "0" * difficulty  # e.g., "0000" for difficulty=4

        # Keep trying different nonce values until we find a valid hash
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()

    def to_dict(self) -> dict:
        """
        Serialize this block to a dictionary (for JSON storage).

        Returns:
            Dictionary representation of the block.
        """
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        """
        Deserialize a block from a dictionary (loaded from JSON).

        Args:
            data: Dictionary containing block fields.

        Returns:
            A Block instance with the stored data.
        """
        return cls(
            index=data["index"],
            transactions=data["transactions"],
            previous_hash=data["previous_hash"],
            timestamp=data["timestamp"],
            nonce=data["nonce"],
            block_hash=data["hash"],
        )

    def __repr__(self) -> str:
        return (
            f"Block(index={self.index}, hash={self.hash[:16]}..., "
            f"nonce={self.nonce}, txns={len(self.transactions)})"
        )
