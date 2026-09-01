# gui/app.py
"""
Tkinter GUI for the Educational Blockchain.

A tabbed interface that lets users interact with all blockchain features:
  - Wallet management (create, view keys, check balance)
  - Transaction creation and signing
  - Mining with real-time progress
  - Blockchain explorer with visual chain links
  - Validation and tampering demonstration
  - Network node management
  - Full demo mode

Design choices:
  - Dark theme for a modern look
  - Monospace font for hashes and keys
  - Color-coded status messages (green=valid, red=invalid)
  - Mining runs in a background thread to keep the GUI responsive
"""

import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import time

from blockchain.blockchain import Blockchain
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet


# ---------------------------------------------------------------------------
# Color Palette (Dark Theme)
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#1a1a2e",
    "bg_secondary": "#16213e",
    "bg_card": "#0f3460",
    "accent": "#e94560",
    "accent_green": "#00b894",
    "accent_yellow": "#fdcb6e",
    "text": "#eaeaea",
    "text_dim": "#a0a0b0",
    "text_hash": "#74b9ff",
    "border": "#2d3436",
    "button": "#e94560",
    "button_hover": "#ff6b81",
    "entry_bg": "#2d3436",
}

FONT_NORMAL = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_HEADING = ("Segoe UI", 14, "bold")
FONT_MONO = ("Consolas", 9)
FONT_MONO_SMALL = ("Consolas", 8)


class BlockchainApp:
    """Main GUI Application for the Educational Blockchain."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Educational Blockchain")
        self.root.geometry("1100x750")
        self.root.configure(bg=COLORS["bg"])
        self.root.minsize(900, 600)

        # Blockchain instance
        self.blockchain = Blockchain(difficulty=4, mining_reward=10.0)
        self.data_path = "data/blockchain.json"

        # Try loading existing chain
        self.blockchain.load_chain(self.data_path)

        # Wallets managed by the GUI
        self.wallets: dict[str, Wallet] = {}  # name -> Wallet
        self.wallet_names: dict[str, str] = {}  # address -> name

        # Mining state
        self.is_mining = False

        # Configure styles
        self._setup_styles()

        # Create the tabbed interface
        self.notebook = ttk.Notebook(root, style="Dark.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Create tabs
        self._create_wallet_tab()
        self._create_transaction_tab()
        self._create_mining_tab()
        self._create_explorer_tab()
        self._create_validation_tab()
        self._create_network_tab()
        self._create_demo_tab()

    # ------------------------------------------------------------------
    # Style Configuration
    # ------------------------------------------------------------------

    def _setup_styles(self):
        """Configure ttk styles for the dark theme."""
        style = ttk.Style()
        style.theme_use("clam")

        # Notebook
        style.configure("Dark.TNotebook", background=COLORS["bg"])
        style.configure(
            "Dark.TNotebook.Tab",
            background=COLORS["bg_secondary"],
            foreground=COLORS["text"],
            padding=[12, 6],
            font=FONT_BOLD,
        )
        style.map(
            "Dark.TNotebook.Tab",
            background=[("selected", COLORS["bg_card"])],
            foreground=[("selected", COLORS["accent"])],
        )

        # Frame
        style.configure("Dark.TFrame", background=COLORS["bg"])
        style.configure("Card.TFrame", background=COLORS["bg_card"])

        # Label
        style.configure(
            "Dark.TLabel",
            background=COLORS["bg"],
            foreground=COLORS["text"],
            font=FONT_NORMAL,
        )
        style.configure(
            "Card.TLabel",
            background=COLORS["bg_card"],
            foreground=COLORS["text"],
            font=FONT_NORMAL,
        )
        style.configure(
            "Heading.TLabel",
            background=COLORS["bg"],
            foreground=COLORS["accent"],
            font=FONT_HEADING,
        )

        # Button
        style.configure(
            "Accent.TButton",
            background=COLORS["button"],
            foreground="white",
            font=FONT_BOLD,
            padding=[16, 8],
        )
        style.map(
            "Accent.TButton",
            background=[("active", COLORS["button_hover"])],
        )

        # Entry
        style.configure(
            "Dark.TEntry",
            fieldbackground=COLORS["entry_bg"],
            foreground=COLORS["text"],
            insertcolor=COLORS["text"],
        )

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _make_frame(self, parent) -> tk.Frame:
        """Create a styled frame."""
        f = tk.Frame(parent, bg=COLORS["bg"])
        return f

    def _make_label(self, parent, text, font=None, fg=None, bg=None):
        """Create a styled label."""
        return tk.Label(
            parent,
            text=text,
            font=font or FONT_NORMAL,
            fg=fg or COLORS["text"],
            bg=bg or COLORS["bg"],
        )

    def _make_button(self, parent, text, command, bg=None):
        """Create a styled button."""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=FONT_BOLD,
            fg="white",
            bg=bg or COLORS["button"],
            activebackground=COLORS["button_hover"],
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=16,
            pady=6,
        )
        return btn

    def _make_entry(self, parent, width=40):
        """Create a styled entry field."""
        entry = tk.Entry(
            parent,
            width=width,
            font=FONT_NORMAL,
            bg=COLORS["entry_bg"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        return entry

    def _make_text_area(self, parent, height=10, width=80):
        """Create a styled scrolled text area."""
        text = scrolledtext.ScrolledText(
            parent,
            height=height,
            width=width,
            font=FONT_MONO,
            bg=COLORS["bg_secondary"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            wrap=tk.WORD,
        )
        return text

    def _get_display_name(self, address: str) -> str:
        """Get a human-friendly name for a wallet address."""
        return self.wallet_names.get(address, address[:30] + "...")

    def _log(self, text_widget, message: str, tag: str = None):
        """Append a message to a text widget."""
        text_widget.config(state=tk.NORMAL)
        text_widget.insert(tk.END, message + "\n", tag)
        text_widget.see(tk.END)
        text_widget.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Tab 1: Wallet
    # ------------------------------------------------------------------

    def _create_wallet_tab(self):
        """Create the Wallet management tab."""
        tab = self._make_frame(self.notebook)
        self.notebook.add(tab, text="  💼 Wallet  ")

        # Header
        self._make_label(tab, "Wallet Management", FONT_HEADING, COLORS["accent"]).pack(
            pady=(15, 10)
        )

        # Create wallet section
        create_frame = tk.Frame(tab, bg=COLORS["bg_secondary"], padx=15, pady=10)
        create_frame.pack(fill=tk.X, padx=15, pady=5)

        self._make_label(create_frame, "Wallet Name:", bg=COLORS["bg_secondary"]).grid(
            row=0, column=0, sticky=tk.W, pady=3
        )
        self.wallet_name_entry = self._make_entry(create_frame, width=25)
        self.wallet_name_entry.grid(row=0, column=1, padx=10, pady=3)
        self.wallet_name_entry.insert(0, "Alice")

        self._make_button(create_frame, "Create Wallet", self._create_wallet).grid(
            row=0, column=2, padx=10
        )

        # Wallet info display
        info_frame = tk.Frame(tab, bg=COLORS["bg_secondary"], padx=15, pady=10)
        info_frame.pack(fill=tk.X, padx=15, pady=5)

        self._make_label(info_frame, "Select Wallet:", bg=COLORS["bg_secondary"]).grid(
            row=0, column=0, sticky=tk.W, pady=3
        )
        self.wallet_selector = ttk.Combobox(
            info_frame, values=[], state="readonly", width=25
        )
        self.wallet_selector.grid(row=0, column=1, padx=10, pady=3)
        self.wallet_selector.bind("<<ComboboxSelected>>", self._on_wallet_selected)

        self._make_button(info_frame, "Refresh Balance", self._refresh_balance).grid(
            row=0, column=2, padx=10
        )

        # Key display
        self.wallet_info_text = self._make_text_area(tab, height=14, width=100)
        self.wallet_info_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        self.wallet_info_text.config(state=tk.DISABLED)

        # Tag for colored text
        self.wallet_info_text.tag_configure("key", foreground=COLORS["text_hash"])
        self.wallet_info_text.tag_configure("success", foreground=COLORS["accent_green"])
        self.wallet_info_text.tag_configure("warning", foreground=COLORS["accent_yellow"])

        # Show/hide private key
        self.show_private_key = tk.BooleanVar(value=False)
        tk.Checkbutton(
            tab,
            text="Show Private Key (keep secret!)",
            variable=self.show_private_key,
            command=self._on_wallet_selected,
            bg=COLORS["bg"],
            fg=COLORS["accent"],
            selectcolor=COLORS["bg_secondary"],
            activebackground=COLORS["bg"],
            activeforeground=COLORS["accent"],
            font=FONT_NORMAL,
        ).pack(pady=5)

    def _create_wallet(self):
        """Create a new wallet."""
        name = self.wallet_name_entry.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Please enter a wallet name.")
            return
        if name in self.wallets:
            messagebox.showwarning("Warning", f"Wallet '{name}' already exists.")
            return

        wallet = Wallet()
        self.wallets[name] = wallet
        self.wallet_names[wallet.address] = name

        # Update selector
        self.wallet_selector["values"] = list(self.wallets.keys())
        self.wallet_selector.set(name)

        self._on_wallet_selected()

        self.wallet_info_text.config(state=tk.NORMAL)
        self.wallet_info_text.delete("1.0", tk.END)
        self._log(self.wallet_info_text, f"✓ Wallet '{name}' created successfully!\n", "success")
        self._log(self.wallet_info_text, "Public Key (Address):", "key")
        self._log(self.wallet_info_text, wallet.address)
        balance = self.blockchain.get_balance(wallet.address)
        self._log(self.wallet_info_text, f"\nBalance: {balance} coins", "success")
        self.wallet_info_text.config(state=tk.DISABLED)

        # Update transaction dropdowns
        self._update_tx_dropdowns()

    def _on_wallet_selected(self, event=None):
        """Display selected wallet info."""
        name = self.wallet_selector.get()
        if name not in self.wallets:
            return

        wallet = self.wallets[name]

        self.wallet_info_text.config(state=tk.NORMAL)
        self.wallet_info_text.delete("1.0", tk.END)

        self._log(self.wallet_info_text, f"Wallet: {name}\n", "success")
        self._log(self.wallet_info_text, "Public Key (Address):", "key")
        self._log(self.wallet_info_text, wallet.address)

        if self.show_private_key.get():
            self._log(self.wallet_info_text, "\n⚠ Private Key (KEEP SECRET!):", "warning")
            self._log(self.wallet_info_text, wallet.get_private_key_pem())

        balance = self.blockchain.get_balance(wallet.address)
        self._log(self.wallet_info_text, f"\nBalance: {balance} coins", "success")

        self.wallet_info_text.config(state=tk.DISABLED)

    def _refresh_balance(self):
        """Refresh the balance display for the selected wallet."""
        self._on_wallet_selected()

    # ------------------------------------------------------------------
    # Tab 2: Transactions
    # ------------------------------------------------------------------

    def _create_transaction_tab(self):
        """Create the Transaction tab."""
        tab = self._make_frame(self.notebook)
        self.notebook.add(tab, text="  💸 Transactions  ")

        self._make_label(tab, "Create Transaction", FONT_HEADING, COLORS["accent"]).pack(
            pady=(15, 10)
        )

        form_frame = tk.Frame(tab, bg=COLORS["bg_secondary"], padx=15, pady=15)
        form_frame.pack(fill=tk.X, padx=15, pady=5)

        # Sender
        self._make_label(form_frame, "Sender:", bg=COLORS["bg_secondary"]).grid(
            row=0, column=0, sticky=tk.W, pady=5
        )
        self.tx_sender = ttk.Combobox(form_frame, values=[], state="readonly", width=30)
        self.tx_sender.grid(row=0, column=1, padx=10, pady=5)

        # Receiver
        self._make_label(form_frame, "Receiver:", bg=COLORS["bg_secondary"]).grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        self.tx_receiver = ttk.Combobox(form_frame, values=[], state="readonly", width=30)
        self.tx_receiver.grid(row=1, column=1, padx=10, pady=5)

        # Amount
        self._make_label(form_frame, "Amount:", bg=COLORS["bg_secondary"]).grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        self.tx_amount = self._make_entry(form_frame, width=15)
        self.tx_amount.grid(row=2, column=1, sticky=tk.W, padx=10, pady=5)

        # Send button
        self._make_button(form_frame, "📤 Send Transaction", self._send_transaction).grid(
            row=3, column=0, columnspan=2, pady=15
        )

        # Status display
        self.tx_log = self._make_text_area(tab, height=15, width=100)
        self.tx_log.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        self.tx_log.config(state=tk.DISABLED)
        self.tx_log.tag_configure("success", foreground=COLORS["accent_green"])
        self.tx_log.tag_configure("error", foreground=COLORS["accent"])
        self.tx_log.tag_configure("info", foreground=COLORS["text_hash"])

    def _update_tx_dropdowns(self):
        """Update sender/receiver dropdowns with available wallets."""
        names = list(self.wallets.keys())
        self.tx_sender["values"] = names
        self.tx_receiver["values"] = names

    def _send_transaction(self):
        """Create, sign, and submit a transaction."""
        sender_name = self.tx_sender.get()
        receiver_name = self.tx_receiver.get()

        if not sender_name or not receiver_name:
            self._log(self.tx_log, "✗ Please select both sender and receiver.", "error")
            return

        if sender_name == receiver_name:
            self._log(self.tx_log, "✗ Sender and receiver must be different.", "error")
            return

        try:
            amount = float(self.tx_amount.get())
            if amount <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            self._log(self.tx_log, "✗ Please enter a valid positive amount.", "error")
            return

        sender_wallet = self.wallets[sender_name]
        receiver_wallet = self.wallets[receiver_name]

        # Create the transaction
        tx = Transaction(
            sender=sender_wallet.address,
            receiver=receiver_wallet.address,
            amount=amount,
        )

        # Sign it
        sender_wallet.sign_transaction(tx)
        self._log(self.tx_log, f"✓ Transaction signed by {sender_name}", "success")

        # Verify the signature
        if tx.is_valid():
            self._log(self.tx_log, "✓ Signature verified", "success")
        else:
            self._log(self.tx_log, "✗ Signature verification FAILED", "error")
            return

        # Add to pending pool
        success, message = self.blockchain.add_transaction(tx)
        if success:
            self._log(
                self.tx_log,
                f"✓ {sender_name} → {receiver_name}: {amount} coins", "success",
            )
            self._log(self.tx_log, f"  {message}", "info")
            self._log(
                self.tx_log,
                f"  Pending transactions: {len(self.blockchain.pending_transactions)}\n",
                "info",
            )
        else:
            self._log(self.tx_log, f"✗ {message}", "error")

    # ------------------------------------------------------------------
    # Tab 3: Mining
    # ------------------------------------------------------------------

    def _create_mining_tab(self):
        """Create the Mining tab."""
        tab = self._make_frame(self.notebook)
        self.notebook.add(tab, text="  ⛏ Mining  ")

        self._make_label(tab, "Mine Block", FONT_HEADING, COLORS["accent"]).pack(
            pady=(15, 10)
        )

        # Mining controls
        control_frame = tk.Frame(tab, bg=COLORS["bg_secondary"], padx=15, pady=10)
        control_frame.pack(fill=tk.X, padx=15, pady=5)

        self._make_label(
            control_frame,
            f"Difficulty: {self.blockchain.difficulty} (hash must start with "
            f"{'0' * self.blockchain.difficulty})",
            bg=COLORS["bg_secondary"],
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=3)

        self._make_label(
            control_frame, "Miner Wallet:", bg=COLORS["bg_secondary"]
        ).grid(row=1, column=0, sticky=tk.W, pady=3)
        self.miner_selector = ttk.Combobox(
            control_frame, values=[], state="readonly", width=25
        )
        self.miner_selector.grid(row=1, column=1, padx=10, pady=3)

        self.mine_button = self._make_button(
            control_frame, "⛏ Mine Block", self._mine_block,
            bg=COLORS["accent_green"],
        )
        self.mine_button.grid(row=1, column=2, padx=10)

        # Mining status
        status_frame = tk.Frame(tab, bg=COLORS["bg_secondary"], padx=15, pady=10)
        status_frame.pack(fill=tk.X, padx=15, pady=5)

        self.mining_status_label = self._make_label(
            status_frame, "Ready to mine", bg=COLORS["bg_secondary"],
            fg=COLORS["text_dim"],
        )
        self.mining_status_label.pack(anchor=tk.W)

        self.mining_nonce_label = self._make_label(
            status_frame, "Nonce: —", FONT_MONO, COLORS["text_hash"],
            COLORS["bg_secondary"],
        )
        self.mining_nonce_label.pack(anchor=tk.W, pady=2)

        self.mining_hash_label = self._make_label(
            status_frame, "Hash: —", FONT_MONO, COLORS["text_hash"],
            COLORS["bg_secondary"],
        )
        self.mining_hash_label.pack(anchor=tk.W, pady=2)

        # Mining log
        self.mine_log = self._make_text_area(tab, height=15, width=100)
        self.mine_log.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        self.mine_log.config(state=tk.DISABLED)
        self.mine_log.tag_configure("success", foreground=COLORS["accent_green"])
        self.mine_log.tag_configure("info", foreground=COLORS["text_hash"])
        self.mine_log.tag_configure("error", foreground=COLORS["accent"])

    def _mine_block(self):
        """Start mining in a background thread."""
        miner_name = self.miner_selector.get()
        if not miner_name:
            # Update miner selector with available wallets
            self.miner_selector["values"] = list(self.wallets.keys())
            self._log(self.mine_log, "✗ Please select a miner wallet first.", "error")
            return

        if self.is_mining:
            self._log(self.mine_log, "✗ Already mining...", "error")
            return

        if not self.blockchain.pending_transactions:
            self._log(self.mine_log, "✗ No pending transactions to mine.", "error")
            return

        miner_wallet = self.wallets[miner_name]
        self.is_mining = True
        self.mine_button.config(state=tk.DISABLED)

        self._log(
            self.mine_log,
            f"⛏ Mining started... (difficulty: {self.blockchain.difficulty})",
            "info",
        )
        self._log(
            self.mine_log,
            f"  Pending transactions: {len(self.blockchain.pending_transactions)}",
            "info",
        )

        self.mining_status_label.config(text="⛏ Mining...", fg=COLORS["accent_yellow"])

        def mining_thread():
            start_time = time.time()

            def progress(nonce, hash_value):
                # Schedule GUI update on the main thread
                self.root.after(0, self._update_mining_progress, nonce, hash_value)

            block = self.blockchain.mine_pending_transactions(
                miner_wallet.address, progress_callback=progress
            )

            elapsed = time.time() - start_time

            # Schedule completion update on the main thread
            self.root.after(
                0, self._mining_complete, block, miner_name, elapsed
            )

        thread = threading.Thread(target=mining_thread, daemon=True)
        thread.start()

    def _update_mining_progress(self, nonce, hash_value):
        """Update mining progress labels (called from main thread)."""
        self.mining_nonce_label.config(text=f"Nonce: {nonce:,}")
        self.mining_hash_label.config(text=f"Hash: {hash_value}")

    def _mining_complete(self, block, miner_name, elapsed):
        """Handle mining completion (called from main thread)."""
        self.is_mining = False
        self.mine_button.config(state=tk.NORMAL)

        self.mining_status_label.config(
            text="✓ Block mined successfully!", fg=COLORS["accent_green"]
        )

        self._log(self.mine_log, f"\n✓ Block #{block.index} mined successfully!", "success")
        self._log(self.mine_log, f"  Nonce: {block.nonce:,}", "info")
        self._log(self.mine_log, f"  Hash: {block.hash}", "info")
        self._log(self.mine_log, f"  Time: {elapsed:.2f} seconds", "info")
        self._log(
            self.mine_log,
            f"  Mining reward: {self.blockchain.mining_reward} coins → {miner_name}\n",
            "success",
        )

        # Save chain
        self.blockchain.save_chain(self.data_path)

        # Update miner selector
        self.miner_selector["values"] = list(self.wallets.keys())

    # ------------------------------------------------------------------
    # Tab 4: Blockchain Explorer
    # ------------------------------------------------------------------

    def _create_explorer_tab(self):
        """Create the Blockchain Explorer tab."""
        tab = self._make_frame(self.notebook)
        self.notebook.add(tab, text="  🔗 Explorer  ")

        top_frame = tk.Frame(tab, bg=COLORS["bg"])
        top_frame.pack(fill=tk.X, padx=15, pady=(15, 5))

        self._make_label(top_frame, "Blockchain Explorer", FONT_HEADING, COLORS["accent"]).pack(
            side=tk.LEFT
        )
        self._make_button(top_frame, "🔄 Refresh", self._refresh_explorer).pack(
            side=tk.RIGHT
        )

        # Scrollable canvas for block cards
        canvas_frame = tk.Frame(tab, bg=COLORS["bg"])
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        self.explorer_canvas = tk.Canvas(
            canvas_frame, bg=COLORS["bg"], highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(
            canvas_frame, orient=tk.VERTICAL, command=self.explorer_canvas.yview
        )
        self.explorer_inner = tk.Frame(self.explorer_canvas, bg=COLORS["bg"])

        self.explorer_inner.bind(
            "<Configure>",
            lambda e: self.explorer_canvas.configure(
                scrollregion=self.explorer_canvas.bbox("all")
            ),
        )
        self.explorer_canvas.create_window(
            (0, 0), window=self.explorer_inner, anchor=tk.NW
        )
        self.explorer_canvas.configure(yscrollcommand=scrollbar.set)

        self.explorer_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel scrolling
        self.explorer_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.explorer_canvas.yview_scroll(
                int(-1 * (e.delta / 120)), "units"
            ),
        )

        self._refresh_explorer()

    def _refresh_explorer(self):
        """Refresh the blockchain explorer view."""
        # Clear existing cards
        for widget in self.explorer_inner.winfo_children():
            widget.destroy()

        for i, block in enumerate(self.blockchain.chain):
            # Chain connector (arrow)
            if i > 0:
                arrow_label = tk.Label(
                    self.explorer_inner,
                    text="     ⬇  previous_hash links to above block",
                    font=FONT_MONO_SMALL,
                    fg=COLORS["accent_yellow"],
                    bg=COLORS["bg"],
                )
                arrow_label.pack(pady=2)

            # Block card
            card = tk.Frame(
                self.explorer_inner,
                bg=COLORS["bg_card"],
                padx=15,
                pady=10,
                highlightbackground=COLORS["accent"] if i == 0 else COLORS["border"],
                highlightthickness=2,
            )
            card.pack(fill=tk.X, padx=10, pady=2)

            # Block header
            title = "Genesis Block" if i == 0 else f"Block #{block.index}"
            tk.Label(
                card, text=title, font=FONT_BOLD,
                fg=COLORS["accent"] if i == 0 else COLORS["accent_green"],
                bg=COLORS["bg_card"],
            ).pack(anchor=tk.W)

            # Block details
            details = (
                f"Timestamp:     {block.timestamp}\n"
                f"Hash:          {block.hash}\n"
                f"Previous Hash: {block.previous_hash}\n"
                f"Nonce:         {block.nonce}\n"
                f"Transactions:  {len(block.transactions)}"
            )
            tk.Label(
                card, text=details, font=FONT_MONO_SMALL,
                fg=COLORS["text_hash"], bg=COLORS["bg_card"],
                justify=tk.LEFT,
            ).pack(anchor=tk.W, padx=5, pady=3)

            # Transaction list
            if block.transactions:
                for tx in block.transactions:
                    sender = self._get_display_name(tx["sender"])
                    receiver = self._get_display_name(tx["receiver"])
                    tx_text = f"    {sender} → {receiver}: {tx['amount']} coins"
                    fg = COLORS["accent_yellow"] if tx["sender"] == "SYSTEM" else COLORS["text"]
                    tk.Label(
                        card, text=tx_text, font=FONT_MONO_SMALL,
                        fg=fg, bg=COLORS["bg_card"],
                        justify=tk.LEFT,
                    ).pack(anchor=tk.W)

    # ------------------------------------------------------------------
    # Tab 5: Validation & Tampering
    # ------------------------------------------------------------------

    def _create_validation_tab(self):
        """Create the Validation & Tampering tab."""
        tab = self._make_frame(self.notebook)
        self.notebook.add(tab, text="  🛡 Validation  ")

        self._make_label(tab, "Blockchain Validation & Tampering Demo", FONT_HEADING,
                         COLORS["accent"]).pack(pady=(15, 10))

        btn_frame = tk.Frame(tab, bg=COLORS["bg"])
        btn_frame.pack(pady=10)

        self._make_button(
            btn_frame, "✓ Validate Blockchain", self._validate_chain,
            bg=COLORS["accent_green"],
        ).pack(side=tk.LEFT, padx=10)

        self._make_button(
            btn_frame, "💀 Demonstrate Tampering", self._demonstrate_tampering,
            bg=COLORS["accent"],
        ).pack(side=tk.LEFT, padx=10)

        self._make_button(
            btn_frame, "🔄 Reset Chain", self._reset_chain,
            bg=COLORS["accent_yellow"],
        ).pack(side=tk.LEFT, padx=10)

        # Result display
        self.validation_log = self._make_text_area(tab, height=20, width=100)
        self.validation_log.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        self.validation_log.config(state=tk.DISABLED)
        self.validation_log.tag_configure("valid", foreground=COLORS["accent_green"], font=FONT_BOLD)
        self.validation_log.tag_configure("invalid", foreground=COLORS["accent"], font=FONT_BOLD)
        self.validation_log.tag_configure("info", foreground=COLORS["text_hash"])
        self.validation_log.tag_configure("warning", foreground=COLORS["accent_yellow"])

    def _validate_chain(self):
        """Validate the blockchain and display results."""
        is_valid, message = self.blockchain.is_chain_valid()

        if is_valid:
            self._log(self.validation_log, "✓ Blockchain is VALID", "valid")
        else:
            self._log(self.validation_log, "✗ Blockchain is INVALID", "invalid")

        self._log(self.validation_log, f"  {message}\n", "info")

    def _demonstrate_tampering(self):
        """Demonstrate blockchain tampering."""
        if len(self.blockchain.chain) < 2:
            self._log(
                self.validation_log,
                "✗ Need at least 2 blocks to demonstrate tampering. Mine a block first.\n",
                "invalid",
            )
            return

        self._log(self.validation_log, "=" * 60, "warning")
        self._log(self.validation_log, "TAMPERING DEMONSTRATION", "warning")
        self._log(self.validation_log, "=" * 60, "warning")

        # Show the block before tampering
        block = self.blockchain.chain[1]
        self._log(
            self.validation_log,
            f"\nBefore tampering — Block #{block.index}:", "info",
        )
        for tx in block.transactions:
            sender = self._get_display_name(tx["sender"])
            receiver = self._get_display_name(tx["receiver"])
            self._log(
                self.validation_log,
                f"  {sender} → {receiver}: {tx['amount']} coins", "info",
            )

        # Tamper with the block
        result = self.blockchain.tamper_block(1, 99999.0)
        self._log(self.validation_log, f"\n⚠ {result}", "warning")

        # Show the block after tampering
        self._log(
            self.validation_log,
            f"\nAfter tampering — Block #{block.index}:", "invalid",
        )
        for tx in block.transactions:
            sender = self._get_display_name(tx["sender"])
            receiver = self._get_display_name(tx["receiver"])
            self._log(
                self.validation_log,
                f"  {sender} → {receiver}: {tx['amount']} coins", "invalid",
            )

        # Validate again
        self._log(self.validation_log, "\nRunning validation...", "info")
        is_valid, message = self.blockchain.is_chain_valid()

        if is_valid:
            self._log(self.validation_log, "✓ Blockchain is VALID\n", "valid")
        else:
            self._log(self.validation_log, "✗ Blockchain is INVALID", "invalid")
            self._log(self.validation_log, f"  Reason: {message}\n", "invalid")

        self._log(
            self.validation_log,
            "This demonstrates that modifying any block's data makes\n"
            "the blockchain invalid because the stored hash no longer\n"
            "matches the recalculated hash.\n",
            "info",
        )

    def _reset_chain(self):
        """Reset the blockchain to a fresh state."""
        self.blockchain = Blockchain(difficulty=4, mining_reward=10.0)
        self.blockchain.save_chain(self.data_path)
        self._log(self.validation_log, "🔄 Blockchain reset to Genesis Block.\n", "warning")
        self._refresh_explorer()

    # ------------------------------------------------------------------
    # Tab 6: Network
    # ------------------------------------------------------------------

    def _create_network_tab(self):
        """Create the Network tab."""
        tab = self._make_frame(self.notebook)
        self.notebook.add(tab, text="  🌐 Network  ")

        self._make_label(tab, "Network Node Management", FONT_HEADING, COLORS["accent"]).pack(
            pady=(15, 10)
        )

        info_label = self._make_label(
            tab,
            "To use networking, start nodes from the command line:\n"
            "  python main.py --node 5000\n"
            "  python main.py --node 5001\n\n"
            "Then use the controls below to register peers and sync chains.",
            FONT_MONO,
            COLORS["text_dim"],
        )
        info_label.pack(padx=15, pady=5)

        # Node registration
        reg_frame = tk.Frame(tab, bg=COLORS["bg_secondary"], padx=15, pady=10)
        reg_frame.pack(fill=tk.X, padx=15, pady=5)

        self._make_label(reg_frame, "Node URL:", bg=COLORS["bg_secondary"]).grid(
            row=0, column=0, sticky=tk.W, pady=3
        )
        self.node_url_entry = self._make_entry(reg_frame, width=35)
        self.node_url_entry.grid(row=0, column=1, padx=10, pady=3)
        self.node_url_entry.insert(0, "http://localhost:5001")

        self._make_button(reg_frame, "Register Node", self._register_node).grid(
            row=0, column=2, padx=5
        )
        self._make_button(reg_frame, "Sync Chain", self._sync_chain).grid(
            row=0, column=3, padx=5
        )

        # Network log
        self.network_log = self._make_text_area(tab, height=15, width=100)
        self.network_log.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        self.network_log.config(state=tk.DISABLED)
        self.network_log.tag_configure("success", foreground=COLORS["accent_green"])
        self.network_log.tag_configure("error", foreground=COLORS["accent"])
        self.network_log.tag_configure("info", foreground=COLORS["text_hash"])

    def _register_node(self):
        """Register a peer node (informational — real networking needs Flask nodes)."""
        url = self.node_url_entry.get().strip()
        if not url:
            self._log(self.network_log, "✗ Please enter a node URL.", "error")
            return

        self._log(
            self.network_log,
            f"Note: Peer registration works when running as a Flask node.\n"
            f"Start a node with: python main.py --node <port>\n"
            f"Then POST to http://localhost:<port>/nodes/register\n"
            f"Body: {{\"nodes\": [\"{url}\"]}}\n",
            "info",
        )

    def _sync_chain(self):
        """Sync chain with a peer (informational in GUI mode)."""
        self._log(
            self.network_log,
            "Note: Chain synchronization works between Flask nodes.\n"
            "Use: GET http://localhost:<port>/consensus\n",
            "info",
        )

    # ------------------------------------------------------------------
    # Tab 7: Demo Mode
    # ------------------------------------------------------------------

    def _create_demo_tab(self):
        """Create the Demo Mode tab."""
        tab = self._make_frame(self.notebook)
        self.notebook.add(tab, text="  🎬 Demo  ")

        self._make_label(tab, "Full Blockchain Demo", FONT_HEADING, COLORS["accent"]).pack(
            pady=(15, 10)
        )

        self._make_label(
            tab,
            "This demo walks through the complete blockchain workflow:\n"
            "creating wallets, making transactions, mining, validation, and tampering.",
            fg=COLORS["text_dim"],
        ).pack(padx=15, pady=5)

        self._make_button(tab, "▶ Run Full Demo", self._run_demo,
                          bg=COLORS["accent_green"]).pack(pady=10)

        self.demo_log = self._make_text_area(tab, height=25, width=100)
        self.demo_log.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        self.demo_log.config(state=tk.DISABLED)
        self.demo_log.tag_configure("step", foreground=COLORS["accent_yellow"], font=FONT_BOLD)
        self.demo_log.tag_configure("success", foreground=COLORS["accent_green"])
        self.demo_log.tag_configure("error", foreground=COLORS["accent"])
        self.demo_log.tag_configure("info", foreground=COLORS["text_hash"])
        self.demo_log.tag_configure("heading", foreground=COLORS["accent"], font=FONT_HEADING)

    def _run_demo(self):
        """Run the full demo in a background thread."""
        if self.is_mining:
            self._log(self.demo_log, "✗ Please wait for mining to complete.", "error")
            return

        # Clear log
        self.demo_log.config(state=tk.NORMAL)
        self.demo_log.delete("1.0", tk.END)
        self.demo_log.config(state=tk.DISABLED)

        def demo_thread():
            def log(msg, tag="info"):
                self.root.after(0, self._log, self.demo_log, msg, tag)

            def step(n, desc):
                log(f"\n{'='*60}", "step")
                log(f"Step {n}: {desc}", "step")
                log(f"{'='*60}", "step")
                time.sleep(0.3)

            log("🎬 EDUCATIONAL BLOCKCHAIN — FULL DEMO", "heading")
            log("=" * 60, "info")

            # Reset blockchain for demo
            self.blockchain = Blockchain(difficulty=4, mining_reward=10.0)

            # Step 1: Create wallets
            step(1, "Create wallets for Alice and Bob")
            alice_wallet = Wallet()
            bob_wallet = Wallet()
            self.wallets["Alice"] = alice_wallet
            self.wallets["Bob"] = bob_wallet
            self.wallet_names[alice_wallet.address] = "Alice"
            self.wallet_names[bob_wallet.address] = "Bob"
            log(f"Alice's address: {alice_wallet.address[:60]}...", "info")
            log(f"Bob's address:   {bob_wallet.address[:60]}...", "info")

            # Step 2: Display public keys
            step(2, "Display public keys")
            log("Alice Public Key:", "info")
            log(alice_wallet.address, "info")
            log("\nBob Public Key:", "info")
            log(bob_wallet.address, "info")

            # Step 3: Mine initial block for Alice (so she has coins)
            step(3, "Mine initial block to give Alice coins")
            log(f"Mining reward: {self.blockchain.mining_reward} coins", "info")

            # Create a dummy transaction so we have something to mine
            dummy_tx = Transaction(sender="SYSTEM", receiver=alice_wallet.address, amount=0)
            self.blockchain.pending_transactions.append(dummy_tx)

            block1 = self.blockchain.mine_pending_transactions(alice_wallet.address)
            log(f"✓ Block #{block1.index} mined! Nonce: {block1.nonce}", "success")
            log(f"  Hash: {block1.hash}", "info")

            alice_bal = self.blockchain.get_balance(alice_wallet.address)
            log(f"  Alice balance: {alice_bal} coins", "success")

            # Step 4: Create a transaction
            step(4, "Create transaction: Alice → Bob (5 coins)")
            tx = Transaction(
                sender=alice_wallet.address,
                receiver=bob_wallet.address,
                amount=5.0,
            )
            log(f"Transaction created: Alice → Bob: 5.0 coins", "info")

            # Step 5: Sign the transaction
            step(5, "Digitally sign the transaction")
            alice_wallet.sign_transaction(tx)
            log(f"✓ Transaction signed with Alice's private key", "success")
            log(f"  Signature: {tx.signature[:40]}...", "info")

            # Step 6: Verify the transaction
            step(6, "Verify the transaction signature")
            if tx.is_valid():
                log("✓ Signature verified — transaction is authentic", "success")
            else:
                log("✗ Signature verification FAILED", "error")

            # Step 7: Add to pending transactions
            step(7, "Add transaction to pending pool")
            success, message = self.blockchain.add_transaction(tx)
            log(f"{'✓' if success else '✗'} {message}", "success" if success else "error")

            # Step 8: Mine a block
            step(8, "Mine the block with Proof of Work")
            log(f"Difficulty: {self.blockchain.difficulty}", "info")
            log(f"Target: hash must start with '{'0' * self.blockchain.difficulty}'", "info")
            log("Mining...", "info")

            block2 = self.blockchain.mine_pending_transactions(alice_wallet.address)
            log(f"✓ Block #{block2.index} mined!", "success")
            log(f"  Nonce: {block2.nonce:,}", "info")
            log(f"  Hash: {block2.hash}", "info")

            # Step 9: Display the blockchain
            step(9, "Display the blockchain")
            for block in self.blockchain.chain:
                title = "Genesis Block" if block.index == 0 else f"Block #{block.index}"
                log(f"\n┌─ {title} ─┐", "step")
                log(f"  Hash:     {block.hash}", "info")
                log(f"  PrevHash: {block.previous_hash}", "info")
                log(f"  Nonce:    {block.nonce}", "info")
                for t in block.transactions:
                    s = self._get_display_name(t["sender"])
                    r = self._get_display_name(t["receiver"])
                    log(f"  TX: {s} → {r}: {t['amount']} coins", "info")

            # Step 10: Show balances
            step(10, "Check balances")
            alice_bal = self.blockchain.get_balance(alice_wallet.address)
            bob_bal = self.blockchain.get_balance(bob_wallet.address)
            log(f"Alice: {alice_bal} coins", "success")
            log(f"Bob:   {bob_bal} coins", "success")

            # Step 11: Validate the blockchain
            step(11, "Validate the blockchain")
            is_valid, message = self.blockchain.is_chain_valid()
            if is_valid:
                log("✓ Blockchain is VALID", "success")
            else:
                log(f"✗ Blockchain is INVALID: {message}", "error")

            # Step 12: Demonstrate tampering
            step(12, "Demonstrate tampering")
            log("Tampering with Block #2...", "error")
            log("Changing Alice → Bob from 5.0 to 99999.0 coins", "error")
            tamper_result = self.blockchain.tamper_block(2, 99999.0)
            log(f"⚠ {tamper_result}", "error")

            # Step 13: Validate again
            step(13, "Validate again after tampering")
            is_valid, message = self.blockchain.is_chain_valid()
            if is_valid:
                log("✓ Blockchain is VALID", "success")
            else:
                log("✗ Blockchain is INVALID", "error")
                log(f"  Reason: {message}", "error")

            log(f"\n{'='*60}", "heading")
            log("🎬 DEMO COMPLETE", "heading")
            log(
                "The blockchain successfully detected the tampering!\n"
                "This is the fundamental security guarantee of blockchain technology.",
                "success",
            )

            # Update dropdowns
            self.root.after(0, self._update_tx_dropdowns)
            self.root.after(0, lambda: self.miner_selector.configure(values=list(self.wallets.keys())))

        thread = threading.Thread(target=demo_thread, daemon=True)
        thread.start()


def run_gui():
    """Launch the blockchain GUI application."""
    root = tk.Tk()
    app = BlockchainApp(root)
    root.mainloop()
