# blockchain/node.py
"""
Network Node for the Educational Blockchain.

A Node is a server that participates in the blockchain network.
Each node maintains:
  - Its own copy of the blockchain
  - A list of pending transactions
  - A set of known peer nodes
  - A wallet (miner identity)

Nodes communicate via HTTP (Flask) and implement a simple
consensus mechanism: the longest valid chain wins.

How does consensus work?
  When nodes disagree about which chain is correct, the network
  adopts the longest chain that passes validation. This works because
  the longest chain represents the most computational work (mining),
  making it the most trustworthy.

Endpoints:
  GET  /chain              — Returns the full blockchain
  POST /transactions/new   — Submits a new transaction
  POST /mine               — Mines pending transactions
  POST /nodes/register     — Registers peer nodes
  GET  /nodes              — Lists known peers
  GET  /chain/valid        — Validates the chain
  GET  /balance/<address>  — Returns balance for an address
"""

import requests as http_requests
from flask import Flask, jsonify, request

from blockchain.blockchain import Blockchain
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet


def create_node_app(
    host: str = "0.0.0.0",
    port: int = 5000,
    difficulty: int = 4,
) -> tuple[Flask, "NodeState"]:
    """
    Create a Flask application for a blockchain node.

    Args:
        host: Host address to bind to.
        port: Port number.
        difficulty: Mining difficulty for this node's blockchain.

    Returns:
        Tuple of (Flask app, NodeState).
    """
    app = Flask(__name__)

    # Node state — shared across all request handlers
    state = NodeState(difficulty=difficulty, port=port)

    # -----------------------------------------------------------------
    # Endpoints
    # -----------------------------------------------------------------

    @app.route("/chain", methods=["GET"])
    def get_chain():
        """Return the full blockchain as JSON."""
        return jsonify(state.blockchain.to_dict()), 200

    @app.route("/transactions/new", methods=["POST"])
    def new_transaction():
        """
        Accept a new signed transaction.

        Expected JSON body:
            { sender, receiver, amount, timestamp, signature }
        """
        data = request.get_json()
        required = ["sender", "receiver", "amount", "timestamp", "signature"]

        if not data or not all(k in data for k in required):
            return jsonify({"error": f"Missing fields. Required: {required}"}), 400

        tx = Transaction.from_dict(data)
        success, message = state.blockchain.add_transaction(tx)

        if success:
            return jsonify({"message": message}), 201
        else:
            return jsonify({"error": message}), 400

    @app.route("/mine", methods=["POST"])
    def mine_block():
        """Mine pending transactions into a new block."""
        data = request.get_json() or {}
        miner_address = data.get("miner_address", state.wallet.address)

        block = state.blockchain.mine_pending_transactions(miner_address)

        # Save after mining
        state.blockchain.save_chain(state.data_path)

        # Announce new block to peers (best-effort)
        state.broadcast_chain()

        return jsonify({
            "message": "Block mined successfully!",
            "block": block.to_dict(),
        }), 201

    @app.route("/nodes/register", methods=["POST"])
    def register_nodes():
        """
        Register one or more peer nodes.

        Expected JSON body:
            { "nodes": ["http://localhost:5001", ...] }
        """
        data = request.get_json()
        nodes = data.get("nodes", []) if data else []

        if not nodes:
            return jsonify({"error": "No nodes provided."}), 400

        for node_url in nodes:
            state.peers.add(node_url.rstrip("/"))

        return jsonify({
            "message": "Nodes registered.",
            "peers": list(state.peers),
        }), 201

    @app.route("/nodes", methods=["GET"])
    def get_nodes():
        """List all registered peer nodes."""
        return jsonify({"peers": list(state.peers)}), 200

    @app.route("/chain/valid", methods=["GET"])
    def validate_chain():
        """Validate the blockchain and return the result."""
        is_valid, message = state.blockchain.is_chain_valid()
        return jsonify({
            "valid": is_valid,
            "message": message,
        }), 200

    @app.route("/balance", methods=["POST"])
    def get_balance():
        """Return the balance for a wallet address."""
        data = request.get_json()
        if not data or "address" not in data:
            return jsonify({"error": "Missing 'address' field."}), 400
        address = data["address"]
        balance = state.blockchain.get_balance(address)
        return jsonify({"address": address[:60] + "...", "balance": balance}), 200

    @app.route("/consensus", methods=["GET"])
    def consensus():
        """
        Run the consensus algorithm.

        Queries all peer nodes and adopts the longest valid chain.
        """
        replaced = state.resolve_conflicts()
        if replaced:
            return jsonify({
                "message": "Chain was replaced by a longer valid chain.",
                "chain": state.blockchain.to_dict(),
            }), 200
        else:
            return jsonify({
                "message": "Our chain is authoritative. No replacement needed.",
                "chain": state.blockchain.to_dict(),
            }), 200

    @app.route("/info", methods=["GET"])
    def node_info():
        """Return node information."""
        return jsonify({
            "port": state.port,
            "chain_length": len(state.blockchain.chain),
            "peers": list(state.peers),
            "pending_transactions": len(state.blockchain.pending_transactions),
            "difficulty": state.blockchain.difficulty,
            "miner_address": state.wallet.address[:60] + "...",
        }), 200

    return app, state


class NodeState:
    """
    Holds the state for a blockchain node.

    Attributes:
        blockchain (Blockchain): This node's blockchain instance.
        peers (set): URLs of known peer nodes.
        wallet (Wallet): This node's miner wallet.
        port (int): Port this node runs on.
        data_path (str): Path to the blockchain JSON file.
    """

    def __init__(self, difficulty: int = 4, port: int = 5000):
        self.blockchain = Blockchain(difficulty=difficulty)
        self.peers: set[str] = set()
        self.wallet = Wallet()
        self.port = port
        self.data_path = f"data/blockchain_node_{port}.json"

        # Try to load existing chain
        self.blockchain.load_chain(self.data_path)

    def resolve_conflicts(self) -> bool:
        """
        Consensus algorithm: adopt the longest valid chain from peers.

        Queries every registered peer for their chain. If any peer has
        a longer chain that passes validation, we replace our chain.

        Returns:
            True if our chain was replaced, False otherwise.
        """
        replaced = False

        for peer in self.peers:
            try:
                response = http_requests.get(f"{peer}/chain", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    peer_chain = data.get("chain", [])
                    if self.blockchain.replace_chain(peer_chain):
                        replaced = True
            except http_requests.exceptions.RequestException:
                # Peer is unreachable — skip it
                continue

        if replaced:
            self.blockchain.save_chain(self.data_path)

        return replaced

    def broadcast_chain(self) -> None:
        """
        Notify peers that we have a new chain (best-effort).

        Peers can then decide whether to adopt it via consensus.
        """
        for peer in self.peers:
            try:
                http_requests.get(f"{peer}/consensus", timeout=5)
            except http_requests.exceptions.RequestException:
                continue
