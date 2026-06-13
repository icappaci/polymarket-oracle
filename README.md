# Polymarket Oracle

A free, signed data feed for [Polymarket](https://polymarket.com). Every minute it publishes a fresh JSON snapshot of:

- **Top 50 active markets** — volume, liquidity, end date, current price
- **Top 100 wallets by 30-day profit** — realized PnL, win rate, trade count

Each snapshot is signed with an ECDSA key, so you can verify the data really came from us and wasn't tampered with in transit.

**Live endpoint:** https://polymarket-oracle.istarley2000.workers.dev/snapshot.json

---

## Try it

```bash
curl https://polymarket-oracle.istarley2000.workers.dev/snapshot.json
```

Or just open it in a browser.

For a health check:
```bash
curl https://polymarket-oracle.istarley2000.workers.dev/health
```

---

## What's inside

```json
{
  "generated_at_unix": 1781390587,
  "signer_address": "0x1C2Dd3AFA33cF338332C47024BdB747d3240551C",
  "signature": "0x...",
  "markets": [
    {
      "slug": "fifwc-bra-mar-2026-06-13",
      "title": "Brazil vs Morocco",
      "volume_usd": 1234567,
      "liquidity_usd": 89000,
      "end_date_utc": "2026-06-13T22:00:00Z",
      "outcomes": [{"name": "Brazil", "price": 0.62}, ...]
    },
    ...
  ],
  "wallets": [
    {
      "address": "0xa5ea13a81d2b7e8e424b182bdc1db08e756bd96a",
      "realized_pnl_usd": 10126164,
      "win_rate": 0.938,
      "n_trades": 130
    },
    ...
  ]
}
```

---

## Verify the signature

Each snapshot is signed with secp256k1 (the same curve Ethereum uses). To verify:

1. Take the snapshot JSON and remove the `signature` field
2. Serialize what's left to canonical JSON: sorted keys, no whitespace
3. SHA-256 hash the result, wrap in Ethereum's signed-message envelope
4. Recover the signer address from the signature
5. Check it matches `0x1C2Dd3AFA33cF338332C47024BdB747d3240551C`

If you'd rather just call a function:

```python
# pip install eth-account
from oracle.verify_snapshot import verify
from pathlib import Path

ok = verify(Path("snapshot.json"))  # True or False
```

Or in JavaScript with [ethers.js](https://docs.ethers.org/) — same algorithm, see `verify_snapshot.py` for reference.

---

## Update frequency

| | Free (this endpoint) | Paid (planned) |
|---|---|---|
| Refresh | Every 60 seconds | 5-10 seconds |
| CDN cache | 30 seconds | None |
| Dedicated endpoint | No (shared) | Yes |
| Stale-data alerts | No | Yes |
| Historical query | No | Yes |
| Uptime SLA | Best effort | 99.9% |

The free tier runs on [Cloudflare Workers](https://workers.cloudflare.com/) and [GitHub raw](https://raw.githubusercontent.com/). It's funded by us — you don't sign up for anything.

If you need tighter latency, custom signals, or a stable SLA, get in touch (see Contact below).

---

## Why we built this

Prediction protocols (Azuro, Overtime, Limitless, SX, Thales) need reference data: what does the rest of the market think a sports outcome is worth? Polymarket has it, but the public API is not signed and historical wallet attribution is undocumented.

This feed gives you both: a snapshot of the current top markets, plus a list of wallets that have been consistently profitable — useful as a smart-money signal or as a secondary oracle source.

---

## Use cases

- **Reference pricing** — compare your odds to the largest prediction venue's current price
- **Smart-money flow** — see which historically-profitable wallets are entering positions right now
- **Liquidity health monitoring** — early warning if a Polymarket market thins out before resolution
- **Settlement cross-check** — verify your own oracle's outcome against Polymarket's resolved price

---

## How to integrate

Nothing to install. Pull the JSON from your service:

```js
// JavaScript example
const r = await fetch("https://polymarket-oracle.istarley2000.workers.dev/snapshot.json");
const snap = await r.json();
const market = snap.markets.find(m => m.slug === "fifwc-bra-mar-2026-06-13");
console.log(market.outcomes);
```

Polled once a minute is plenty — the CDN cache makes that effectively free for us, and you'll always get the latest published snapshot.

---

## Limits

This is the free tier. It's intended for low-frequency reference use:

- **100,000 requests / day** total across all users (Cloudflare free plan)
- **30-second cache** — refreshing more often than that returns the cached copy
- **No SLA** — we aim for "almost always up" but don't promise it

If you're hitting these limits or need stronger guarantees, contact us about a dedicated endpoint.

---

## Contact

- GitHub: open an issue on this repo
- Telegram: TBD (will be added once we have an outreach channel)

---

## License

MIT. The data is public — Polymarket exposes it through their own API. We just package it into a signed, easy-to-consume feed.
