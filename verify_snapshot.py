"""Проверка подписи Polymarket Oracle snapshot — публичный пример для потребителей.

Запуск:
  python -m oracle.verify_snapshot                # верифицировать oracle/public/snapshot.json
  python -m oracle.verify_snapshot path/to.json   # или произвольный файл

ОТДАЁМ в README ПОЛЬЗОВАТЕЛЯМ как пример проверки.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from eth_account.messages import encode_defunct
from eth_account import Account


def verify(path: Path) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    sig_block = data.pop("signature", None)
    if not sig_block:
        print("FAIL: no signature block")
        return False

    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    digest_hex = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if digest_hex != sig_block["digest_sha256"]:
        print(f"FAIL: digest mismatch")
        print(f"  expected: {sig_block['digest_sha256']}")
        print(f"  computed: {digest_hex}")
        return False

    msg = encode_defunct(text=digest_hex)
    recovered = Account.recover_message(msg, signature=sig_block["signature_hex"])
    if recovered.lower() != sig_block["signer_address"].lower():
        print(f"FAIL: signer mismatch")
        print(f"  claimed:   {sig_block['signer_address']}")
        print(f"  recovered: {recovered}")
        return False

    print("OK: подпись валидна")
    print(f"  signer:   {recovered}")
    print(f"  digest:   {digest_hex}")
    print(f"  ts:       {data.get('generated_at_utc')}")
    print(f"  markets:  {len(data.get('top_markets', []))}")
    print(f"  wallets:  {len(data.get('top_wallets_by_30d_pnl', []))}")
    return True


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).parent / "public" / "snapshot.json")
    if not path.exists():
        print(f"NO FILE: {path}")
        sys.exit(1)
    sys.exit(0 if verify(path) else 1)


if __name__ == "__main__":
    main()
