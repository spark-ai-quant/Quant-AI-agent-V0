STRATEGY_NAME = "alpaca_rotation"

PARAM_SCHEMA = {
    "total_stock_nums": {
        "type": "int",
        "default": 30,
        "description": "Total number of holdings",
    },
    "sell_stock_nums": {
        "type": "int",
        "default": 6,
        "description": "Number of worst holdings sold on each rebalance",
    },
    "rebalance_days": {
        "type": "int",
        "default": 22,
        "description": "Rebalance interval in trading days",
    },
    "random_seed": {
        "type": "int",
        "default": 42,
        "description": "Random seed",
    },
}


def generate(params):
    total_stock_nums = params.get("total_stock_nums", 30)
    sell_stock_nums = params.get("sell_stock_nums", 6)
    rebalance_days = params.get("rebalance_days", 22)
    random_seed = params.get("random_seed", 42)

    return f"""
from jqdata import *
import random
from datetime import timedelta


def _order_target_percent(context, security, percent):
    if "order_target_percent" in globals():
        return order_target_percent(security, percent)
    if "order_target_value" in globals():
        return order_target_value(security, context.portfolio.total_value * percent)
    if hasattr(context, "order_target_percent"):
        return context.order_target_percent(security, percent)
    if hasattr(context, "order_target_value"):
        return context.order_target_value(security, context.portfolio.total_value * percent)
    raise NameError("order_target_percent is not defined")


def _order_target_zero(context, security):
    return _order_target_percent(context, security, 0)


# =========================
# 股票池（增强版）
# =========================
def _candidate_stocks(context):
    securities = get_all_securities("stock", date=context.previous_date)

    if securities is None or securities.empty:
        return []

    current_data = get_current_data()
    today = context.current_dt.date()

    candidates = []

    for stock, row in securities.iterrows():

        data = current_data[stock]

        # 1️⃣ 停牌
        if data.paused:
            continue

        # 2️⃣ ST
        if data.is_st or "ST" in data.name or "*" in data.name:
            continue

        # 3️⃣ 次新股（<60天）
        listed_days = (today - row.start_date).days
        if listed_days < 60:
            continue

        # 4️⃣ 涨跌停过滤
        if data.high_limit == data.low_limit:
            continue
        if data.last_price >= data.high_limit * 0.99:
            continue
        if data.last_price <= data.low_limit * 1.01:
            continue

        candidates.append(stock)

    return candidates


def _current_holdings(context):
    return [
        stock
        for stock, position in context.portfolio.positions.items()
        if getattr(position, "total_amount", 0) > 0
    ]


# =========================
# 随机选股（可复现）
# =========================
def _random_pick(candidates, count, seed):
    if count <= 0 or not candidates:
        return []

    rng = random.Random(seed)
    count = min(count, len(candidates))
    return rng.sample(candidates, count)


# =========================
# 调仓执行（先卖后买）
# =========================
def _rebalance_to_targets(context, targets):

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
    set_benchmark("000300.XSHG")
    set_option("use_real_price", True)

    g.total_stock_nums = {total_stock_nums}
    g.sell_stock_nums = {sell_stock_nums}
    g.rebalance_days = {rebalance_days}
    g.random_seed = {random_seed}

    g.day_counter = 0

    run_daily(trade, time="09:35")


def trade(context):

    g.day_counter += 1

    candidates = _candidate_stocks(context)

    if len(candidates) < g.total_stock_nums:
        return

    holdings = _current_holdings(context)

    # =========================
    # 初始建仓
    # =========================
    if not holdings:
        initial_targets = _random_pick(
            candidates,
            g.total_stock_nums,
            g.random_seed + g.day_counter,
        )
        _rebalance_to_targets(context, initial_targets)
        return

    # =========================
    # 调仓日判断
    # =========================
    if g.day_counter % g.rebalance_days != 0:
        return

    # =========================
    # 计算收益（无未来函数）
    # =========================
    scored_holdings = []

    for stock in holdings:
        position = context.portfolio.positions.get(stock)

        avg_cost = getattr(position, "avg_cost", 0)
        current_price = getattr(position, "price", 0)

        if avg_cost > 0:
            return_pct = (current_price - avg_cost) / avg_cost
        else:
            return_pct = 0

        scored_holdings.append((stock, return_pct))

    # 按收益排序（卖最差）
    scored_holdings.sort(key=lambda x: x[1])

    sell_num = min(g.sell_stock_nums, len(scored_holdings))
    sell_list = [stock for stock, _ in scored_holdings[:sell_num]]

    kept = [stock for stock in holdings if stock not in sell_list]

    # =========================
    # 补充新股票
    # =========================
    available = [s for s in candidates if s not in kept]

    buy_needed = g.total_stock_nums - len(kept)
    buy_num = min(buy_needed, len(available))

    buy_list = _random_pick(
        available,
        buy_num,
        g.random_seed + g.day_counter,
    )

    targets = kept + buy_list

    _rebalance_to_targets(context, targets)
"""