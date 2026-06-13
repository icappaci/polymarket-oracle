"""Build a signed JSON snapshot of Polymarket data for the Oracle endpoint.

Snapshot contents:
1. timestamp / schema version / signer address
2. top_markets: top-N active markets by volume (from a local DuckDB
   maintained by the Polymarket scraper project)
3. top_wallets_by_30d_pnl: top-N wallets by realized PnL over the last
   30 days (also from DuckDB)
4. ECDSA signature over the canonical JSON (secp256k1, via eth_account)

Run:
  python -m oracle.build_snapshot   # writes oracle/public/snapshot.json
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import duckdb
from eth_account.messages import encode_defunct

ROOT = Path(__file__).parent.parent
# Data source: DuckDB maintained by the Polymarket scraper (separate project).
# Override with env POLYMARKET_DB_PATH if running on a different machine.
import os
_DEFAULT_DB = Path(
    r"C:\Users\icap\OneDrive\Рабочий стол\polymarket_wallet_ranker"
    r"\copy_bot\data\polymarket.duckdb")
DB_PATH = Path(os.environ.get("POLYMARKET_DB_PATH", str(_DEFAULT_DB)))
OUT_DIR = Path(__file__).parent / "public"
OUT_PATH = OUT_DIR / "snapshot.json"

SCHEMA_VERSION = "v0.1"
TOP_MARKETS = 50
TOP_WALLETS = 100
WALLET_LOOKBACK_DAYS = 30


def collect_top_markets(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """Top-N active markets by volume_num."""
    rows = con.execute("""
        SELECT slug, condition_id, title, end_date_utc, volume_num, liquidity_num
        FROM markets
        WHERE active = TRUE AND closed = FALSE AND volume_num IS NOT NULL
        ORDER BY volume_num DESC
        LIMIT ?
    """, [TOP_MARKETS]).fetchall()
    out = []
    for slug, cid, title, end_dt, vol, liq in rows:
        out.append({
            "slug": slug,
            "condition_id": cid,
            "title": (title or "")[:200],
            "end_date_utc": end_dt.isoformat() if end_dt else None,
            "volume_usd": round(float(vol or 0), 2),
            "liquidity_usd": round(float(liq or 0), 2) if liq else None,
        })
    return out


def collect_top_wallets(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """Top-N wallets by realized PnL over the last N days."""
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=WALLET_LOOKBACK_DAYS)
    rows = con.execute("""
        SELECT wallet,
               COUNT(*) AS n_trades,
               SUM(realized_pnl) AS total_pnl,
               SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) AS wins
        FROM closed_positions
        WHERE COALESCE(closed_at_utc, opened_at_utc) >= ?
          AND realized_pnl IS NOT NULL
        GROUP BY wallet
        HAVING COUNT(*) >= 5 AND SUM(realized_pnl) > 0
        ORDER BY total_pnl DESC
        LIMIT ?
    """, [cutoff, TOP_WALLETS]).fetchall()
    out = []
    for wallet, n, pnl, wins in rows:
        out.append({
            "address": wallet,
            "n_trades_30d": int(n),
            "wins_30d": int(wins or 0),
            "win_rate": round(wins / n, 3) if n else 0,
            "realized_pnl_30d": round(float(pnl or 0), 2),
        })
    return out


def build_payload() -> dict:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        now = dt.datetime.now(dt.timezone.utc)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "generated_at_utc": now.isoformat(),
            "generated_at_unix": int(now.timestamp()),
            "source": "polymarket_oracle_mvp",
            "lookback_days": WALLET_LOOKBACK_DAYS,
            "top_markets": collect_top_markets(con),
            "top_wallets_by_30d_pnl": collect_top_wallets(con),
        }
        return payload
    finally:
        con.close()


def sign_payload(payload: dict) -> dict:
    """Add signature and signer address to the payload."""
    from oracle.sign_keys import load_signer
    signer = load_signer()
    # Canonical JSON (sorted keys, no whitespace) -> SHA256 -> ECDSA
    # This deterministic encoding is what consumers re-compute when verifying.
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    digest_hex = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    msg = encode_defunct(text=digest_hex)
    sig = signer.sign_message(msg)
    return {
        **payload,
        "signature": {
            "signer_address": signer.address,
            "algorithm": "ECDSA-secp256k1 over SHA256(canonical_json)",
            "digest_sha256": digest_hex,
            "signature_hex": sig.signature.hex(),
            "recoverable": True,
        },
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    signed = sign_payload(payload)
    OUT_PATH.write_text(json.dumps(signed, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"[oracle] snapshot written: {OUT_PATH} ({size_kb:.1f} KB)")
    print(f"  markets: {len(payload['top_markets'])}")
    print(f"  wallets: {len(payload['top_wallets_by_30d_pnl'])}")
    print(f"  signer:  {signed['signature']['signer_address']}")
    print(f"  digest:  {signed['signature']['digest_sha256'][:16]}...")


if __name__ == "__main__":
    sys.exit(main())
