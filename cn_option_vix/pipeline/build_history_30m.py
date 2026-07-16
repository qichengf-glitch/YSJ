"""Quota-aware, resumable half-hour CN financial-option VIX history builder.

The VIX mathematics are unchanged. This module only streams date-correct
contract rosters and native 30-minute close/open-interest observations into the
shared ``instrument_vix_from_snapshot`` calculation path.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from cn_option_vix.config import ROSTER
from cn_option_vix.core.instrument_vix import instrument_vix_from_snapshot
from cn_option_vix.data.intraday_chains import (
    assemble_historical_snapshot,
    expected_timestamps,
    fetch_historical_bars,
    load_contract_plan,
    quota_snapshot,
    trading_dates_between,
)
from cn_option_vix.pipeline.one_day import assemble_vix_row

_OUT = Path(__file__).resolve().parent.parent / "outputs"


def _int_or_none(value) -> int | None:
    return int(value) if value is not None else None


def _remaining_bytes(q: dict) -> int | None:
    limit = q.get("bytes_limit")
    used = q.get("bytes_used")
    if limit in (None, 0) or used is None:
        return None
    return max(0, int(limit) - int(used))


def _load_vix(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "timestamp" not in df.columns:
        raise ValueError(f"existing output has no timestamp column: {path}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
    return df.set_index("timestamp").sort_index()


def _load_audit(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


def _atomic_save_table(df: pd.DataFrame, csv_path: Path, parquet_path: Path) -> None:
    csv_tmp = csv_path.with_suffix(".tmp.csv")
    parquet_tmp = parquet_path.with_suffix(".tmp.parquet")
    df.to_csv(csv_tmp)
    df.to_parquet(parquet_tmp)
    csv_tmp.replace(csv_path)
    parquet_tmp.replace(parquet_path)


def _atomic_save_audit(df: pd.DataFrame, path: Path) -> None:
    tmp = path.with_suffix(".tmp.csv")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def _completed_dates(df: pd.DataFrame) -> set[pd.Timestamp]:
    if df.empty:
        return set()
    counts = pd.Series(1, index=df.index).groupby(df.index.normalize()).sum()
    return {
        pd.Timestamp(day).normalize()
        for day, count in counts.items()
        if int(count) == 8
    }


def _compute_date(date: pd.Timestamp, force: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    prepared: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
    for item in ROSTER:
        symbol = item["symbol"]
        print(f"  prepare {symbol}", flush=True)
        plan = load_contract_plan(symbol, date, force=force)
        bars = fetch_historical_bars(symbol, date, plan, force=force)
        prepared[symbol] = (plan, bars)

    rows: list[dict] = []
    audits: list[dict] = []
    all_iv_cols = ["iv_" + item["symbol"] for item in ROSTER]

    for timestamp in expected_timestamps(date):
        per_inst = []
        slot_audits = []
        point_has_any_raw_bar = False

        for item in ROSTER:
            symbol = item["symbol"]
            plan, bars = prepared[symbol]
            if not bars[bars["datetime"] == timestamp].empty:
                point_has_any_raw_bar = True

            snap, audit_obj, _point = assemble_historical_snapshot(
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
                audit["n_strikes_near"] = result.get("n_strikes_near")
            slot_audits.append(audit)

        if not point_has_any_raw_bar:
            continue

        audits.extend(slot_audits)
        row = assemble_vix_row(timestamp, per_inst)
        row["timestamp"] = pd.Timestamp(row.pop("date"))
        for col in all_iv_cols:
            row.setdefault(col, None)
        row["expected_instruments"] = len(ROSTER)
        row["missing_instruments"] = len(ROSTER) - int(row["n_instruments"])
        rows.append(row)
        print(
            f"  {timestamp.time()} valid={row['n_instruments']}/{len(ROSTER)} "
            f"overall={row.get('overall')}",
            flush=True,
        )

    if len(rows) != 8:
        raise RuntimeError(
            f"{date.date()} produced {len(rows)} half-hour rows; expected 8. "
            "The day was not checkpointed and is safe to rerun."
        )

    out = pd.DataFrame(rows).set_index("timestamp").sort_index()
    if out.index.duplicated().any():
        raise AssertionError(f"duplicate timestamp on {date.date()}")
    audit_df = pd.DataFrame(audits).sort_values(["timestamp", "symbol"])
    return out, audit_df


def build_history_30m(
    start,
    end,
    out_stem: str = "vix_30m_2y",
    force: bool = False,
    probe_days: int = 10,
    reserve_mib: float = 64.0,
    safety_factor: float = 1.15,
) -> pd.DataFrame:
    """Build an inclusive trading-date range with automatic quota preflight.

    The first ``probe_days`` newly processed dates are retained as real output.
    Their measured RQData traffic is extrapolated conservatively. Processing
    continues automatically only when the remaining quota covers the projection
    plus ``reserve_mib``.
    """
    if probe_days <= 0:
        raise ValueError("probe_days must be positive")
    if safety_factor < 1.0:
        raise ValueError("safety_factor must be >= 1")

    dates = trading_dates_between(start, end)
    if not dates:
        raise RuntimeError("no trading dates in requested range")

    _OUT.mkdir(parents=True, exist_ok=True)
    csv_path = _OUT / f"{out_stem}.csv"
    parquet_path = _OUT / f"{out_stem}.parquet"
    audit_path = _OUT / f"{out_stem}_audit.csv"
    summary_path = _OUT / f"{out_stem}_summary.json"
    error_path = _OUT / f"{out_stem}_last_error.json"

    full_df = _load_vix(csv_path)
    audit_df = _load_audit(audit_path)
    completed = _completed_dates(full_df)
    pending = [d for d in dates if force or d not in completed]

    quota_start = quota_snapshot()
    used_start = _int_or_none(quota_start.get("bytes_used"))
    left_start = _remaining_bytes(quota_start)
    reserve_bytes = int(reserve_mib * 1024**2)

    print(
        f"range: {dates[0].date()} -> {dates[-1].date()} "
        f"({len(dates)} trading days)",
        flush=True,
    )
    print(
        f"completed={len(dates) - len(pending)} pending={len(pending)}",
        flush=True,
    )
    if left_start is not None:
        print(
            f"quota remaining before run: {left_start / 1024**2:.3f} MiB; "
            f"reserve={reserve_mib:.1f} MiB",
            flush=True,
        )

    processed_new = 0
    measured_download_days = 0
    measured_download_bytes = 0
    projected_checked = False

    for idx, date in enumerate(pending, start=1):
        q_before = quota_snapshot()
        left_before = _remaining_bytes(q_before)
        if left_before is not None and left_before <= reserve_bytes:
            print("quota reserve reached; stopping safely", flush=True)
            break

        print(f"[{idx}/{len(pending)}] {date.date()}", flush=True)
        try:
            day_df, day_audit = _compute_date(date, force=force)
        except Exception as exc:
            error = {
                "date": str(date.date()),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "note": "No partial output for this date was checkpointed.",
            }
            error_path.write_text(json.dumps(error, indent=2, ensure_ascii=False))
            raise

        # Replace any partial/forced version of this date and checkpoint atomically.
        if not full_df.empty:
            full_df = full_df[full_df.index.normalize() != date]
        full_df = pd.concat([full_df, day_df]).sort_index()
        if full_df.index.duplicated().any():
            raise AssertionError("duplicate timestamp in cumulative output")

        if not audit_df.empty and "timestamp" in audit_df.columns:
            audit_df = audit_df[
                pd.to_datetime(audit_df["timestamp"]).dt.normalize() != date
            ]
        audit_df = pd.concat([audit_df, day_audit], ignore_index=True)
        audit_df = audit_df.sort_values(["timestamp", "symbol"])

        _atomic_save_table(full_df, csv_path, parquet_path)
        _atomic_save_audit(audit_df, audit_path)
        processed_new += 1

        q_after = quota_snapshot()
        used_before = _int_or_none(q_before.get("bytes_used"))
        used_after = _int_or_none(q_after.get("bytes_used"))
        day_delta = (
            used_after - used_before
            if used_before is not None and used_after is not None
            else None
        )
        if day_delta is not None:
            print(f"  traffic this day: {day_delta / 1024**2:.3f} MiB", flush=True)
            if day_delta > 0:
                measured_download_days += 1
                measured_download_bytes += day_delta

        # Conservative automatic preflight after real, retained downloads.
        required_probe_days = min(probe_days, len(pending))
        if (
            not projected_checked
            and measured_download_days >= required_probe_days
        ):
            projected_checked = True
            used_now = _int_or_none(q_after.get("bytes_used"))
            left_now = _remaining_bytes(q_after)
            if used_now is not None and left_now is not None:
                observed = measured_download_bytes
                avg = observed / measured_download_days
                remaining_days = len(pending) - processed_new
                projected = avg * remaining_days * safety_factor
                available = max(0, left_now - reserve_bytes)
                print(
                    "preflight: "
                    f"observed={observed / 1024**2:.3f} MiB / "
                    f"{measured_download_days} downloaded days, "
                    f"avg={avg / 1024**2:.3f} MiB/day, "
                    f"projected_remaining_with_{safety_factor:.2f}x="
                    f"{projected / 1024**2:.3f} MiB, "
                    f"available_after_reserve={available / 1024**2:.3f} MiB",
                    flush=True,
                )
                if projected > available:
                    summary = {
                        "status": "stopped_after_preflight_insufficient_quota",
                        "start": str(dates[0].date()),
                        "end": str(dates[-1].date()),
                        "trading_days": len(dates),
                        "completed_rows": int(len(full_df)),
                        "completed_dates": len(_completed_dates(full_df)),
                        "probe_days": measured_download_days,
                        "observed_probe_bytes": observed,
                        "average_bytes_per_day": avg,
                        "projected_remaining_bytes_with_safety": projected,
                        "available_bytes_after_reserve": available,
                        "reserve_mib": reserve_mib,
                        "safety_factor": safety_factor,
                    }
                    summary_path.write_text(
                        json.dumps(summary, indent=2, ensure_ascii=False)
                    )
                    print(
                        "STOP: optimized probe still projects insufficient quota. "
                        "Downloaded probe dates are saved; rerunning will resume.",
                        flush=True,
                    )
                    return full_df

        status = {
            "status": "running",
            "start": str(dates[0].date()),
            "end": str(dates[-1].date()),
            "trading_days": len(dates),
            "completed_rows": int(len(full_df)),
            "completed_dates": len(_completed_dates(full_df)),
            "last_completed_date": str(date.date()),
            "price_source": "RQData native 30m close",
            "open_interest_source": "RQData native 30m open_interest",
            "join_keys": ["order_book_id", "datetime"],
            "forward_fill": False,
            "core_path": "instrument_vix_from_snapshot (shared with daily pipeline)",
        }
        summary_path.write_text(json.dumps(status, indent=2, ensure_ascii=False))

    quota_end = quota_snapshot()
    used_end = _int_or_none(quota_end.get("bytes_used"))
    total_delta = (
        used_end - used_start
        if used_start is not None and used_end is not None
        else None
    )
    final_completed = _completed_dates(full_df)
    final_status = "complete" if all(d in final_completed for d in dates) else "paused"
    summary = {
        "status": final_status,
        "start": str(dates[0].date()),
        "end": str(dates[-1].date()),
        "trading_days": len(dates),
        "completed_dates": len([d for d in dates if d in final_completed]),
        "n_output_rows": int(len(full_df)),
        "first_timestamp": str(full_df.index.min()) if not full_df.empty else None,
        "last_timestamp": str(full_df.index.max()) if not full_df.empty else None,
        "quota_bytes_before": used_start,
        "quota_bytes_after": used_end,
        "quota_bytes_used_this_run": total_delta,
        "price_source": "RQData native 30m close",
        "open_interest_source": "RQData native 30m open_interest",
        "join_keys": ["order_book_id", "datetime"],
        "forward_fill": False,
        "core_path": "instrument_vix_from_snapshot (shared with daily pipeline)",
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print("saved:", csv_path)
    print("saved:", parquet_path)
    print("saved:", audit_path)
    print("saved:", summary_path)
    if total_delta is not None:
        print(f"RQData traffic this run: {total_delta / 1024**2:.3f} MiB")
    print("status:", final_status)
    return full_df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="inclusive YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="inclusive YYYY-MM-DD")
    parser.add_argument("--out-stem", default="vix_30m_2y")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--probe-days", type=int, default=10)
    parser.add_argument("--reserve-mib", type=float, default=64.0)
    parser.add_argument("--safety-factor", type=float, default=1.15)
    args = parser.parse_args()

    try:
        build_history_30m(
            start=args.start,
            end=args.end,
            out_stem=args.out_stem,
            force=args.force,
            probe_days=args.probe_days,
            reserve_mib=args.reserve_mib,
            safety_factor=args.safety_factor,
        )
    except KeyboardInterrupt:
        print("interrupted; completed dates are already checkpointed", file=sys.stderr)
        raise SystemExit(130)


if __name__ == "__main__":
    main()
