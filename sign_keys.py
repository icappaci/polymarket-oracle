"""Генерация и загрузка ECDSA-ключа для подписи snapshot'ов Oracle.

Один раз генерируем secp256k1-ключ (стандарт Ethereum/Bitcoin, дешёвая
проверка в смарт-контрактах). Приватный ключ хранится локально (НЕ
коммитить!), публичный публикуется в README.

Использование:
  python -m oracle.sign_keys generate   # один раз
  python -m oracle.sign_keys show       # показать публичный ключ
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from eth_account import Account

KEY_DIR = Path(__file__).parent / "keys"
PRIV_PATH = KEY_DIR / "signing_key.json"   # НЕ коммитить (в .gitignore)
PUB_PATH = KEY_DIR / "signing_pubkey.txt"  # коммитить — это публичный


def generate() -> None:
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    if PRIV_PATH.exists():
        print(f"ALREADY EXISTS: {PRIV_PATH}")
        print("Удали вручную, если действительно хочешь сгенерить новый ключ.")
        sys.exit(1)
    acct = Account.create()
    PRIV_PATH.write_text(json.dumps({
        "private_key": acct.key.hex(),
        "address": acct.address,
    }, indent=2), encoding="utf-8")
    PUB_PATH.write_text(acct.address + "\n", encoding="utf-8")
    print(f"Generated signing key.")
    print(f"  PRIVATE (НЕ КОММИТИТЬ): {PRIV_PATH}")
    print(f"  PUBLIC address (для README/потребителей): {acct.address}")


def load_signer() -> Account:
    if not PRIV_PATH.exists():
        raise FileNotFoundError(
            f"Нет ключа подписи. Запусти: python -m oracle.sign_keys generate")
    data = json.loads(PRIV_PATH.read_text(encoding="utf-8"))
    return Account.from_key(data["private_key"])


def show() -> None:
    if not PUB_PATH.exists():
        print("Нет публичного ключа — запусти 'generate' сначала.")
        sys.exit(1)
    print(PUB_PATH.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("generate", "show"):
        print("Использование: python -m oracle.sign_keys {generate|show}")
        sys.exit(1)
    {"generate": generate, "show": show}[sys.argv[1]]()
