#!/usr/bin/env python3
"""
hype_cli.py

A user-friendly, colorful CLI for managing HYPE staking and vault transfers on Hyperliquid (mainnet only).

Features:
  1) View staking overview (summary + recent rewards)
  2) Unstake (undelegate) HYPE from a validator (manual address entry)
  3) Prepare .env for TypeScript withdraw script (staking → spot)
  4) Vault transfer (deposit into / withdraw from a vault)
  5) Exit

Requirements:
  - Python 3.10+
  - pip install:
      hyperliquid-python-sdk
      eth-account
      rich

Config:
  - A local file config.json must exist with:
      {
        "private_key": "0xYOUR_PRIVATE_KEY_HERE"
      }
"""

import json
import os
from decimal import Decimal
from typing import Tuple, List, Dict, Any, Optional

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.utils.signing import (
    get_timestamp_ms,
    sign_l1_action,
    float_to_usd_int,
)

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.theme import Theme
from rich import box

# ------------------------------
# Rich console setup
# ------------------------------

custom_theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "title": "bold magenta",
        "highlight": "bold cyan",
        "muted": "dim",
    }
)

console = Console(theme=custom_theme)

CONFIG_PATH = "config.json"
ENV_PATH = ".env"

HYPE_DECIMALS = 8
HYPE_WEI_FACTOR = 10 ** HYPE_DECIMALS


# ------------------------------
# Core helpers
# ------------------------------

def load_config(path: str = CONFIG_PATH) -> dict:
    """
    Load local config.json which must contain:
        { "private_key": "0x..." }
    """
    if not os.path.exists(path):
        console.print(
            f"[error]config.json not found at [highlight]{path}[/highlight].[/error]"
        )
        console.print(
            "[info]Please create it with:\n"
            '  { "private_key": "0xYOUR_PRIVATE_KEY_HERE" }[/info]'
        )
        raise SystemExit(1)

    with open(path, "r") as f:
        cfg = json.load(f)

    if "private_key" not in cfg:
        console.print("[error]'private_key' is missing in config.json[/error]")
        raise SystemExit(1)

    return cfg


def build_clients(private_key: str) -> Tuple[Account, Info, Exchange]:
    """
    Create:
      - eth_account.Account wallet
      - Info client (for staking info)
      - Exchange client (for staking/vault actions)
    Mainnet only.
    """
    wallet = Account.from_key(private_key)
    base_url = constants.MAINNET_API_URL

    info = Info(base_url=base_url, skip_ws=True)
    exchange = Exchange(wallet=wallet, base_url=base_url)

    return wallet, info, exchange


def hype_to_wei(amount_hype: str) -> int:
    """
    Convert a human-readable HYPE amount ('1.23') into integer wei
    using 8 decimals (1 HYPE = 100_000_000 wei).
    """
    dec = Decimal(amount_hype)
    wei = int(dec * HYPE_WEI_FACTOR)
    if wei <= 0:
        raise ValueError("Amount must be positive.")
    return wei


# ------------------------------
# Staking info & display helpers
# ------------------------------

def fetch_staking_data(address: str, info: Info) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Fetch staking summary and rewards.

    NOTE:
      The current hyperliquid-python-sdk version does NOT expose per-validator
      delegations (user_stakes) anymore, so we only show:
        - overall summary (delegated, undelegated, pending withdrawals)
        - recent rewards (if available)
    """
    try:
        summary = info.user_staking_summary(address)
    except Exception as e:
        console.print(f"[error]Error fetching staking summary: {e}[/error]")
        summary = None

    try:
        rewards = info.user_staking_rewards(address)
    except Exception:
        rewards = []

    return summary, rewards


def show_staking_overview(wallet: Account, info: Info) -> None:
    """
    Pretty-print staking overview:
      - Basic summary (raw JSON)
      - Recent rewards (if available)
    """
    console.rule("[title]Staking Overview[/title]")

    summary, rewards = fetch_staking_data(wallet.address, info)

    console.print(f"[info]Address:[/info] [highlight]{wallet.address}[/highlight]\n")

    if summary is not None:
        summary_json = json.dumps(summary, indent=2)
        console.print(
            Panel(
                summary_json,
                title="Staking Summary (raw)",
                border_style="info",
            )
        )
    else:
        console.print("[warning]No staking summary available.[/warning]")

    console.print()
    console.print("[title]Recent Staking Rewards (up to 5)[/title]")
    if not rewards:
        console.print("[muted]No rewards data or rewards API not available.[/muted]")
    else:
        table = Table(
            show_header=True,
            header_style="bold magenta",
            box=box.MINIMAL_DOUBLE_HEAD,
        )
        table.add_column("#", style="muted", justify="right")
        table.add_column("Reward Entry (truncated)", style="info")

        for idx, r in enumerate(rewards[:5]):
            raw = json.dumps(r)
            raw_short = raw[:120] + "..." if len(raw) > 120 else raw
            table.add_row(str(idx), raw_short)

        console.print(table)

    console.print()


# ------------------------------
# Actions: Unstake
# ------------------------------

def action_unstake(wallet: Account, exchange: Exchange) -> None:
    """
    Unstake (undelegate) HYPE from a validator.

    Because per-validator delegations are not available via the SDK,
    the user must manually enter the validator address.
    """
    console.rule("[title]Unstake (Undelegate) HYPE[/title]")

    console.print(f"[info]Your address:[/info] [highlight]{wallet.address}[/highlight]\n")

    validator = Prompt.ask("Enter validator address (0x...)").strip()
    if not (validator.startswith("0x") and len(validator) == 42):
        console.print("[error]Invalid validator address format.[/error]")
        return

    amount_str = Prompt.ask(
        "Amount of HYPE to unstake (e.g. 10 or 5.5)",
        default="10"
    ).strip()

    try:
        wei_amount = hype_to_wei(amount_str)
    except Exception as e:
        console.print(f"[error]Invalid amount: {e}[/error]")
        return

    console.print(
        Panel.fit(
            f"You are about to [bold red]UNSTAKE[/bold red] [highlight]{amount_str} HYPE[/highlight]\n"
            f"from validator:\n[highlight]{validator}[/highlight]\n\n"
            f"[muted]This will start the lock / unbonding process. Tokens will not be immediately withdrawable.[/muted]",
            title="Confirm Unstake",
            border_style="warning",
        )
    )

    if not Confirm.ask("Proceed?", default=False):
        console.print("[warning]Unstake cancelled.[/warning]")
        return

    console.print("\n[info]Sending Unstake (token_delegate with is_undelegate=True)...[/info]")
    try:
        result = exchange.token_delegate(
            validator=validator,
            wei=wei_amount,
            is_undelegate=True,
        )
    except Exception as e:
        console.print(f"[error]Error while sending Unstake transaction: {e}[/error]")
        return

    console.print("\n[success]Hyperliquid response:[/success]")
    console.print_json(data=result)
    console.print(
        "\n[muted]If status == 'ok', your tokens are now in the lock/unbonding period.[/muted]"
    )


# ------------------------------
# Action: Prepare .env for withdraw script
# ------------------------------

def action_prepare_withdraw_env(wallet: Account) -> None:
    """
    Prepare or update the .env file used by withdrawFromStaking.ts.

    Writes:
      PRIVATE_KEY=<wallet.key>
      AMOUNT_HYPE_TO_WITHDRAW=<amount>
    """
    console.rule("[title]Prepare .env for Withdraw (staking → spot)[/title]")

    amount_str = Prompt.ask(
        "Amount of HYPE you plan to withdraw once unlocked (e.g. 10.0)",
        default="10.0",
    ).strip()

    try:
        amount_val = float(amount_str)
        if amount_val <= 0:
            raise ValueError
    except Exception:
        console.print("[error]Amount must be a positive number.[/error]")
        return

    lines: List[str] = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r") as f:
            lines = f.readlines()

    new_lines: List[str] = []
    seen_pk = False
    seen_amount = False

    pk_str = f"PRIVATE_KEY={wallet.key.hex()}\n"
    amt_str = f"AMOUNT_HYPE_TO_WITHDRAW={amount_str}\n"

    for line in lines:
        if line.startswith("PRIVATE_KEY="):
            new_lines.append(pk_str)
            seen_pk = True
        elif line.startswith("AMOUNT_HYPE_TO_WITHDRAW="):
            new_lines.append(amt_str)
            seen_amount = True
        else:
            new_lines.append(line)

    if not seen_pk:
        new_lines.append(pk_str)
    if not seen_amount:
        new_lines.append(amt_str)

    with open(ENV_PATH, "w") as f:
        f.writelines(new_lines)

    console.print(
        Panel.fit(
            "[success].env file updated successfully![/success]\n\n"
            "[muted]Sensitive values are written locally only and are NOT part of the repo.[/muted]",
            title=".env prepared",
            border_style="success",
        )
    )

    console.print(
        "\nTo withdraw from staking → spot after lock ends, run:\n\n"
        "  [highlight]node withdrawFromStaking.js[/highlight]\n"
        "\nMake sure Node.js, TypeScript, and dependencies are installed, and .env is correct."
    )


# ------------------------------
# Action: Vault transfer (deposit / withdraw)
# ------------------------------

def action_vault_transfer(wallet: Account, exchange: Exchange) -> None:
    """
    Perform a vaultTransfer:
      - deposit: perp → vault
      - withdraw: vault → perp
    """
    console.rule("[title]Vault Transfer (vault ↔ perp account)[/title]")

    vault_address = Prompt.ask(
        "Vault address (0x...) to transfer to/from",
    ).strip()
    if not (vault_address.startswith("0x") and len(vault_address) == 42):
        console.print("[error]Invalid vault address format.[/error]")
        return

    console.print("\n[highlight]Choose direction:[/highlight]")
    console.print("  [cyan]1[/cyan]. Deposit into vault (perp → vault)")
    console.print("  [cyan]2[/cyan]. Withdraw from vault (vault → perp) [default]\n")

    direction_choice = Prompt.ask("Your choice (1/2)", default="2").strip()
    if direction_choice == "1":
        is_deposit = True
    else:
        is_deposit = False

    direction_label = "DEPOSIT (perp → vault)" if is_deposit else "WITHDRAW (vault → perp)"

    amount_str = Prompt.ask(
        "Amount in USD (e.g. 1.5)",
        default="1.0",
    ).strip()

    try:
        amount_usd = float(amount_str)
        if amount_usd <= 0:
            raise ValueError
    except Exception:
        console.print("[error]Amount must be a positive number.[/error]")
        return

    console.print(
        Panel.fit(
            f"You are about to perform:\n"
            f"[highlight]{direction_label}[/highlight]\n\n"
            f"Vault:  [highlight]{vault_address}[/highlight]\n"
            f"Amount: [highlight]{amount_usd} USD[/highlight]\n\n"
            f"[muted]This uses the 'vaultTransfer' action and moves funds between your perp account and the vault.[/muted]",
            title="Confirm Vault Transfer",
            border_style="warning",
        )
    )

    if not Confirm.ask("Proceed?", default=False):
        console.print("[warning]Vault transfer cancelled.[/warning]")
        return

    usd_int = float_to_usd_int(amount_usd)
    action = {
        "type": "vaultTransfer",
        "vaultAddress": vault_address,
        "isDeposit": is_deposit,
        "usd": usd_int,
    }

    timestamp = get_timestamp_ms()
    signature = sign_l1_action(
        wallet=wallet,
        action=action,
        active_pool=None,
        nonce=timestamp,
        expires_after=None,
        is_mainnet=True,  # mainnet only
    )

    console.print("\n[info]Sending vaultTransfer action to Hyperliquid...[/info]")

    try:
        result = exchange._post_action(action, signature, timestamp)
    except Exception as e:
        console.print(f"[error]Error while sending vault transfer: {e}[/error]")
        return

    console.print("\n[success]Hyperliquid response:[/success]")
    console.print_json(data=result)


# ------------------------------
# Main menu
# ------------------------------

def main_menu() -> None:
    """
    Main interactive menu loop.
    """
    cfg = load_config()
    private_key = cfg["private_key"]

    wallet, info, exchange = build_clients(private_key)

    console.print(
        Panel.fit(
            f"[title]hyperliquid-withdraw-tools[/title]\n\n"
            f"[info]Connected wallet:[/info] [highlight]{wallet.address}[/highlight]\n"
            f"[muted]All actions run on Hyperliquid mainnet.[/muted]",
            border_style="title",
        )
    )

    while True:
        console.print()
        console.rule("[title]Main Menu[/title]")
        console.print("[highlight]Choose an option:[/highlight]\n")
        console.print("  [cyan]1[/cyan]. View staking overview (summary, rewards)")
        console.print("  [cyan]2[/cyan]. Unstake (undelegate) HYPE from a validator")
        console.print("  [cyan]3[/cyan]. Prepare .env for withdrawFromStaking.ts")
        console.print("  [cyan]4[/cyan]. Vault transfer (deposit / withdraw)")
        console.print("  [cyan]5[/cyan]. Exit\n")

        choice = Prompt.ask("Your choice (1-5)", default="1").strip()

        if choice == "1":
            show_staking_overview(wallet, info)
        elif choice == "2":
            action_unstake(wallet, exchange)
        elif choice == "3":
            action_prepare_withdraw_env(wallet)
        elif choice == "4":
            action_vault_transfer(wallet, exchange)
        elif choice == "5":
            console.print("\n[success]Goodbye![/success] 👋")
            break
        else:
            console.print("[error]Invalid choice. Please select 1, 2, 3, 4, or 5.[/error]")


# ------------------------------
# Entry point
# ------------------------------

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[warning]Interrupted by user. Exiting...[/warning]")
