
from jqdata import *

import pandas as pd


def _order_target_percent(context, security, percent):
    if "order_target_percent" in globals():
        return order_target_percent(security, percent)
    if "order_target_value" in globals():
        return order_target_value(security, context.portfolio.total_value * percent)
    if hasattr(context, "order_target_percent"):
        return context.order_target_percent(security, percent)
    if hasattr(context, "order_target_value"):
        return context.order_target_value(security, context.portfolio.total_value * percent)
    raise NameError("order_target_percent is not defined in this environment")


def _order_target_zero(context, security):
    if "order_target" in globals():
        return order_target(security, 0)
    if "order_target_value" in globals():
        return order_target_value(security, 0)
    if hasattr(context, "order_target"):
        return context.order_target(security, 0)
    if hasattr(context, "order_target_value"):
        return context.order_target_value(security, 0)
    raise NameError("order_target is not defined in this environment")


def _stock_pool(context):
    current_data = get_current_data()
    securities = get_all_securities("stock", date=context.previous_date)
    if securities is None or securities.empty:
        return []

    return [
        stock
        for stock in securities.index
        if not current_data[stock].paused
        and not current_data[stock].is_st
        and "ST" not in current_data[stock].name
    ]


def _score_candidates(context, candidates):
    if not candidates:
        return pd.DataFrame()

    fundamentals = get_fundamentals(
        query(
            valuation.code,
            valuation.pe_ratio,
            valuation.pb_ratio,
            indicator.roe,
            balance.total_liability,
            balance.total_assets,
        ).filter(valuation.code.in_(candidates)),
        date=context.previous_date,
    )

    if fundamentals is None or fundamentals.empty:
        return pd.DataFrame()

    df = fundamentals.dropna().copy()
    if df.empty:
        return df

    df = df[(df["pe_ratio"] > 0) & (df["pb_ratio"] > 0) & (df["total_assets"] > 0)]
    if df.empty:
        return df

    df["debt_ratio"] = df["total_liability"] / df["total_assets"]
    pe_cap = df["pe_ratio"].mean() * 1.5
    pb_cap = min(df["pb_ratio"].mean() * 1.5, 2.0)

    df = df[
        (df["pe_ratio"] < pe_cap)
        & (df["pb_ratio"] < pb_cap)
        & (df["debt_ratio"] < 0.8)
    ]
    if df.empty:
        return df

    df["score"] = (
        (-df["pe_ratio"]).rank(pct=True)
        + (-df["pb_ratio"]).rank(pct=True)
        + df["roe"].rank(pct=True)
        + (1 - df["debt_ratio"]).rank(pct=True)
    )
    return df.sort_values("score", ascending=False)


def rebalance(context):
    candidates = _stock_pool(context)
    ranked = _score_candidates(context, candidates)
    if ranked.empty:
        return

    targets = ranked["code"].head(30).tolist()
    current_positions = list(context.portfolio.positions.keys())
    target_set = set(targets)

    for stock in current_positions:
        if stock not in target_set:
            _order_target_zero(context, stock)

    if not targets:
        return

    weight = 1.0 / len(targets)
    for stock in targets:
        _order_target_percent(context, stock, weight)


def initialize(context):
    set_benchmark("000852.XSHG")
    set_option("use_real_price", True)
    run_monthly(rebalance, monthday=1, time="09:35")
