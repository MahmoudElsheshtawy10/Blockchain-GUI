# blockchain/transaction.py
"""
Transaction Class for the Educational Blockchain.

A Transaction represents a transfer of coins from one wallet to another.
Each transaction contains:
  - sender:     Public key (address) of the sender, or "SYSTEM" for mining rewards
  - receiver:   Public key (address) of the receiver
  - amount:     Number of coins to transfer
  - timestamp:  When the transaction was created
  - signature:  Digital signature proving the sender authorized this transaction

Why digital signatures?
  Without signatures, anyone could create a fake transaction saying
  "Alice sends 1000 coins to Eve." Digital signatures prove that only
  Alice (who owns the private key) could have created the transaction.
"""

import json
from datetime import datetime, timezone

from blockchain.crypto import hash_sha256, sign_data, verify_signature


class Transaction:
    """
    Represents a single transaction in the blockchain.

    Attributes:
        sender (str): Sender's public key (PEM) or "SYSTEM" for rewards.
        receiver (str): Receiver's public key (PEM).
        amount (float): Amount of coins to transfer.
        timestamp (str): ISO 8601 timestamp.
        signature (str): Base64-encoded ECDSA signature.
    """

    def __init__(
        self,
        sender: str,
        receiver: str,
        amount: float,
        timestamp: str = None,
        signature: str = "",
    ):
        """
        Initialize a new Transaction.

        Args:
            sender: Sender's public key PEM string, or "SYSTEM" for mining rewards.
            receiver: Receiver's public key PEM string.
            amount: Number of coins to transfer (must be > 0).
            timestamp: ISO 8601 string (auto-generated if None).
            signature: Pre-existing signature (used when loading from JSON).
        """
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.signature = signature

    def calculate_hash(self) -> str:
        """
        Calculate a hash of the transaction data.

        This hash is what gets signed by the sender's private key.
        It includes sender, receiver, amount, and timestamp to ensure
        every part of the transaction is protected.

        Returns:
            SHA-256 hex digest of the transaction data.
        """
        tx_string = json.dumps(
            {
                "sender": self.sender,
                "receiver": self.receiver,
                "amount": self.amount,
                "timestamp": self.timestamp,
            },
            sort_keys=True,
        )
        return hash_sha256(tx_string)

    def sign(self, private_key) -> None:
        """
        Sign this transaction with the sender's private key.

        The signature proves that the owner of the sending wallet
        authorized this specific transaction. No one else can create
        a valid signature without the private key.

        Args:
            private_key: The sender's ECDSA private key object.
        """
        tx_hash = self.calculate_hash()
        self.signature = sign_data(private_key, tx_hash)

    def is_valid(self) -> bool:
        """
        Verify that this transaction has a valid digital signature.

        Special case: Mining reward transactions (sender="SYSTEM")
        are created by the system and do not require a signature.

        Returns:
            True if the transaction is valid, False otherwise.
        """
        # Mining reward transactions are always valid
        if self.sender == "SYSTEM":
            return True

        # A transaction without a signature is invalid
        if not self.signature:
            return False

        # Verify the signature using the sender's public key
        tx_hash = self.calculate_hash()
        return verify_signature(self.sender, tx_hash, self.signature)

    def to_dict(self) -> dict:
        """
        Serialize this transaction to a dictionary (for JSON storage).

        Returns:
            Dictionary representation of the transaction.
        """
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        """
        Deserialize a transaction from a dictionary (loaded from JSON).

        Args:
            data: Dictionary containing transaction fields.

        Returns:
            A Transaction instance with the stored data.
        """
        return cls(
            sender=data["sender"],
            receiver=data["receiver"],
            amount=data["amount"],
            timestamp=data.get("timestamp", ""),
            signature=data.get("signature", ""),
        )

    def __repr__(self) -> str:
        sender_short = self.sender[:20] + "..." if len(self.sender) > 20 else self.sender
        receiver_short = self.receiver[:20] + "..." if len(self.receiver) > 20 else self.receiver
        return f"Transaction({sender_short} -> {receiver_short}: {self.amount})"
