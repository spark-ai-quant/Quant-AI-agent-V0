STRATEGY_NAME = "kdj_timing"

PARAM_SCHEMA = {
    "stock_pool_type": {"type": "str", "default": "hs300"},
    "stock_list": {"type": "list", "default": []},
    "k_period": {"type": "int", "default": 9},
    "buy_threshold": {"type": "float", "default": 20},
    "sell_threshold": {"type": "float", "default": 80},
    "max_hold": {"type": "int", "default": 10},
}


def generate(params):

    stock_pool_type = params.get("stock_pool_type", "hs300")
    stock_list = params.get("stock_list", [])
    k_period = params.get("k_period", 9)
    buy_threshold = params.get("buy_threshold", 20)
    sell_threshold = params.get("sell_threshold", 80)
    max_hold = params.get("max_hold", 10)

    return f"""
from jqdata import *
import pandas as pd
from templates.common import get_stock_pool


def _calc_k(df, n={k_period}):
    low = df.low.rolling(n).min()
    high = df.high.rolling(n).max()
    rsv = (df.close - low) / (high - low) * 100
    return rsv.ewm(com=2).mean().iloc[-1]


def trade(context):

    stocks = get_stock_pool(context, "{stock_pool_type}", {stock_list})

    buy, sell = [], []

    for s in stocks:
        df = get_price(s, count=30, end_date=context.previous_date,
                       fields=["close","high","low"])

        if df is None or len(df) < {k_period}:
            continue

        k = _calc_k(df)

        if k < {buy_threshold}:
            buy.append(s)
        elif k > {sell_threshold}:
            sell.append(s)

    current = list(context.portfolio.positions.keys())

    for s in current:
        if s in sell:
            order_target(s, 0)

    remain = {max_hold} - len(context.portfolio.positions)

    if remain <= 0:
        return

    buy = buy[:remain]

    if not buy:
        return

    w = 1.0 / len(buy)

    for s in buy:
        order_target_percent(s, w)


def initialize(context):
    set_option("use_real_price", True)
    run_daily(trade, time="09:35")
"""
