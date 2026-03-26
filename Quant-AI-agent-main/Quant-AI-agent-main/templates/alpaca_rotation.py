STRATEGY_NAME = "alpaca_rotation"

PARAM_SCHEMA = {
    "total_stock_nums": {"type": "int", "default": 30},
    "sell_stock_nums": {"type": "int", "default": 6},
    "rebalance_days": {"type": "int", "default": 22},
    "random_seed": {"type": "int", "default": 42},
    "stock_pool_type": {"type": "str", "default": "all"},
    "stock_list": {"type": "list", "default": []},
}


def generate(params):
    total_stock_nums = params.get("total_stock_nums", 30)
    sell_stock_nums = params.get("sell_stock_nums", 6)
    rebalance_days = params.get("rebalance_days", 22)
    random_seed = params.get("random_seed", 42)
    stock_pool_type = params.get("stock_pool_type", "all")
    stock_list = params.get("stock_list", [])

    return f"""
from jqdata import *
import random
from templates.common import get_stock_pool


def _order_target_percent(context, security, percent):
    return order_target_percent(security, percent)

def _order_target_zero(context, security):
    return order_target(security, 0)


def _current_holdings(context):
    return [s for s in context.portfolio.positions.keys()]


def _random_pick(candidates, count, seed):
    rng = random.Random(seed)
    return rng.sample(candidates, min(count, len(candidates)))


def _rebalance(context, targets):
    current = list(context.portfolio.positions.keys())

    for s in current:
        if s not in targets:
            _order_target_zero(context, s)

    if not targets:
        return

    weight = 1.0 / len(targets)
    for s in targets:
        _order_target_percent(context, s, weight)


def initialize(context):
    set_option("use_real_price", True)
    g.total = {total_stock_nums}
    g.sell = {sell_stock_nums}
    g.days = {rebalance_days}
    g.seed = {random_seed}
    g.counter = 0
    run_daily(trade, time="09:35")


def trade(context):
    g.counter += 1

    stocks = get_stock_pool(context, "{stock_pool_type}", {stock_list})

    if len(stocks) < g.total:
        return

    holdings = _current_holdings(context)

    if not holdings:
        targets = _random_pick(stocks, g.total, g.seed)
        _rebalance(context, targets)
        return

    if g.counter % g.days != 0:
        return

    scored = []
    for s in holdings:
        pos = context.portfolio.positions[s]
        ret = (pos.price - pos.avg_cost) / pos.avg_cost if pos.avg_cost > 0 else 0
        scored.append((s, ret))

    scored.sort(key=lambda x: x[1])
    sell_list = [s for s, _ in scored[:g.sell]]

    keep = [s for s in holdings if s not in sell_list]
    pool = [s for s in stocks if s not in keep]

    buy = _random_pick(pool, g.total - len(keep), g.seed + g.counter)

    _rebalance(context, keep + buy)
"""
