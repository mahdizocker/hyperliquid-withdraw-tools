# **hyperliquid-withdraw-tools**

### *Tools for Unstaking & Withdrawing HYPE on Hyperliquid (Python + TypeScript)*

---

## 📌 Overview

**hyperliquid-withdraw-tools** is a simple, command-line based toolkit that allows you to:

* **Unstake (Undelegate) HYPE** from *any* Hyperliquid validator (Python)
* **Withdraw HYPE from Staking → Spot** after the lock/unbonding period (TypeScript)
* Use a **beginner-friendly CLI** to guide you through both processes interactively

This project is designed for users who **cannot use the Hyperliquid UI**, or prefer automation and scripting.

---

## ⚠️ Security Warning

**Never share or upload your real private key (private_key, .env, config.json).**
This repository includes:

* `config.example.json`
* `.env.example`
* `.gitignore`

You must create your own **local** `config.json` and `.env` files on your system.
They must **never** be committed to GitHub.

---

## 📁 Project Structure

```
hyperliquid-withdraw-tools/
│
├── unstake_hype.py               # Python script to unstake from any validator
├── withdrawFromStaking.ts        # TypeScript script to withdraw staking → spot
├── hype_cli.py                   # Interactive CLI tool (Python)
│
├── config.example.json           # Template config (safe)
├── .env.example                  # Template .env (safe)
│
├── README.md                     # This file
├── GUIDE.fa.md                   # Persian-language full guide
│
├── package.json / tsconfig.json  # Node configuration files
└── ...
```

---

# 🐍 Python — Unstake HYPE (Undelegate)

The script `unstake_hype.py` lets you unstake HYPE from **any validator** with a single command.

### ✅ Installation

```bash
pip install hyperliquid-python-sdk eth-account
```

### 🔧 Local configuration

Create a file `config.json`:

```json
{
  "private_key": "0xYOUR_PRIVATE_KEY_HERE"
}
```

---

## ▶️ Usage Examples

### 1) Unstake 10 HYPE from **Hyper Foundation3**

```bash
python unstake_hype.py \
  --validator 0x80f0cd23da5bf3a0101110cfd0f89c8a69a1384d \
  --amount 10
```

### 2) Unstake 5.5 HYPE from any validator

```bash
python unstake_hype.py --validator 0xValidatorAddress --amount 5.5
```

---

## 📝 What happens after unstaking?

* Your tokens move into the **lock / unbonding period**.
* You **cannot withdraw yet**, even if unstake was successful.
* After the lock period ends, you can perform the **withdraw step** using the TypeScript script.

---

# 🟦 TypeScript — Withdraw Staking → Spot

The script `withdrawFromStaking.ts` uses the official Hyperliquid TS SDK to send the `cWithdraw` action.

> ⚠️ You can only withdraw **after** lock/unbonding completes.

---

## ✅ Installation

```bash
npm install @nktkas/hyperliquid viem dotenv
npm install -D ts-node typescript @types/node
```

### 🔧 Create `.env` locally:

```
PRIVATE_KEY=0xYOUR_PRIVATE_KEY
AMOUNT_HYPE_TO_WITHDRAW=10.0
```

---

## ▶️ Usage

```bash
npx ts-node withdrawFromStaking.ts
```

### Example output:

```
Withdrawing 10 HYPE (1000000000 wei) from staking → spot
Using address: 0xYourAddress
cWithdraw result:
{ "status": "ok", ... }
```

After this, your **Spot HYPE balance** will increase.

---

# 🖥️ Python CLI — Interactive Tool

The file `hype_cli.py` provides a step-by-step interactive CLI for beginners.

It offers two main operations:

### 1. **Unstake HYPE**

Guides you through entering:

* Validator address
* Amount of HYPE

### 2. **Prepare `.env` for Withdraw**

Automatically writes a correct `.env` file for the TS withdraw script.

---

## ▶️ Run CLI

```bash
python hype_cli.py
```

You’ll see a menu:

```
==================== HYPE CLI ====================
1) Unstake (Undelegate) HYPE from a validator
2) Prepare .env for Withdraw from Staking → Spot
3) Exit
```

---

# 🧠 Full Withdrawal Flow

Here is the required 2-step Hyperliquid process:

### **Step 1 — Unstake (Undelegate) using Python**

```bash
python unstake_hype.py --validator <address> --amount <HYPE>
```

### **Wait for Lock / Unbonding Period**

Nothing can bypass this — it’s enforced by Hyperliquid.

### **Step 2 — Withdraw from Staking → Spot (TypeScript)**

```bash
npx ts-node withdrawFromStaking.ts
```

---

# 🛠️ Requirements

### Python tools require:

* Python 3.10+
* pip packages:

  * `hyperliquid-python-sdk`
  * `eth-account`

### TypeScript tools require:

* Node.js 16+
* npm packages:

  * `@nktkas/hyperliquid`
  * `viem`
  * `dotenv`
  * `typescript`
  * `ts-node`

---

### ❗️ Never share private keys.
