from jqdata import *
import datetime


def get_stock_pool(context, stock_pool_type="all", stock_list=None):
    """
    统一股票池入口
    """

    if stock_list is None:
        stock_list = []

    current_data = get_current_data()

    # =========================
    # 1️⃣ 获取原始股票池
    # =========================
    if stock_pool_type == "hs300":
        pool = get_index_stocks("000300.XSHG")

    elif stock_pool_type == "zz500":
        pool = get_index_stocks("000905.XSHG")

    elif stock_pool_type == "zz1000":
        pool = get_index_stocks("000852.XSHG")

    elif stock_pool_type == "custom":
        pool = stock_list

    else:
        securities = get_all_securities("stock", date=context.previous_date)
        pool = list(securities.index)

    # =========================
    # 2️⃣ 过滤逻辑（A股实盘标准）
    # =========================
    final_pool = []

    today = context.current_dt.date()

    securities_info = get_all_securities("stock", date=context.previous_date)

    for stock in pool:

        # 防御：部分股票可能不存在
        if stock not in current_data:
            continue

        data = current_data[stock]

        # 停牌
        if data.paused:
            continue

        # ST
        if data.is_st or "ST" in data.name or "*" in data.name:
            continue

        # 次新股（<60天）
        if stock in securities_info.index:
            listed_days = (today - securities_info.loc[stock].start_date).days
            if listed_days < 60:
                continue

        # 涨跌停（避免成交问题）
        if data.high_limit == data.low_limit:
            continue
        if data.last_price >= data.high_limit * 0.99:
            continue
        if data.last_price <= data.low_limit * 1.01:
            continue

        final_pool.append(stock)

    return final_pool
