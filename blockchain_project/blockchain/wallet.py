# blockchain/wallet.py
"""
Wallet Class for the Educational Blockchain.

A Wallet is like a digital bank account. It contains:
  - A private key:  Secret — used to sign transactions (like a password)
  - A public key:   Shared — used as the wallet address (like a bank account number)

How does it work?
  1. The wallet generates a key pair (private + public) using ECDSA.
  2. When the owner wants to send coins, they sign the transaction
     with their private key.
  3. Anyone on the network can verify the signature using the public key,
     confirming the owner really authorized the transaction.

Why can't someone forge a transaction?
  Without the private key, it is computationally infeasible to create
  a valid signature. This is the mathematical guarantee of ECDSA.
"""

from blockchain.crypto import (
    generate_key_pair,
    serialize_public_key,
    serialize_private_key,
    deserialize_private_key,
)
from blockchain.transaction import Transaction


class Wallet:
    """
    A simple cryptocurrency wallet with key pair management.

    Attributes:
        private_key: ECDSA private key object (NEVER shared).
        public_key: ECDSA public key object.
        address (str): PEM-encoded public key string (acts as wallet address).
    """

    def __init__(self, private_key_pem: str = None):
        """
        Create a new wallet or restore from an existing private key.

        Args:
            private_key_pem: Optional PEM string to restore wallet.
                             If None, a new key pair is generated.
        """
        if private_key_pem:
            # Restore wallet from existing private key
            self.private_key = deserialize_private_key(private_key_pem)
            self.public_key = self.private_key.public_key()
        else:
            # Generate a brand-new key pair
            self.private_key, self.public_key = generate_key_pair()

        # The wallet address is the PEM-encoded public key
        self.address = serialize_public_key(self.public_key)

    def sign_transaction(self, transaction: Transaction) -> None:
        """
        Sign a transaction with this wallet's private key.

        This proves that the wallet owner authorized the transaction.
        Only the owner (who has the private key) can create valid signatures.

        Args:
            transaction: The transaction to sign.

        Raises:
            ValueError: If this wallet is not the sender of the transaction.
        """
        if transaction.sender != self.address:
            raise ValueError(
                "Cannot sign transaction: this wallet is not the sender."
            )
        transaction.sign(self.private_key)

    def get_private_key_pem(self) -> str:
        """
        Get the PEM-encoded private key string.

        WARNING: This should only be used for local display/backup.
        The private key must NEVER be sent over the network.

        Returns:
            PEM-encoded private key string.
        """
        return serialize_private_key(self.private_key)

    def to_dict(self) -> dict:
        """
        Serialize the wallet to a dictionary (for optional persistence).

        Only the private key is stored — the public key and address
        can be derived from it.

        Returns:
            Dictionary with the private key PEM string.
        """
        return {
            "private_key": self.get_private_key_pem(),
            "address": self.address,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Wallet":
        """
        Restore a wallet from a dictionary.

        Args:
            data: Dictionary containing 'private_key' PEM string.

        Returns:
            A Wallet instance with the restored key pair.
        """
        return cls(private_key_pem=data["private_key"])

    def __repr__(self) -> str:
        return f"Wallet(address={self.address[:40]}...)"
