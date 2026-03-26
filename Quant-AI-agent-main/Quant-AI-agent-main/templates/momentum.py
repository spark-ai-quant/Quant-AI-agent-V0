STRATEGY_NAME = "momentum"

PARAM_SCHEMA = {
    "lookback_days": {
        "type": "int",
        "default": 20,
        "description": "动量回看周期"
    },
    "stock_count": {
        "type": "int",
        "default": 10,
        "description": "持仓股票数量"
    },
    "stock_pool_type": {
        "type": "str",
        "default": "all",
        "description": "all / hs300 / zz500 / zz1000 / custom"
    },
    "stock_list": {
        "type": "list",
        "default": [],
        "description": "自定义股票池"
    }
}


def generate(params):
    lookback = params.get("lookback_days", 20)
    stock_num = params.get("stock_count", 10)
    stock_pool_type = params.get("stock_pool_type", "all")
    stock_list = params.get("stock_list", [])

    return f"""
from jqdata import *
import pandas as pd
from templates.common import get_stock_pool


# =========================
# 下单函数
# =========================
def _order_target_percent(context, security, percent):
    return order_target_percent(security, percent)


def _order_target_zero(context, security):
    return order_target(security, 0)


# =========================
# 初始化
# =========================
def initialize(context):
    set_option('avoid_future_data', True)   # 防未来函数
    set_option("use_real_price", True)

    g.lookback = {lookback}
    g.stock_num = {stock_num}

    run_daily(trade, time='09:35')


# =========================
# 动量计算（无未来函数）
# =========================
def calc_momentum(context, stocks, lookback):

    df = get_price(
        stocks,
        count=lookback,
        end_date=context.previous_date,   # 🔥关键：防未来函数
        fields=['close'],
        panel=False
    )

    if df is None or df.empty:
        return pd.Series()

    price_df = df.pivot(index='time', columns='code', values='close')

    if price_df.shape[0] < 2:
        return pd.Series()

    returns = price_df.iloc[-1] / price_df.iloc[0] - 1
    returns = returns.dropna()

    return returns


# =========================
# 主交易逻辑
# =========================
def trade(context):

    stocks = get_stock_pool(
        context,
        stock_pool_type="{stock_pool_type}",
        stock_list={stock_list}
    )

    if not stocks:
        return

    returns = calc_momentum(context, stocks, g.lookback)

    if returns is None or len(returns) == 0:
        return

    # 选动量最高
    top = returns.sort_values(ascending=False).head(g.stock_num)

    target_set = set(top.index)
    current_positions = list(context.portfolio.positions.keys())

    # =========================
    # 先卖出
    # =========================
    for stock in current_positions:
        if stock not in target_set:
            _order_target_zero(context, stock)

    # =========================
    # 再买入
    # =========================
    if len(target_set) == 0:
        return

    weight = 1.0 / len(target_set)

    for stock in target_set:
        _order_target_percent(context, stock, weight)
"""
