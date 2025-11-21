#!/usr/bin/env python3
"""
Unstake (undelegate) HYPE from any Hyperliquid validator.

Usage examples:

  # Unstake 10 HYPE from Hyper Foundation3
  python unstake_hype.py --validator 0x80f0cd23da5bf3a0101110cfd0f89c8a69a1384d --amount 10

  # Unstake 5.5 HYPE from some other validator
  python unstake_hype.py --validator 0xValidatorAddressHere --amount 5.5
"""

import json
import argparse
from decimal import Decimal

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# HYPE uses 8 decimals for its native "wei"-like unit on Hyperliquid
# (1 HYPE = 100_000_000 units). 
HYPE_DECIMALS = 8
HYPE_WEI_FACTOR = 10 ** HYPE_DECIMALS


def load_config(path: str = "config.json"):
    with open(path, "r") as f:
        cfg = json.load(f)

    if "private_key" not in cfg:
        raise ValueError("config.json must contain 'private_key'.")
    return cfg


def hype_to_wei(amount_hype: str) -> int:
    """
    Convert a (possibly decimal) HYPE amount string into integer wei units.
    Example: "1.23" -> 123000000 (for 8 decimals).
    """
    dec = Decimal(amount_hype)
    wei = int(dec * HYPE_WEI_FACTOR)
    if wei <= 0:
        raise ValueError("Amount must be positive.")
    return wei


def main():
    parser = argparse.ArgumentParser(description="Unstake (undelegate) HYPE from a Hyperliquid validator.")
    parser.add_argument(
        "--validator",
        required=True,
        help="Validator address to unstake from (e.g. 0x80f0cd23da5bf3a0101110cfd0f89c8a69a1384d)",
    )
    parser.add_argument(
        "--amount",
        required=True,
        help="Amount of HYPE to unstake (e.g. 10 or 5.5)."
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config.json (default: config.json)"
    )

    args = parser.parse_args()

    cfg = load_config(args.config)

    private_key = cfg["private_key"]
    delegator_wallet = Account.from_key(private_key)

    print(f"Using delegator address: {delegator_wallet.address}")
    print(f"Target validator: {args.validator}")
    print(f"Unstaking amount (HYPE): {args.amount}")

    # Convert HYPE -> wei (native unit)
    wei_amount = hype_to_wei(args.amount)
    print(f"Unstaking amount in wei units: {wei_amount}")

    # Initialize Exchange client on mainnet
    exchange = Exchange(
        wallet=delegator_wallet,
        base_url=constants.MAINNET_API_URL,  # mainnet endpoint 
    )

    # token_delegate with is_undelegate=True performs an unstake. 
    print("\nSending undelegate (unstake) transaction...")
    try:
        result = exchange.token_delegate(
            validator=args.validator,
            wei=wei_amount,
            is_undelegate=True,
        )
    except Exception as e:
        print(f"\n❌ Error while sending unstake transaction: {e}")
        return

    print("\n✅ Hyperliquid response:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
