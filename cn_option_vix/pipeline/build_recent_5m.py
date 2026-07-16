"""Backfill the latest five trading days at native five-minute frequency."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from cn_option_vix.config import LIVE_DASHBOARD_PARAMS, ROSTER
from cn_option_vix.core.instrument_vix import instrument_vix_from_snapshot
from cn_option_vix.data.five_min_chains import (
    assemble_historical_5m_snapshot,
    expected_5m_timestamps,
    fetch_historical_5m_bars,
)
from cn_option_vix.data.intraday_chains import (
    latest_trading_dates,
    load_contract_plan,
    quota_snapshot,
)
from cn_option_vix.pipeline.one_day import assemble_vix_row
from cn_option_vix.web.storage import DEFAULT_DB_PATH, query_series, upsert_points

_OUT = Path(__file__).resolve().parent.parent / "outputs"


def _quota_used(q: dict) -> int | None:
    value = q.get("bytes_used")
    return int(value) if value is not None else None


def _compute_date_5m(
    date: pd.Timestamp,
    *,
    force: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    prepared: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
    for item in ROSTER:
        symbol = item["symbol"]
        print(f"  prepare {symbol}", flush=True)
        plan = load_contract_plan(symbol, date, force=force)
        bars = fetch_historical_5m_bars(symbol, date, plan, force=force)
        prepared[symbol] = (plan, bars)

    rows: list[dict] = []
    audits: list[dict] = []
    all_iv_cols = ["iv_" + item["symbol"] for item in ROSTER]

    for timestamp in expected_5m_timestamps(date):
        per_inst = []
        slot_audits: list[dict] = []
        point_has_any_raw_bar = False

        for item in ROSTER:
            symbol = item["symbol"]
            plan, bars = prepared[symbol]
            if not bars[bars["datetime"] == timestamp].empty:
                point_has_any_raw_bar = True
            snap, audit_obj, _point = assemble_historical_5m_snapshot(
                symbol, date, timestamp, plan, bars
            )
            audit = audit_obj.as_dict()
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
            slot_audits.append(audit)

        # Future points on a still-forming current day have no raw bars at all.
        if not point_has_any_raw_bar:
            continue

        audits.extend(slot_audits)
        row = assemble_vix_row(timestamp, per_inst)
        row["timestamp"] = pd.Timestamp(row.pop("date"))
        for col in all_iv_cols:
            row.setdefault(col, None)
        row["expected_instruments"] = len(ROSTER)
        row["missing_instruments"] = len(ROSTER) - int(row["n_instruments"])
        row["valid_contracts"] = sum(int(a["valid_prices"]) for a in slot_audits)
        row["missing_quotes"] = sum(
            max(0, int(a["expected_contracts"]) - int(a["valid_prices"]))
            for a in slot_audits
        )
        row["calculated_at"] = datetime.now()
        rows.append(row)
        print(
            f"  {timestamp.time()} valid={row['n_instruments']}/{len(ROSTER)} "
            f"overall={row.get('overall')}",
            flush=True,
        )

    if not rows:
        raise RuntimeError(f"{date.date()} produced no five-minute VIX rows")
    out = pd.DataFrame(rows).set_index("timestamp").sort_index()
    if out.index.duplicated().any():
        raise AssertionError(f"duplicate five-minute timestamp on {date.date()}")
    audit_df = pd.DataFrame(audits).sort_values(["timestamp", "symbol"])
    return out, audit_df


def build_recent_5m(
    n_days: int = 5,
    *,
    asof=None,
    force: bool = False,
    db_path: str | Path = DEFAULT_DB_PATH,
    out_stem: str = "vix_5m_latest5",
    reserve_mib: float = 64.0,
    safety_factor: float = 1.15,
) -> pd.DataFrame:
    dates = latest_trading_dates(n=n_days, asof=asof)
    latest_date = dates[-1]
    quota_before = quota_snapshot()
    _OUT.mkdir(parents=True, exist_ok=True)

    all_audits = []
    reserve_bytes = int(reserve_mib * 1024**2)
    for idx, date in enumerate(dates, start=1):
        q_day_before = quota_snapshot()
        limit = q_day_before.get("bytes_limit")
        used = q_day_before.get("bytes_used")
        left_before = int(limit - used) if limit and used is not None else None
        if left_before is not None and left_before <= reserve_bytes:
            print(f"quota reserve reached ({reserve_mib:.1f} MiB); stopping safely")
            break
        refresh = bool(force or date == latest_date)
        print(f"[{idx}/{len(dates)}] {date.date()} refresh={refresh}", flush=True)
        day_df, day_audit = _compute_date_5m(date, force=refresh)
        records = day_df.reset_index().to_dict("records")
        upsert_points(
            records,
            resolution="5m",
            source="historical_5m_close",
            db_path=db_path,
        )
        all_audits.append(day_audit)
        print(f"  checkpointed {len(day_df)} points", flush=True)

        # Measure the first real day before committing the remaining history.
        # Cached days commonly use ~0 traffic, in which case no extrapolation is needed.
        q_day_after = quota_snapshot()
        after_used = q_day_after.get("bytes_used")
        day_delta = (
            int(after_used) - int(used)
            if after_used is not None and used is not None
            else None
        )
        remaining_dates = len(dates) - idx
        if idx == 1 and day_delta is not None and day_delta > 0 and remaining_dates > 0:
            after_limit = q_day_after.get("bytes_limit")
            left_after = (
                int(after_limit) - int(after_used)
                if after_limit and after_used is not None
                else None
            )
            projected = int(day_delta * remaining_dates * safety_factor)
            available = max(0, left_after - reserve_bytes) if left_after is not None else None
            print(
                f"5m quota probe: {day_delta / 1024**2:.3f} MiB/day; "
                f"projected remaining={projected / 1024**2:.3f} MiB; "
                f"available after reserve={available / 1024**2:.3f} MiB"
                if available is not None
                else f"5m quota probe: {day_delta / 1024**2:.3f} MiB/day",
                flush=True,
            )
            if available is not None and projected > available:
                print(
                    "STOP: remaining quota does not safely cover the other five-minute dates. "
                    "The completed day is committed and rerunning will reuse its cache.",
                    flush=True,
                )
                break

    rows = query_series("5m", db_path=db_path, trading_days=n_days)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").set_index("timestamp")
    audit_df = pd.concat(all_audits, ignore_index=True) if all_audits else pd.DataFrame()

    csv_path = _OUT / f"{out_stem}.csv"
    parquet_path = _OUT / f"{out_stem}.parquet"
    audit_path = _OUT / f"{out_stem}_audit.csv"
    summary_path = _OUT / f"{out_stem}_summary.json"
    df.to_csv(csv_path)
    df.to_parquet(parquet_path)
    audit_df.to_csv(audit_path, index=False)

    quota_after = quota_snapshot()
    before = _quota_used(quota_before)
    after = _quota_used(quota_after)
    delta = after - before if before is not None and after is not None else None
    summary = {
        "trading_dates": [str(d.date()) for d in dates],
        "n_output_rows": int(len(df)),
        "first_timestamp": str(df.index.min()) if not df.empty else None,
        "last_timestamp": str(df.index.max()) if not df.empty else None,
        "quota_bytes_before": before,
        "quota_bytes_after": after,
        "quota_bytes_used_this_run": delta,
        "frequency": LIVE_DASHBOARD_PARAMS["frequency"],
        "price_source": "RQData native 5m close",
        "open_interest_source": "RQData native 5m open_interest",
        "join_keys": ["order_book_id", "datetime"],
        "forward_fill": False,
        "core_path": "instrument_vix_from_snapshot",
        "database": str(Path(db_path)),
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print("saved:", csv_path)
    print("saved:", parquet_path)
    print("saved:", audit_path)
    print("database:", db_path)
    if delta is not None:
        print(f"RQData traffic this run: {delta / 1024**2:.3f} MiB")
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=5)
    parser.add_argument("--asof", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--out-stem", default="vix_5m_latest5")
    parser.add_argument("--reserve-mib", type=float, default=64.0)
    parser.add_argument("--safety-factor", type=float, default=1.15)
    args = parser.parse_args()
    try:
        build_recent_5m(
            n_days=args.days,
            asof=args.asof,
            force=args.force,
            db_path=args.db,
            out_stem=args.out_stem,
            reserve_mib=args.reserve_mib,
            safety_factor=args.safety_factor,
        )
    except KeyboardInterrupt:
        print("interrupted; cached dates and database checkpoints are preserved")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
