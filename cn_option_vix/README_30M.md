# Half-hour CN Option VIX extension

This extension leaves the VIX mathematics unchanged and adds two data paths:

1. `pipeline.build_recent_30m`: fetch the latest N trading days of native RQData 30-minute option bars.
2. `pipeline.monitor_30m`: append a live observation at each completed half-hour market slot.

## Fixed sampling points

Financial options trade from 09:31-11:30 and 13:01-15:00. A complete day therefore uses:

```text
10:00 10:30 11:00 11:30 13:30 14:00 14:30 15:00
```

No artificial 09:30 or 13:00 observations are created.

## Data contract

Historical data:

- contracts: `rq.options.get_contracts(underlying=symbol, trading_date=date)`
- contract metadata: `rq.instruments(ids)`
- date-correct ETF option strike: daily `strike_price`
- observation price: native `30m close`
- observation OI: native `30m open_interest`

Live data:

- observation price: `current_snapshot.last`
- observation OI: `current_snapshot.open_interest`

The historical `30m close` and live `last` use the same latest-transaction price convention. Bid/ask midpoint is not mixed into the series.

All merges use explicit keys (`order_book_id`, `datetime`). There is no positional concatenation, no forward fill, and no future-bar fallback.

## Install the patch

From the directory containing your existing `cn_option_vix` folder:

```bash
cd /Users/wonderfulren/Desktop/coding/quant
cp -a cn_option_vix cn_option_vix.backup.$(date +%Y%m%d_%H%M%S)
unzip -o /path/to/cn_option_vix_30m_patch.zip
```

The ZIP contains a top-level `cn_option_vix/` directory and overwrites only modified/new source files.

## Build the latest five trading days

```bash
cd /Users/wonderfulren/Desktop/coding/quant
conda activate rqvix
export RQDATA_URI='tcp://...'
python -m cn_option_vix.pipeline.build_recent_30m --days 5
```

To pin the final date explicitly:

```bash
python -m cn_option_vix.pipeline.build_recent_30m \
  --days 5 \
  --asof 2026-07-13
```

The latest selected date is always refreshed because it may still be forming. Older dates are reused from immutable caches. To refresh all five dates:

```bash
python -m cn_option_vix.pipeline.build_recent_30m --days 5 --force
```

## Outputs

```text
outputs/vix_30m_latest5.parquet
outputs/vix_30m_latest5.csv
outputs/vix_30m_latest5_audit.csv
outputs/vix_30m_latest5_contracts.parquet
outputs/vix_30m_latest5_summary.json
```

`audit.csv` records every timestamp × instrument status. `contracts.parquet` preserves the exact contract-level rows used in the VIX calculation.

## Live one-shot test

Run only at one of the configured Shanghai-market timestamps:

```bash
python -m cn_option_vix.pipeline.monitor_30m \
  --once \
  --timestamp '2026-07-13 14:30'
```

For continuous fixed-slot monitoring:

```bash
python -m cn_option_vix.pipeline.monitor_30m
```

## Algorithm regression

The daily cached sample for 2024-06-03 through 2024-06-07 was computed before and after the refactor. All rows and columns are identical, with maximum absolute numeric difference `0.0`.
