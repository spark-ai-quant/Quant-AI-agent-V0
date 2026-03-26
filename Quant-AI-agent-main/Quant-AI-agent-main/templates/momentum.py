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
    }
}


def generate(params):
    lookback = params.get("lookback_days", 20)
    stock_num = params.get("stock_count", 10)

    return f"""
from jqdata import *
import numpy as np

# =========================
# 安全下单函数（兼容不同环境）
# =========================
def _order_target_percent(context, security, percent):
    if "order_target_value" in globals():
        return order_target_value(security, context.portfolio.total_value * percent)
    if hasattr(context, "order_target_value"):
        return context.order_target_value(security, context.portfolio.total_value * percent)
    if "order_target_percent" in globals():
        return order_target_percent(security, percent)
    if hasattr(context, "order_target_percent"):
        return context.order_target_percent(security, percent)
    raise NameError("order_target_percent is not defined")


def _order_target_zero(context, security):
    if "order_target" in globals():
        return order_target(security, 0)
    if "order_target_value" in globals():
        return order_target_value(security, 0)
    if hasattr(context, "order_target"):
        return context.order_target(security, 0)
    if hasattr(context, "order_target_value"):
        return context.order_target_value(security, 0)
    raise NameError("order_target is not defined")


# =========================
# 初始化
# =========================
def initialize(context):
    set_option('avoid_future_data', True)  # 防未来函数
    g.lookback = {lookback}
    g.stock_num = {stock_num}
    run_daily(trade, time='09:35')


# =========================
# 股票池过滤
# =========================
def get_stock_pool(context):
    stocks = get_all_securities('stock').index.tolist()

    # 去除ST
    current_data = get_current_data()
    stocks = [s for s in stocks if not current_data[s].is_st]

    # 去除停牌
    stocks = [s for s in stocks if not current_data[s].paused]

    # 去除新股（上市不足60天）
    stocks = [
        s for s in stocks 
        if (context.current_dt.date() - get_security_info(s).start_date).days > 60
    ]

    return stocks


# =========================
# 动量计算（更稳健）
# =========================
def calc_momentum(stocks, lookback):
    df = get_price(
        stocks,
        count=lookback,
        fields=['close'],
        panel=False
    )

    # pivot 成矩阵
    price_df = df.pivot(index='time', columns='code', values='close')

    # 收益率 = 终值 / 初值 - 1
    returns = price_df.iloc[-1] / price_df.iloc[0] - 1

    # 去掉NaN
    returns = returns.dropna()

    return returns


# =========================
# 主交易逻辑
# =========================
def trade(context):
    stocks = get_stock_pool(context)

    if len(stocks) == 0:
        return

    returns = calc_momentum(stocks, g.lookback)

    if len(returns) == 0:
        return

    # 选动量最高的股票
    top = returns.sort_values(ascending=False).head(g.stock_num)

    # =========================
    # 先卖出不在池中的
    # =========================
    for stock in list(context.portfolio.positions.keys()):
        if stock not in top.index:
            _order_target_zero(context, stock)

    # =========================
    # 再买入目标股票
    # =========================
    weight = 1.0 / len(top)

    for stock in top.index:
        _order_target_percent(context, stock, weight)
"""