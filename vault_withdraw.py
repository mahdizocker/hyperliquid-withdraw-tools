#!/usr/bin/env python3
"""
vault_withdraw.py

Perform a vaultTransfer on Hyperliquid:

- Withdraw from a vault → back to your perp account
- Or deposit from your perp account → into a vault

Configuration sources (precedence: CLI > ENV > config > defaults):

1) Command-line flags:
   --private-key       0x... private key
   --vault-address     0x... vault address
   --amount-usd        float amount in normal USD units (e.g. 1.5)
   --deposit           deposit into vault (perp → vault)
   --withdraw          withdraw from vault (vault → perp) [default]
   --testnet           use testnet instead of mainnet
   --config            path to config.json (default: config.json)

2) Environment variables:
   PRIVATE_KEY
   VAULT_ADDRESS
   WITHDRAW_AMOUNT_USD
   IS_DEPOSIT         ("true"/"false")
   IS_MAINNET         ("true"/"false")

3) config.json keys (optional):
   {
     "private_key": "0x...",
     "vault_address": "0x...",
     "default_vault_withdraw_usd": 1.5,
     "is_mainnet": true,
     "vault_is_deposit_default": false
   }

If nothing is provided for a required field (private_key, vault_address, amount),
the script will exit with an error.
"""

import os
import json
import argparse
from typing import Any, Optional

from eth_account import Account
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.utils.constants import MAINNET_API_URL
from hyperliquid.utils.signing import (
    get_timestamp_ms,
    sign_l1_action,
    float_to_usd_int,
)


TESTNET_API_URL = "https://api.hyperliquid-testnet.xyz"  # used if --testnet or IS_MAINNET=false


# -----------------------------
# Config helpers
# -----------------------------
def load_local_config(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        try:
            return json.load(f)
        except Exception:
            return {}


def str_to_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    v = value.strip().lower()
    if v in ("1", "true", "yes", "y"):
        return True
    if v in ("0", "false", "no", "n"):
        return False
    return default


def first_non_none(*values: Any) -> Any:
    for v in values:
        if v is not None:
            return v
    return None


# -----------------------------
# Core action builder
# -----------------------------
def build_vault_transfer_action(
    vault_address: str,
    is_deposit: bool,
    usd_amount: float,
) -> dict:
    """
    Build the vaultTransfer action.
    Uses perpetual USD integer format with 6 decimals, e.g. 1.0 -> 1_000_000.
    """
    usd_int = float_to_usd_int(usd_amount)

    action = {
        "type": "vaultTransfer",
        "vaultAddress": vault_address,
        "isDeposit": is_deposit,
        "usd": usd_int,
    }
    return action


# -----------------------------
# Main
# -----------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Perform a vaultTransfer (deposit or withdraw) on Hyperliquid."
    )
    parser.add_argument(
        "--private-key",
        help="EOA private key (0x...). Overrides PRIVATE_KEY env and config.json.",
    )
    parser.add_argument(
        "--vault-address",
        help="Vault address to transfer to/from (0x...). Overrides VAULT_ADDRESS env and config.json.",
    )
    parser.add_argument(
        "--amount-usd",
        type=float,
        help="Amount in normal USD units (e.g. 1.5). Overrides WITHDRAW_AMOUNT_USD env and config default.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--deposit",
        action="store_true",
        help="Deposit from perp account into the vault (perp → vault).",
    )
    group.add_argument(
        "--withdraw",
        action="store_true",
        help="Withdraw from vault back to perp account (vault → perp). [default]",
    )
    parser.add_argument(
        "--testnet",
        action="store_true",
        help="Use Hyperliquid testnet instead of mainnet.",
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to local JSON config file (default: config.json).",
    )

    args = parser.parse_args()

    # Load optional local config.json
    cfg = load_local_config(args.config)

    # Resolve private key
    private_key = first_non_none(
        args.private_key,
        os.getenv("PRIVATE_KEY"),
        cfg.get("private_key"),
    )

    if not private_key:
        raise RuntimeError(
            "Missing private key. Provide via --private-key, PRIVATE_KEY env, or config.json['private_key']."
        )

    # Resolve vault address
    vault_address = first_non_none(
        args.vault_address,
        os.getenv("VAULT_ADDRESS"),
        cfg.get("vault_address"),
    )

    if not vault_address:
        raise RuntimeError(
            "Missing vault address. Provide via --vault-address, VAULT_ADDRESS env, or config.json['vault_address']."
        )

    if not (vault_address.startswith("0x") and len(vault_address) == 42):
        raise RuntimeError("VAULT_ADDRESS must be a 42-char 0x… address.")

    # Resolve amount in USD
    amount_from_env = os.getenv("WITHDRAW_AMOUNT_USD")
    amount_from_env_float = float(amount_from_env) if amount_from_env is not None else None

    amount_usd = first_non_none(
        args.amount_usd,
        amount_from_env_float,
        cfg.get("default_vault_withdraw_usd"),
    )

    if amount_usd is None:
        raise RuntimeError(
            "Missing amount. Provide via --amount-usd, WITHDRAW_AMOUNT_USD env, "
            "or config.json['default_vault_withdraw_usd']."
        )

    if amount_usd <= 0:
        raise RuntimeError("Amount in USD must be positive.")

    # Resolve is_mainnet
    if args.testnet:
        is_mainnet = False
    else:
        is_mainnet = str_to_bool(
            os.getenv("IS_MAINNET"),
            default=cfg.get("is_mainnet", True),
        )

    base_url = MAINNET_API_URL if is_mainnet else TESTNET_API_URL

    # Resolve is_deposit (default: withdraw)
    if args.deposit:
        is_deposit = True
    elif args.withdraw:
        is_deposit = False
    else:
        # env or config default
        env_is_deposit = os.getenv("IS_DEPOSIT")
        is_deposit = str_to_bool(
            env_is_deposit,
            default=cfg.get("vault_is_deposit_default", False),
        )

    # Summary
    direction = "DEPOSIT (perp → vault)" if is_deposit else "WITHDRAW (vault → perp)"
    print("=== Vault Transfer Configuration ===")
    print(f"  Network:    {'Mainnet' if is_mainnet else 'Testnet'}")
    print(f"  Direction:  {direction}")
    print(f"  Vault:      {vault_address}")
    print(f"  Amount:     {amount_usd} USD\n")

    # Create local wallet object
    wallet: LocalAccount = Account.from_key(private_key)
    print(f"Using wallet address: {wallet.address}")

    # Create Exchange client
    exchange = Exchange(
        wallet=wallet,
        base_url=base_url,
    )

    # Current timestamp in ms → used as nonce
    timestamp = get_timestamp_ms()

    # Build vaultTransfer action
    action = build_vault_transfer_action(
        vault_address=vault_address,
        is_deposit=is_deposit,
        usd_amount=amount_usd,
    )

    # Sign as an L1 action using phantom agent (EOA signer)
    signature = sign_l1_action(
        wallet=wallet,
        action=action,
        active_pool=None,
        nonce=timestamp,
        expires_after=None,
        is_mainnet=is_mainnet,
    )

    print("\nSignature produced:")
    print(f"  r: {signature['r']}")
    print(f"  s: {signature['s']}")
    print(f"  v: {signature['v']}")

    # Send it to /exchange
    result = exchange._post_action(action, signature, timestamp)

    print("\nExchange response:")
    print(result)


if __name__ == "__main__":
    main()
