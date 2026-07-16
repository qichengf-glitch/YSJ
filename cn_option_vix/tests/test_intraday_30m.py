from types import SimpleNamespace

import pandas as pd

from cn_option_vix.data import intraday_chains as ic


def _plan():
    return pd.DataFrame(
        [
            {"order_book_id": "C10", "maturity_date": "2026-08-01", "days": 10, "term": "near", "cp": "c", "strike": 100.0},
            {"order_book_id": "P10", "maturity_date": "2026-08-01", "days": 10, "term": "near", "cp": "p", "strike": 100.0},
            {"order_book_id": "C20", "maturity_date": "2026-08-11", "days": 20, "term": "next", "cp": "c", "strike": 100.0},
            {"order_book_id": "P20", "maturity_date": "2026-08-11", "days": 20, "term": "next", "cp": "p", "strike": 100.0},
        ]
    ).assign(maturity_date=lambda x: pd.to_datetime(x.maturity_date))


def test_historical_join_is_keyed_and_exact_time_only():
    plan = _plan()
    bars = pd.DataFrame(
        [
            # deliberately shuffled; values identify the contracts
            {"order_book_id": "P20", "datetime": "2026-07-22 10:00", "close": 4.0, "open_interest": 40},
            {"order_book_id": "C10", "datetime": "2026-07-22 10:00", "close": 1.0, "open_interest": 10},
            {"order_book_id": "P10", "datetime": "2026-07-22 10:00", "close": 2.0, "open_interest": 20},
            {"order_book_id": "C20", "datetime": "2026-07-22 10:00", "close": 3.0, "open_interest": 30},
            # future value must never leak into 10:00
            {"order_book_id": "C10", "datetime": "2026-07-22 10:30", "close": 999.0, "open_interest": 999},
        ]
    )
    bars["datetime"] = pd.to_datetime(bars["datetime"])

    snap, audit, point = ic.assemble_historical_snapshot(
        "TEST", "2026-07-22", "2026-07-22 10:00", plan, bars
    )
    assert audit.status == "chain_ready"
    assert len(point) == 4
    near = snap["by_expiry"][10].set_index("cp")
    nxt = snap["by_expiry"][20].set_index("cp")
    assert near.loc["c", "price"] == 1.0
    assert near.loc["p", "price"] == 2.0
    assert nxt.loc["c", "price"] == 3.0
    assert nxt.loc["p", "price"] == 4.0
    assert 999.0 not in point["price"].tolist()


def test_contract_plan_selects_same_near_next_and_daily_strike(monkeypatch, tmp_path):
    date = pd.Timestamp("2026-07-13")
    ids = ["A", "B", "C", "D", "E", "F"]
    maturity = {
        "A": "2026-07-20", "B": "2026-07-20",  # 7d near
        "C": "2026-08-17", "D": "2026-08-17",  # 35d next
        "E": "2026-09-21", "F": "2026-09-21",  # must be excluded
    }
    types = {"A": "C", "B": "P", "C": "C", "D": "P", "E": "C", "F": "P"}
    objs = [
        SimpleNamespace(
            order_book_id=i,
            maturity_date=maturity[i],
            option_type=types[i],
            strike_price=100.0,
        )
        for i in ids
    ]

    monkeypatch.setattr(ic, "ensure_rq", lambda: None)
    monkeypatch.setattr(ic, "_PLAN_DIR", tmp_path)
    monkeypatch.setattr(ic.rq.options, "get_contracts", lambda **kwargs: ids)
    monkeypatch.setattr(ic.rq, "instruments", lambda requested: objs)
    monkeypatch.setattr(
        ic,
        "_daily_strikes",
        lambda requested, d: pd.DataFrame(
            {"order_book_id": requested, "strike_daily": [101.0] * len(requested)}
        ),
    )

    plan = ic.load_contract_plan("TEST", date, force=True)
    assert set(plan["order_book_id"]) == {"A", "B", "C", "D"}
    assert set(plan["days"]) == {7, 35}
    assert (plan["strike"] == 101.0).all()
