# main.py
"""
Entry Point for the Educational Blockchain.

Usage:
    python main.py              Launch the GUI
    python main.py --demo       Run the demo in the terminal
    python main.py --node PORT  Start a Flask network node on the given port

Examples:
    python main.py
    python main.py --demo
    python main.py --node 5000
    python main.py --node 5001
"""

import argparse
import io
import sys
import time

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )

from blockchain.blockchain import Blockchain
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet


def run_demo():
    """
    Run the full blockchain demo in the terminal.

    This demonstrates every core concept:
      1. Wallet creation (key generation)
      2. Transaction creation and signing
      3. Signature verification
      4. Mining with Proof of Work
      5. Blockchain display
      6. Balance calculation
      7. Chain validation
      8. Tampering detection
    """
    print("=" * 70)
    print("  EDUCATIONAL BLOCKCHAIN -- COMPLETE DEMO")
    print("=" * 70)

    # ---- Step 1: Create wallets ----
    print("\n[Step 1] Creating wallets for Alice and Bob...")
    alice = Wallet()
    bob = Wallet()
    print(f"  Alice address: {alice.address[:60]}...")
    print(f"  Bob address:   {bob.address[:60]}...")

    # ---- Step 2: Create blockchain ----
    print("\n[Step 2] Initializing blockchain (difficulty=4)...")
    bc = Blockchain(difficulty=4, mining_reward=10.0)
    print(f"  Genesis Block created: {bc.chain[0].hash[:32]}...")
    print(f"  Chain length: {len(bc.chain)}")

    # ---- Step 3: Mine first block for Alice (gives her coins) ----
    print("\n[Step 3] Mining first block to give Alice coins...")
    # Add a dummy pending transaction so mining proceeds
    dummy = Transaction(sender="SYSTEM", receiver=alice.address, amount=0)
    bc.pending_transactions.append(dummy)

    start = time.time()
    block1 = bc.mine_pending_transactions(alice.address)
    elapsed1 = time.time() - start
    print(f"  [OK] Block #{block1.index} mined in {elapsed1:.2f}s")
    print(f"    Nonce: {block1.nonce:,}")
    print(f"    Hash:  {block1.hash}")
    print(f"  Alice balance: {bc.get_balance(alice.address)} coins")

    # ---- Step 4: Create a transaction ----
    print("\n[Step 4] Creating transaction: Alice -> Bob (5 coins)...")
    tx = Transaction(
        sender=alice.address,
        receiver=bob.address,
        amount=5.0,
    )
    print("  Transaction created.")

    # ---- Step 5: Sign the transaction ----
    print("\n[Step 5] Signing transaction with Alice's private key...")
    alice.sign_transaction(tx)
    print(f"  [OK] Signed. Signature: {tx.signature[:40]}...")

    # ---- Step 6: Verify the signature ----
    print("\n[Step 6] Verifying transaction signature...")
    if tx.is_valid():
        print("  [OK] Signature is VALID -- transaction is authentic.")
    else:
        print("  [FAIL] Signature is INVALID!")
        return

    # ---- Step 7: Add to pending ----
    print("\n[Step 7] Adding transaction to pending pool...")
    success, msg = bc.add_transaction(tx)
    print(f"  {'[OK]' if success else '[FAIL]'} {msg}")

    # ---- Step 8: Mine the block ----
    print("\n[Step 8] Mining block with Proof of Work...")
    print(f"  Difficulty: {bc.difficulty}")
    print(f"  Target: hash must start with '{'0' * bc.difficulty}'")
    start = time.time()
    block2 = bc.mine_pending_transactions(alice.address)
    elapsed2 = time.time() - start
    print(f"  [OK] Block #{block2.index} mined in {elapsed2:.2f}s")
    print(f"    Nonce: {block2.nonce:,}")
    print(f"    Hash:  {block2.hash}")

    # ---- Step 9: Display the blockchain ----
    print("\n[Step 9] Current blockchain:")
    print("-" * 70)
    for block in bc.chain:
        title = "GENESIS BLOCK" if block.index == 0 else f"BLOCK #{block.index}"
        print(f"\n  +--- {title} ---+")
        print(f"  | Timestamp:  {block.timestamp}")
        print(f"  | Hash:       {block.hash}")
        print(f"  | Prev Hash:  {block.previous_hash}")
        print(f"  | Nonce:      {block.nonce}")
        print(f"  | Txns:       {len(block.transactions)}")
        for t in block.transactions:
            s = "SYSTEM" if t["sender"] == "SYSTEM" else "Alice" if t["sender"] == alice.address else "Bob"
            r = "Alice" if t["receiver"] == alice.address else "Bob"
            print(f"  |   {s} -> {r}: {t['amount']} coins")
        print(f"  +---------------------+")

    # ---- Step 10: Balances ----
    print("\n[Step 10] Balances:")
    print(f"  Alice: {bc.get_balance(alice.address)} coins")
    print(f"  Bob:   {bc.get_balance(bob.address)} coins")

    # ---- Step 11: Validate ----
    print("\n[Step 11] Validating blockchain...")
    is_valid, message = bc.is_chain_valid()
    print(f"  {'[OK]' if is_valid else '[FAIL]'} {message}")

    # ---- Step 12: Tamper ----
    print("\n[Step 12] TAMPERING DEMONSTRATION")
    print("  Modifying Block #2: changing amount to 99999 coins...")
    result = bc.tamper_block(2, 99999.0)
    print(f"  [WARNING] {result}")

    # ---- Step 13: Validate again ----
    print("\n[Step 13] Validating blockchain after tampering...")
    is_valid, message = bc.is_chain_valid()
    print(f"  {'[OK]' if is_valid else '[FAIL]'} {message}")

    # ---- Save ----
    print("\n[Persistence] Saving blockchain to data/blockchain.json...")
    bc.save_chain("data/blockchain.json")
    print("  [OK] Saved.")

    print("\n" + "=" * 70)
    print("  DEMO COMPLETE")
    print("  The blockchain detected the tampering!")
    print("=" * 70)


def run_node(port: int):
    """Start a Flask network node on the given port."""
    from blockchain.node import create_node_app

    print(f"Starting blockchain node on port {port}...")
    app, state = create_node_app(port=port)
    print(f"  Miner address: {state.wallet.address[:60]}...")
    print(f"  Chain length:  {len(state.blockchain.chain)}")
    print(f"  Difficulty:    {state.blockchain.difficulty}")
    print(f"\nEndpoints:")
    print(f"  GET  http://localhost:{port}/chain")
    print(f"  POST http://localhost:{port}/transactions/new")
    print(f"  POST http://localhost:{port}/mine")
    print(f"  POST http://localhost:{port}/nodes/register")
    print(f"  GET  http://localhost:{port}/nodes")
    print(f"  GET  http://localhost:{port}/chain/valid")
    print(f"  GET  http://localhost:{port}/consensus")
    print(f"  GET  http://localhost:{port}/info")
    print()
    app.run(host="0.0.0.0", port=port, debug=False)


def main():
    parser = argparse.ArgumentParser(
        description="Educational Blockchain",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py              Launch GUI\n"
            "  python main.py --demo       Run terminal demo\n"
            "  python main.py --node 5000  Start Flask node on port 5000\n"
        ),
    )
    parser.add_argument(
        "--demo", action="store_true", help="Run the demo in the terminal"
    )
    parser.add_argument(
        "--node", type=int, metavar="PORT", help="Start a Flask node on this port"
    )

    args = parser.parse_args()

    if args.demo:
        run_demo()
    elif args.node:
        run_node(args.node)
    else:
        # Launch GUI
        from gui.app import run_gui
        run_gui()


if __name__ == "__main__":
    main()
