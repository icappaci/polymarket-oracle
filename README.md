# Polymarket Oracle (MVP)

Signed JSON-snapshot Polymarket-данных: топ активных рынков и топ-кошельков по 30-дневному PnL.
Подписано ECDSA-ключом (secp256k1, как у Ethereum).

## Endpoint (после deploy)

```
GET https://<your-worker>.workers.dev/snapshot.json
```

Содержит:
- `top_markets[]` — топ активных рынков (volume_usd, liquidity_usd, end_date_utc)
- `top_wallets_by_30d_pnl[]` — топ-100 кошельков по realized PnL за 30 дней (win_rate, n_trades)
- `signature` — ECDSA-подпись канонического JSON

## Проверка подписи (Python, для потребителей)

```python
from oracle.verify_snapshot import verify
from pathlib import Path
verify(Path("snapshot.json"))   # True/False
```

Или вживую любым eth_account-совместимым клиентом — алгоритм:
1. Удалить блок `"signature"` из payload
2. `canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))`
3. `digest = sha256(canonical)`
4. `recovered = ecrecover(eth_msg_hash(digest), signature_hex)`
5. Сравнить `recovered == signature.signer_address`

## Локальный pipeline

```bash
# Один раз: генерация ключа (приватный в keys/, НЕ коммитится)
python -m oracle.sign_keys generate

# Каждый прогон: собрать + подписать snapshot
python -m oracle.build_snapshot

# Проверить подпись локально
python -m oracle.verify_snapshot
```

## Cron (например, каждую минуту)

Windows (Task Scheduler) / Linux (cron):
```
*/1 * * * * cd /path/to/polymarket_wallet_ranker && python -m oracle.build_snapshot
```

## SLA (planned)

- Update frequency: 60 seconds
- Data freshness: ≤ 90 seconds (cron + DuckDB read)
- Signature: secp256k1 ECDSA, deterministic over canonical JSON
- Endpoint uptime: Cloudflare Workers ≥ 99.9%

## Использование (для prediction-протоколов)

Используйте feed как:
- Reference price source для аналогичных событий
- Whale-attribution signal (smart-money flow)
- Liquidity health monitoring (если в Polymarket пересохнет — раннее предупреждение)

## Pricing

- **Free tier:** публичный snapshot.json, 60s update — без SLA-обязательств
- **Pro tier ($500/мес):** dedicated endpoint, 10s update, SLA 99.9%, alerts on stale
- **Enterprise ($2000/мес):** historical query API, custom signals, дашборд

## Contact

`<your_handle>` (TG/Discord), repo issues.
