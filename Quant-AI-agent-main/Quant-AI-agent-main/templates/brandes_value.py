STRATEGY_NAME = "brandes_value"

PARAM_SCHEMA = {
    "hold_count": {"type": "int", "default": 30},
    "rebalance_period_days": {"type": "int", "default": 1},
    "stock_pool_type": {"type": "str", "default": "all"},
    "stock_list": {"type": "list", "default": []},
}


def generate(params):
    hold_count = params.get("hold_count", 30)
    rebalance_period_days = params.get("rebalance_period_days", 1)
    stock_pool_type = params.get("stock_pool_type", "all")
    stock_list = params.get("stock_list", [])

    return f"""
from jqdata import *
import pandas as pd
from templates.common import get_stock_pool


def _order_target_percent(context, s, p):
    return order_target_percent(s, p)

def _order_target_zero(context, s):
    return order_target(s, 0)


def _score(context, stocks):
    df = get_fundamentals(
        query(
            valuation.code,
            valuation.pe_ratio,
            valuation.pb_ratio,
            indicator.roe,
            balance.total_liability,
            balance.total_assets,
        ).filter(valuation.code.in_(stocks)),
        date=context.previous_date,
    )

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.dropna()
    df["debt"] = df.total_liability / df.total_assets

    df["score"] = (
        (-df.pe_ratio).rank(pct=True)
        + (-df.pb_ratio).rank(pct=True)
        + df.roe.rank(pct=True)
        + (1 - df.debt).rank(pct=True)
    )

    return df.sort_values("score", ascending=False)


def rebalance(context):
    stocks = get_stock_pool(context, "{stock_pool_type}", {stock_list})
    ranked = _score(context, stocks)

    if ranked.empty:
        return

    targets = ranked.code.head({hold_count}).tolist()

    current = list(context.portfolio.positions.keys())

    for s in current:
        if s not in targets:
            _order_target_zero(context, s)

    weight = 1.0 / len(targets)
    for s in targets:
        _order_target_percent(context, s, weight)


def initialize(context):
    set_option("use_real_price", True)
    run_monthly(rebalance, monthday={rebalance_period_days}, time="09:35")
"""
