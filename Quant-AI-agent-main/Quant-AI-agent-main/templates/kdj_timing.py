STRATEGY_NAME = "kdj_timing"

PARAM_SCHEMA = {
    "stock_pool_type": {
        "type": "str",
        "default": "all",
        "description": "all / hs300 / zz500 / custom",
    },
    "stock_list": {
        "type": "list",
        "default": [],
        "description": "custom stock list",
    },
    "k_period": {
        "type": "int",
        "default": 9,
    },
    "buy_threshold": {
        "type": "float",
        "default": 20,
    },
    "sell_threshold": {
        "type": "float",
        "default": 80,
    },
    "max_hold": {
        "type": "int",
        "default": 10,
    },
}


def generate(params):

    stock_pool_type = params.get("stock_pool_type", "all")
    stock_list = params.get("stock_list", [])
    k_period = params.get("k_period", 9)
    buy_threshold = params.get("buy_threshold", 20)
    sell_threshold = params.get("sell_threshold", 80)
    max_hold = params.get("max_hold", 10)

    return f"""
from jqdata import *
import pandas as pd


# =========================
# 股票池（支持扩展）
# =========================
def _get_stock_pool(context):

    current_data = get_current_data()

    # ===== 自定义股票 =====
    if "{stock_pool_type}" == "custom":
        pool = {stock_list}
    else:
        if "{stock_pool_type}" == "hs300":
            pool = get_index_stocks("000300.XSHG")
        elif "{stock_pool_type}" == "zz500":
            pool = get_index_stocks("000905.XSHG")
        else:
            securities = get_all_securities("stock", date=context.previous_date)
            pool = list(securities.index)

    # ===== 过滤 =====
    final_pool = []
    for stock in pool:

        data = current_data[stock]

        if data.paused:
            continue
        if data.is_st or "ST" in data.name or "*" in data.name:
            continue

        if data.high_limit == data.low_limit:
            continue
        if data.last_price >= data.high_limit * 0.99:
            continue
        if data.last_price <= data.low_limit * 1.01:
            continue

        final_pool.append(stock)

    return final_pool


# =========================
# KDJ计算
# =========================
def _calc_kdj(df, n={k_period}):

    low_list = df['low'].rolling(n).min()
    high_list = df['high'].rolling(n).max()

    rsv = (df['close'] - low_list) / (high_list - low_list) * 100

    K = rsv.ewm(com=2).mean()
    D = K.ewm(com=2).mean()
    J = 3*K - 2*D

    return K.iloc[-1], D.iloc[-1], J.iloc[-1]


# =========================
# 信号生成
# =========================
def _generate_signals(context, stocks):

    buy_list = []
    sell_list = []

    for stock in stocks:

        df = get_price(
            stock,
            count=30,
            end_date=context.previous_date,
            fields=['close','high','low'],
        )

        if df is None or len(df) < 10:
            continue

        K, D, J = _calc_kdj(df)

        if K < {buy_threshold}:
            buy_list.append(stock)

        elif K > {sell_threshold}:
            sell_list.append(stock)

    return buy_list, sell_list


# =========================
# 调仓
# =========================
def trade(context):

    stocks = _get_stock_pool(context)

    buy_list, sell_list = _generate_signals(context, stocks)

    current_positions = list(context.portfolio.positions.keys())

    # ===== 卖 =====
    for stock in current_positions:
        if stock in sell_list:
            order_target(stock, 0)

    # ===== 买 =====
    current_count = len(context.portfolio.positions)
    remaining = {max_hold} - current_count

    if remaining <= 0:
        return

    buy_list = buy_list[:remaining]

    if not buy_list:
        return

    weight = 1.0 / len(buy_list)

    for stock in buy_list:
        order_target_percent(stock, weight)


def initialize(context):
    set_option("use_real_price", True)
    run_daily(trade, time="09:35")
"""