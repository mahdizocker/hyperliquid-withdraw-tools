#!/usr/bin/env python3
"""
hype_cli.py
A simple command-line interface (CLI) to manage HYPE staking actions on Hyperliquid.

This tool allows you to:

1) Unstake (Undelegate) HYPE from ANY validator using Python
2) Prepare a .env file for the TypeScript Withdraw script
   (used to move unlocked HYPE from Staking → Spot)

Requirements:
- Python 3.10+
- A config.json file containing:
    {
      "private_key": "0xYOUR_PRIVATE_KEY_HERE"
    }
"""

import json
import os
from decimal import Decimal

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

CONFIG_PATH = "config.json"
ENV_PATH = ".env"

HYPE_DECIMALS = 8
HYPE_WEI_FACTOR = 10 ** HYPE_DECIMALS


# ------------------------------
# CONFIG LOADING
# ------------------------------
def load_config(path: str = CONFIG_PATH) -> dict:
    """
    Loads the local config.json file.

    This file MUST contain your private key:
        { "private_key": "0x..." }

    NOTE: This file is NOT committed to GitHub. Keep it on your machine only.
    """
    if not os.path.exists(path):
        print(f"❌ config.json not found at: {path}")
        print("   Please create it with the following structure:")
        print('   {"private_key": "0xYOUR_PRIVATE_KEY_HERE"}')
        raise SystemExit(1)

    with open(path, "r") as f:
        cfg = json.load(f)

    if "private_key" not in cfg:
        print("❌ 'private_key' missing in config.json")
        raise SystemExit(1)

    return cfg


# ------------------------------
# HYPE Conversion
# ------------------------------
def hype_to_wei(amount_hype: str) -> int:
    """
    Converts a human-readable HYPE amount (e.g. '1.23')
    into integer wei units using 8 decimals.

    Example:
        1 HYPE  = 100,000,000 wei
        1.5 HYPE = 150,000,000 wei
    """
    dec = Decimal(amount_hype)
    wei = int(dec * HYPE_WEI_FACTOR)
    if wei <= 0:
        raise ValueError("Amount must be positive.")
    return wei


# ------------------------------
# ACTION 1: UNSTAKE
# ------------------------------
def action_unstake():
    """
    Guides the user through:
      - Entering validator address
      - Entering HYPE amount
      - Sending the Unstake (tokenDelegate with is_undelegate=True)

    Uses: Exchange.token_delegate() from hyperliquid-python-sdk
    """
    cfg = load_config()
    private_key = cfg["private_key"]
    delegator_wallet = Account.from_key(private_key)

    print("\n=== Unstake (Undelegate) HYPE from a Validator ===")
    print(f"Your wallet address: {delegator_wallet.address}")

    # Ask user for validator address
    validator = input("Enter validator address (0x...): ").strip()
    if not validator.startswith("0x") or len(validator) != 42:
        print("❌ Invalid validator address format.")
        return

    # Ask user for amount of HYPE to unstake
    amount_str = input("Amount of HYPE to unstake (e.g. 10 or 5.5): ").strip()

    try:
        wei_amount = hype_to_wei(amount_str)
    except Exception as e:
        print(f"❌ Error converting HYPE → wei: {e}")
        return

    print(f"\nPreparing to unstake {amount_str} HYPE from validator:")
    print(f"Validator: {validator}")
    print(f"Amount in wei: {wei_amount}")

    # Initialize Hyperliquid Exchange client (Mainnet)
    exchange = Exchange(
        wallet=delegator_wallet,
        base_url=constants.MAINNET_API_URL,
    )

    print("\n⏳ Sending Unstake (Undelegate) transaction...")
    try:
        result = exchange.token_delegate(
            validator=validator,
            wei=wei_amount,
            is_undelegate=True,
        )
    except Exception as e:
        print(f"\n❌ Error while sending Unstake transaction: {e}")
        return

    print("\n✅ Hyperliquid response:")
    print(json.dumps(result, indent=2))
    print("\nℹ️ If status == 'ok', your tokens are now in the lock/unbonding period.")


# ------------------------------
# ACTION 2: PREPARE .ENV FOR WITHDRAW
# ------------------------------
def action_prepare_withdraw_env():
    """
    Makes it easy for users to prepare the .env file required by the
    TypeScript withdraw script (withdrawFromStaking.ts).

    It automatically writes:
        PRIVATE_KEY=<private_key>
        AMOUNT_HYPE_TO_WITHDRAW=<user_input>
    """
    cfg = load_config()
    private_key = cfg["private_key"]

    print("\n=== Prepare .env for Withdraw From Staking → Spot ===")
    print("This will create/update the .env file for the TypeScript script.")

    amount_str = input("Amount of HYPE to withdraw once unlocked (e.g. 10.0): ").strip()

    try:
        amount_val = float(amount_str)
        if amount_val <= 0:
            raise ValueError
    except Exception:
        print("❌ Invalid amount (must be a positive number).")
        return

    # Load existing .env if exists
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r") as f:
            lines = f.readlines()

    new_lines = []
    seen_pk = False
    seen_amount = False

    for line in lines:
        if line.startswith("PRIVATE_KEY="):
            new_lines.append(f"PRIVATE_KEY={private_key}\n")
            seen_pk = True
        elif line.startswith("AMOUNT_HYPE_TO_WITHDRAW="):
            new_lines.append(f"AMOUNT_HYPE_TO_WITHDRAW={amount_str}\n")
            seen_amount = True
        else:
            new_lines.append(line)

    # Add missing fields
    if not seen_pk:
        new_lines.append(f"PRIVATE_KEY={private_key}\n")
    if not seen_amount:
        new_lines.append(f"AMOUNT_HYPE_TO_WITHDRAW={amount_str}\n")

    # Write the updated .env
    with open(ENV_PATH, "w") as f:
        f.writelines(new_lines)

    print("\n✅ .env file successfully prepared:")
    print(f"PRIVATE_KEY=0x... (hidden)")
    print(f"AMOUNT_HYPE_TO_WITHDRAW={amount_str}")

    print("\nTo withdraw once the lock period ends, run:")
    print("  npx ts-node withdrawFromStaking.ts")
    print("(Make sure Node.js, TypeScript, and dependencies are installed.)")


# ------------------------------
# MAIN MENU
# ------------------------------
def main_menu():
    """Simple text-based menu for user interaction."""
    while True:
        print("\n==================== HYPE CLI ====================")
        print("1) Unstake (Undelegate) HYPE from a validator")
        print("2) Prepare .env for Withdraw (staking → spot)")
        print("3) Exit")
        choice = input("Select an option (1/2/3): ").strip()

        if choice == "1":
            action_unstake()
        elif choice == "2":
            action_prepare_withdraw_env()
        elif choice == "3":
            print("Exiting. Good luck! 🌱")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")


# ------------------------------
# ENTRY POINT
# ------------------------------
if __name__ == "__main__":
    main_menu()
