# Hyperliquid Withdraw Tools

**Tools for managing HYPE staking and vault transfers on Hyperliquid (Python + TypeScript).**

This repository provides:

- A **Python CLI** (`hype_cli.py`) for:
  - Viewing your **staking overview** (summary, rewards)
  - **Unstaking (undelegating)** HYPE from any validator
  - Preparing `.env` for the **TypeScript withdraw script** (staking → spot)
  - Performing **vault transfers** (deposit into / withdraw from a vault)

- Standalone scripts:
  - `unstake_hype.py` – Unstake HYPE from a specific validator
  - `vault_withdraw.py` – Perform a **vaultTransfer** (deposit or withdraw) using config/env/CLI
  - `withdrawFromStaking.ts` – Withdraw unlocked HYPE from **staking → spot** via TS SDK

This project is designed for users who **cannot use the Hyperliquid UI**, or prefer automation and scripting.

---

## ⚠️ Security Warning

> **NEVER commit or share your real private key.**

This repo uses sample config files:

- `config.example.json`
- `.env.example`

You must create your own **local**:

- `config.json`
- `.env`

These files **must not** be uploaded to GitHub or shared with anyone.

---

## 📁 Project Structure

Typical layout:

```text
hyperliquid-withdraw-tools/
│
├── hype_cli.py                 # Rich CLI: staking overview, unstake, env setup, vault transfer
├── unstake_hype.py             # Simple Python script to unstake from a validator
├── vault_withdraw.py           # Python script for vaultTransfer (deposit / withdraw)
├── withdrawFromStaking.ts      # TS script: withdraw HYPE from staking → spot
│
├── config.example.json         # Example config (no real secrets)
├── .env.example                # Example env file (no real secrets)
│
├── README.md                   # This file
├── GUIDE.fa.md                 # Persian-language detailed guide
│
├── package.json                # Node dependencies and scripts
├── tsconfig.json               # TypeScript configuration
└── ...
````

---

## 🔧 Requirements

### Python

* Python **3.10+**
* Install:

```bash
pip install hyperliquid-python-sdk eth-account rich
```

> Recommended: use a virtual environment (`python -m venv venv`).

---

### Node / TypeScript

* Node.js **16+** (LTS recommended)
* Install in the repo folder:

```bash
npm install @nktkas/hyperliquid viem dotenv
npm install -D ts-node typescript @types/node
```

---

## 🔐 Local Configuration

### 1. `config.json` (used by Python scripts)

Create a file named `config.json` in the project root:

```json
{
  "private_key": "0xYOUR_PRIVATE_KEY_HERE"
}
```

Optional extra fields used by `vault_withdraw.py`:

```json
{
  "private_key": "0xYOUR_PRIVATE_KEY_HERE",
  "vault_address": "0xYOUR_VAULT_ADDRESS_HERE",
  "default_vault_withdraw_usd": 1.5,
  "is_mainnet": true,
  "vault_is_deposit_default": false
}
```

---

### 2. `.env` (used by TypeScript withdraw script)

Create a file named `.env` (not committed) in the project root:

```env
PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE
AMOUNT_HYPE_TO_WITHDRAW=10.0
```

You can also let the CLI (`hype_cli.py`) prepare/update this file for you.

---

## 🌈 Rich CLI – `hype_cli.py`

This is the **main entry point** for non-technical users.

It provides:

* Staking overview (summary, rewards)
* Unstake from a validator (with validator auto-detection)
* Prepare `.env` for TypeScript withdraw
* Vault transfer (deposit / withdraw)

### ▶️ Run the CLI

```bash
python hype_cli.py
# or, on some systems:
python3 hype_cli.py
```

You’ll see a menu like:

```text
==================== HYPE CLI ====================
Connected wallet: 0xYourAddressHere

Main Menu
---------
1. View staking overview (summary, rewards)
2. Unstake (undelegate) HYPE from a validator
3. Prepare .env for withdrawFromStaking.ts
4. Vault transfer (deposit / withdraw)
5. Exit
```

### 1) View staking overview

Shows:

* Your address
* Raw staking summary
* Recent rewards (if available)

### 2) Unstake (Undelegate) HYPE

Flow:

* Lets you pick a validator from an address
* Asks how much HYPE to unstake
* Asks for confirmation and sends a `token_delegate` action with `is_undelegate=True`

> After unstaking, your tokens enter **lock / unbonding** and cannot be withdrawn immediately.

### 3) Prepare `.env` for withdraw script

* Asks how much HYPE you plan to withdraw once unlocked.
* Writes/updates:

```env
PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE
AMOUNT_HYPE_TO_WITHDRAW=10.0
```

This prepares everything for `withdrawFromStaking.ts`.

### 4) Vault transfer (deposit / withdraw)

Uses the `vaultTransfer` action to move funds between:

* **Perp account → Vault** (deposit), or
* **Vault → Perp account** (withdraw)

Flow:

1. Asks for `vaultAddress` (0x…)
2. Asks for direction:

   * `1` = Deposit (perp → vault)
   * `2` = Withdraw (vault → perp) – **default**
3. Asks for amount in USD (e.g. `1.5`)
4. Shows a confirmation panel
5. Builds and signs a `vaultTransfer` action using `sign_l1_action`
6. Sends the action via `exchange._post_action(action, signature, nonce)`

---

## 🐍 Script: `unstake_hype.py`

Simple script for **unstaking HYPE from a specific validator**, without going through the full CLI.

### Usage

```bash
python unstake_hype.py --validator 0xValidatorAddress --amount 10
```

Examples:

```bash
# Unstake 10 HYPE from Hyper Foundation3
python unstake_hype.py \
  --validator 0x80f0cd23da5bf3a0101110cfd0f89c8a69a1384d \
  --amount 10

# Unstake 5.5 HYPE from another validator
python unstake_hype.py \
  --validator 0xValidatorAddressHere \
  --amount 5.5
```

Relies on:

* `config.json` for `private_key`
* Hyperliquid mainnet via `hyperliquid-python-sdk`

---

## 🐍 Script: `vault_withdraw.py`

Generic **vaultTransfer** tool that supports:

* **Deposit into vault** (perp → vault)
* **Withdraw from vault** (vault → perp)

It can read configuration from:

1. **Command-line arguments**
2. **Environment variables**
3. **`config.json`**

### Parameters & precedence

**Private key:**

* `--private-key`
* `PRIVATE_KEY` (env)
* `config.json["private_key"]`

**Vault address:**

* `--vault-address`
* `VAULT_ADDRESS` (env)
* `config.json["vault_address"]`

**Amount in USD:**

* `--amount-usd`
* `WITHDRAW_AMOUNT_USD` (env)
* `config.json["default_vault_withdraw_usd"]`

**Direction:**

* `--deposit` (perp → vault)
* `--withdraw` (vault → perp) – default
* `IS_DEPOSIT` env (`true`/`false`)
* `config.json["vault_is_deposit_default"]`

**Network:**

* `--testnet` (use testnet API)
* `IS_MAINNET` env (`true`/`false`)
* `config.json["is_mainnet"]` (default: `true`)

### Example: simple withdraw (vault → perp)

```bash
# Using CLI args only
python vault_withdraw.py \
  --private-key 0xYOUR_PRIVATE_KEY \
  --vault-address 0xYOUR_VAULT_ADDRESS \
  --amount-usd 5.0 \
  --withdraw
```

### Example: deposit from perp → vault

```bash
python vault_withdraw.py \
  --private-key 0xYOUR_PRIVATE_KEY \
  --vault-address 0xYOUR_VAULT_ADDRESS \
  --amount-usd 2.5 \
  --deposit
```

If you have `config.json` and/or env vars set, you can omit many flags and let the script resolve defaults.

---

## 🟦 Script: `withdrawFromStaking.ts` (TypeScript)

This script calls the Hyperliquid TS SDK’s `cWithdraw` method to move unlocked HYPE from **staking balance** → **spot balance**.

> You must have **already unstaked** and the lock/unbonding period must be over, otherwise this will fail.

### Install dependencies

```bash
npm install @nktkas/hyperliquid viem dotenv
npm install -D ts-node typescript @types/node
```

### Ensure `.env` is set

Typically created by `hype_cli.py`, or manually:

```env
PRIVATE_KEY=0xYOUR_PRIVATE_KEY
AMOUNT_HYPE_TO_WITHDRAW=10.0
```

### Run

```bash
npx ts-node withdrawFromStaking.ts
```

OR
```bash
npx tsc withdrawFromStaking.ts
node withdrawFromStaking.js
```

If successful, you’ll see something like:

```text
Withdrawing 10 HYPE (1000000000 wei) from staking → spot
Using address: 0xYourAddress
cWithdraw result:
{ "status": "ok", ... }
```

> Note that transfers from staking to spot account go through a 7 day unstaking queue.

---

## 🔁 Full Flow Overview (Unstaking + Transfer to Spot)

1. **Unstake HYPE from validator**

   * Via CLI:

     ```bash
     python hype_cli.py
     # choose: "Unstake (undelegate) HYPE from a validator"
     ```
   * Or via standalone script:

     ```bash
     python unstake_hype.py --validator 0x... --amount 10
     ```

2. **Wait for lock/unbonding period**

   * On Hyperliquid, tokens don’t become withdrawable instantly.

3. **Prepare withdraw config**

   * Via CLI:

     ```bash
     python hype_cli.py
     # choose: "Prepare .env for withdrawFromStaking.ts"
     ```
   * Or manually edit `.env`.

4. **Withdraw staking → spot**

   ```bash
   npx ts-node withdrawFromStaking.ts
   ```

   OR
   ```bash
   npx tsc withdrawFromStaking.ts
   node withdrawFromStaking.js
   ```

### ❗️ Never share private keys.
