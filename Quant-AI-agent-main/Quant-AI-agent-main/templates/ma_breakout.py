STRATEGY_NAME = "ma_breakout"

PARAM_SCHEMA = {
    "ma_period": {
        "type": "int",
        "default": 5,
        "description": "均线周期"
    },
    "threshold": {
        "type": "float",
        "default": 1.01,
        "description": "突破阈值（如1.01表示上涨1%）"
    },
    "stock_code": {
        "type": "str",
        "default": "000001.XSHE",
        "description": "交易标的"
    }
}


def generate(params):
    ma = params.get("ma_period", 5)
    threshold = params.get("threshold", 1.01)
    stock = params.get("stock_code", "000001.XSHE")

    return f"""
from jqdata import *
import numpy as np


# =========================
# 统一下单接口
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
    set_option("use_real_price", True)

    g.stock = "{stock}"
    g.ma_period = {ma}
    g.threshold = {threshold}

    run_daily(trade, time='09:35')


# =========================
# 交易逻辑
# =========================
def trade(context):
    current_data = get_current_data()

    # 基本过滤（防踩坑🔥）
    if g.stock not in current_data:
        return

    if current_data[g.stock].paused:
        return

    if current_data[g.stock].is_st:
        return

    # =========================
    # 获取历史数据（无未来函数）
    # =========================
    df = attribute_history(
        g.stock,
        g.ma_period + 1,   # 多取一天用于确认趋势
        "1d",
        ["close"],
        skip_paused=True
    )

    if df is None or len(df) < g.ma_period:
        return

    # =========================
    # 计算均线
    # =========================
    ma = df['close'][-g.ma_period:].mean()

    # 当前价格（用最新收盘更稳）
    price = df['close'][-1]

    if price is None or price <= 0:
        return

    # 当前持仓
    position = context.portfolio.positions.get(g.stock, None)
    holding = position.total_amount if position else 0

    # =========================
    # 突破逻辑（优化版🔥）
    # =========================
    breakout = price > ma * g.threshold
    breakdown = price < ma

    # =========================
    # 买入逻辑
    # =========================
    if breakout and holding == 0:
        log.info(f"BUY {g.stock} price={price:.2f}, MA={ma:.2f}")
        _order_target_percent(context, g.stock, 1.0)

    # =========================
    # 卖出逻辑
    # =========================
    elif breakdown and holding > 0:
        log.info(f"SELL {g.stock} price={price:.2f}, MA={ma:.2f}")
        _order_target_zero(context, g.stock)
"""
