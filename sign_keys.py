"""Generate and load the ECDSA signing key used to sign snapshots.

We use secp256k1 (the same curve as Ethereum and Bitcoin) so signatures
can be verified cheaply on-chain if a consumer wants to.

The private key is stored locally and MUST NOT be committed (it's in
.gitignore). The public address is committed and published in the README
so consumers know what to verify against.

Usage:
  python -m oracle.sign_keys generate   # one-time, creates the keypair
  python -m oracle.sign_keys show       # print the public address
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from eth_account import Account

KEY_DIR = Path(__file__).parent / "keys"
PRIV_PATH = KEY_DIR / "signing_key.json"   # NEVER commit (in .gitignore)
PUB_PATH = KEY_DIR / "signing_pubkey.txt"  # safe to commit (public address)


def generate() -> None:
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    if PRIV_PATH.exists():
        print(f"ALREADY EXISTS: {PRIV_PATH}")
        print("Delete it manually if you really want to generate a new key.")
        sys.exit(1)
    acct = Account.create()
    PRIV_PATH.write_text(json.dumps({
        "private_key": acct.key.hex(),
        "address": acct.address,
    }, indent=2), encoding="utf-8")
    PUB_PATH.write_text(acct.address + "\n", encoding="utf-8")
    print(f"Generated signing key.")
    print(f"  PRIVATE (DO NOT COMMIT): {PRIV_PATH}")
    print(f"  PUBLIC address (publish in README): {acct.address}")


def load_signer() -> Account:
    if not PRIV_PATH.exists():
        raise FileNotFoundError(
            "No signing key found. Run: python -m oracle.sign_keys generate")
    data = json.loads(PRIV_PATH.read_text(encoding="utf-8"))
    return Account.from_key(data["private_key"])


def show() -> None:
    if not PUB_PATH.exists():
        print("No public key yet -- run 'generate' first.")
        sys.exit(1)
    print(PUB_PATH.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("generate", "show"):
        print("Usage: python -m oracle.sign_keys {generate|show}")
        sys.exit(1)
    {"generate": generate, "show": show}[sys.argv[1]]()
