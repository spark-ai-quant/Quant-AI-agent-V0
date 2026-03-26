STRATEGY_NAME = "brandes_value"

PARAM_SCHEMA = {
    "hold_count": {
        "type": "int",
        "default": 30,
        "description": "Number of holdings",
    },
    "rebalance_period_days": {
        "type": "int",
        "default": 1,
        "description": "Rebalance on the Nth trading day of each month",
    },
}


def generate(params):
    hold_count = params.get("hold_count", 30)
    rebalance_period_days = params.get("rebalance_period_days", 1)

    return f"""
from jqdata import *
import pandas as pd
import datetime


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
    return _order_target_percent(context, security, 0)


# =========================
# 股票池过滤（增强版）
# =========================
def _stock_pool(context):
    current_data = get_current_data()
    securities = get_all_securities("stock", date=context.previous_date)

    if securities is None or securities.empty:
        return []

    today = context.current_dt.date()
    pool = []

    for stock in securities.index:

        data = current_data[stock]

        # 停牌
        if data.paused:
            continue

        # ST
        if data.is_st or "ST" in data.name or "*" in data.name:
            continue

        # 次新股（<60天）
        listed_days = (today - securities.loc[stock].start_date).days
        if listed_days < 60:
            continue

        # 涨跌停过滤（避免买不到/卖不掉）
        if data.high_limit == data.low_limit:
            continue
        if data.last_price >= data.high_limit * 0.99:
            continue
        if data.last_price <= data.low_limit * 1.01:
            continue

        pool.append(stock)

    return pool


# =========================
# 因子评分（防未来函数）
# =========================
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

    df = df[
        (df["pe_ratio"] > 0)
        & (df["pb_ratio"] > 0)
        & (df["total_assets"] > 0)
    ]

    if df.empty:
        return df

    df["debt_ratio"] = df["total_liability"] / df["total_assets"]

    # 去极值（更稳）
    pe_cap = df["pe_ratio"].quantile(0.8)
    pb_cap = df["pb_ratio"].quantile(0.8)

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


# =========================
# 调仓
# =========================
def rebalance(context):
    candidates = _stock_pool(context)
    ranked = _score_candidates(context, candidates)

    if ranked.empty:
        return

    targets = ranked["code"].head({hold_count}).tolist()
    current_positions = list(context.portfolio.positions.keys())
    target_set = set(targets)

    # 先卖
    for stock in current_positions:
        if stock not in target_set:
            _order_target_zero(context, stock)

    if not targets:
        return

    # 再买
    weight = 1.0 / len(targets)
    for stock in targets:
        _order_target_percent(context, stock, weight)


def initialize(context):
    set_benchmark("000852.XSHG")
    set_option("use_real_price", True)

    run_monthly(rebalance, monthday={rebalance_period_days}, time="09:35")
"""