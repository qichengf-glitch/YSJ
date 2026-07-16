"""Build the latest N trading days of half-hour CN financial-option VIX data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from cn_option_vix.config import ROSTER
from cn_option_vix.core.instrument_vix import instrument_vix_from_snapshot
from cn_option_vix.data.intraday_chains import (
    assemble_historical_snapshot,
    expected_timestamps,
    fetch_historical_bars,
    latest_trading_dates,
    load_contract_plan,
    quota_snapshot,
)
from cn_option_vix.pipeline.one_day import assemble_vix_row

_OUT = Path(__file__).resolve().parent.parent / "outputs"


def _quota_used(q: dict) -> int | None:
    value = q.get("bytes_used")
    return int(value) if value is not None else None


def build_recent_30m(
    n_days: int = 5,
    asof=None,
    force: bool = False,
    out_stem: str = "vix_30m_latest5",
) -> pd.DataFrame:
    """Fetch, validate, compute and save the latest half-hour VIX panel.

    Past-date caches are immutable. The latest selected trading date is always
    refreshed because it may be the current, still-forming trading day.
    """
    dates = latest_trading_dates(n=n_days, asof=asof)
    latest_date = dates[-1]
    _OUT.mkdir(parents=True, exist_ok=True)

    quota_before = quota_snapshot()
    prepared: dict[tuple[str, pd.Timestamp], tuple[pd.DataFrame, pd.DataFrame]] = {}

    print("trading_dates:", ", ".join(str(d.date()) for d in dates))
    for date in dates:
        is_latest = date == latest_date
        for item in ROSTER:
            symbol = item["symbol"]
            refresh = bool(force or is_latest)
            print(f"prepare {date.date()} {symbol} refresh={refresh}")
            plan = load_contract_plan(symbol, date, force=refresh)
            bars = fetch_historical_bars(symbol, date, plan, force=refresh)
            prepared[(symbol, date)] = (plan, bars)

    rows: list[dict] = []
    audits: list[dict] = []
    contract_points: list[pd.DataFrame] = []

    all_iv_cols = ["iv_" + item["symbol"] for item in ROSTER]

    for date in dates:
        for timestamp in expected_timestamps(date):
            per_inst = []
            point_has_any_raw_bar = False
            slot_audits = []
            slot_contract_points = []

            for item in ROSTER:
                symbol = item["symbol"]
                plan, bars = prepared[(symbol, date)]
                if not bars[bars["datetime"] == timestamp].empty:
                    point_has_any_raw_bar = True

                snap, audit_obj, point = assemble_historical_snapshot(
                    symbol, date, timestamp, plan, bars
                )
                audit = audit_obj.as_dict()
                if not point.empty:
                    slot_contract_points.append(point)

                result = instrument_vix_from_snapshot(symbol, date, snap)
                if result is None:
                    if audit["status"] == "chain_ready":
                        audit["status"] = "vix_calculation_failed"
                else:
                    result = dict(result)
                    result["group"] = item["group"]
                    per_inst.append(result)
                    audit["status"] = "ok" if result.get("ok") else "invalid_vix"
                    audit["vix"] = result.get("vix")
                    audit["oi"] = result.get("oi")
                    audit["n_strikes_near"] = result.get("n_strikes_near")
                slot_audits.append(audit)

            # Future slots on a still-forming current day have no bars at all.
            if not point_has_any_raw_bar:
                continue

            audits.extend(slot_audits)
            contract_points.extend(slot_contract_points)
            row = assemble_vix_row(timestamp, per_inst)
            row["timestamp"] = pd.Timestamp(row.pop("date"))
            for col in all_iv_cols:
                row.setdefault(col, None)
            row["expected_instruments"] = len(ROSTER)
            row["missing_instruments"] = len(ROSTER) - int(row["n_instruments"])
            rows.append(row)
            print(
                f"computed {timestamp}: "
                f"{row['n_instruments']}/{len(ROSTER)} instruments, "
                f"overall={row.get('overall')}"
            )

    if not rows:
        raise RuntimeError("no half-hour rows were computed; inspect API/cache logs")

    df = pd.DataFrame(rows).set_index("timestamp").sort_index()
    if df.index.duplicated().any():
        raise AssertionError("duplicate output timestamp detected")

    audit_df = pd.DataFrame(audits).sort_values(["timestamp", "symbol"])
    if contract_points:
        contract_df = pd.concat(contract_points, ignore_index=True)
        contract_df = contract_df.sort_values(
            ["timestamp", "symbol", "days", "strike", "cp", "order_book_id"]
        )
        duplicate_keys = ["timestamp", "symbol", "order_book_id"]
        if contract_df.duplicated(duplicate_keys).any():
            raise AssertionError("duplicate contract/timestamp key after assembly")
    else:
        contract_df = pd.DataFrame()

    parquet_path = _OUT / f"{out_stem}.parquet"
    csv_path = _OUT / f"{out_stem}.csv"
    audit_path = _OUT / f"{out_stem}_audit.csv"
    contracts_path = _OUT / f"{out_stem}_contracts.parquet"
    summary_path = _OUT / f"{out_stem}_summary.json"

    df.to_parquet(parquet_path)
    df.to_csv(csv_path)
    audit_df.to_csv(audit_path, index=False)
    if not contract_df.empty:
        contract_df.to_parquet(contracts_path, index=False)

    quota_after = quota_snapshot()
    used_before = _quota_used(quota_before)
    used_after = _quota_used(quota_after)
    delta = (
        used_after - used_before
        if used_before is not None and used_after is not None
        else None
    )
    summary = {
        "trading_dates": [str(d.date()) for d in dates],
        "n_output_rows": int(len(df)),
        "first_timestamp": str(df.index.min()),
        "last_timestamp": str(df.index.max()),
        "mean_valid_instruments": float(df["n_instruments"].mean()),
        "min_valid_instruments": int(df["n_instruments"].min()),
        "quota_bytes_before": used_before,
        "quota_bytes_after": used_after,
        "quota_bytes_used_this_run": delta,
        "price_source": "RQData native 30m close",
        "open_interest_source": "RQData native 30m open_interest",
        "join_keys": ["order_book_id", "datetime"],
        "forward_fill": False,
        "core_path": "instrument_vix_from_snapshot (shared with daily pipeline)",
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print("saved:", parquet_path)
    print("saved:", csv_path)
    print("saved:", audit_path)
    print("saved:", contracts_path)
    print("saved:", summary_path)
    if delta is not None:
        print(f"RQData traffic this run: {delta / 1024**2:.3f} MiB")
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=5)
    parser.add_argument("--asof", default=None, help="YYYY-MM-DD; default latest trading date")
    parser.add_argument(
        "--force",
        action="store_true",
        help="refresh all five dates instead of refreshing only the latest date",
    )
    parser.add_argument("--out-stem", default="vix_30m_latest5")
    args = parser.parse_args()
    build_recent_30m(
        n_days=args.days,
        asof=args.asof,
        force=args.force,
        out_stem=args.out_stem,
    )


if __name__ == "__main__":
    main()
