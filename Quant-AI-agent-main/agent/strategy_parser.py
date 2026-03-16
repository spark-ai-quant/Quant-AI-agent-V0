import re

def parse_strategy(text):
    """
    从自然语言解析策略参数
    """

    lookback = re.search(r'(\d+)天', text)
    stock_num = re.search(r'(\d+)只', text)

    result = {
        "lookback": int(lookback.group(1)) if lookback else 20,
        "stock_num": int(stock_num.group(1)) if stock_num else 10
    }

    return result