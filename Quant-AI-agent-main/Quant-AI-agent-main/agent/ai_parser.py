import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SYSTEM_PROMPT = """
You convert Chinese or English trading-strategy requests into JSON.
Return JSON only. Do not add markdown, commentary, or code fences.

========================
UNIFIED RULES (VERY IMPORTANT)
========================

1. ALWAYS include:
- strategy_type

2. Stock selection MUST use unified format:
- stock_pool_type: "all" / "hs300" / "zz500" / "custom"
- stock_list: []  (only used when custom)

3. If user mentions:
- "沪深300" → stock_pool_type="hs300"
- "中证500" → stock_pool_type="zz500"
- "全部股票 / 全市场" → stock_pool_type="all"
- specific stocks → stock_pool_type="custom" + stock_list

4. NEVER output stock_code anymore (deprecated)

========================
SUPPORTED STRATEGIES
========================

1. momentum
- lookback_days: int
- stock_count: int

2. ma_breakout
- ma_period: int
- threshold: float

3. kdj_timing
- k_period: int
- buy_threshold: int
- sell_threshold: int
- max_hold: int

4. alpaca_rotation
- total_stock_nums: int
- sell_stock_nums: int
- rebalance_days: int
- random_seed: int

5. brandes_value
- hold_count: int
- rebalance_period_days: int

========================
DEFAULT VALUES
========================

If not specified:

kdj_timing:
- k_period = 9
- buy_threshold = 20
- sell_threshold = 80
- max_hold = 10
- stock_pool_type = "all"

alpaca_rotation:
- total_stock_nums = 30
- sell_stock_nums = 6
- rebalance_days = 22
- random_seed = 42

brandes_value:
- hold_count = 30
- rebalance_period_days = 1

momentum:
- lookback_days = 60
- stock_count = 20

ma_breakout:
- ma_period = 5
- threshold = 1.01

========================
EXAMPLES
========================

Input: 做一个沪深300的KDJ策略，最多持有10只股票
Output:
{"strategy_type":"kdj_timing","stock_pool_type":"hs300","stock_list":[],"max_hold":10,"k_period":9,"buy_threshold":20,"sell_threshold":80}

Input: 用KDJ做全市场选股
Output:
{"strategy_type":"kdj_timing","stock_pool_type":"all","stock_list":[],"k_period":9,"buy_threshold":20,"sell_threshold":80,"max_hold":10}

Input: 用KDJ分析平安银行和茅台
Output:
{"strategy_type":"kdj_timing","stock_pool_type":"custom","stock_list":["000001.XSHE","600519.XSHG"],"k_period":9,"buy_threshold":20,"sell_threshold":80,"max_hold":2}

Input: 做一个羊驼策略，沪深300，持有30只
Output:
{"strategy_type":"alpaca_rotation","stock_pool_type":"hs300","stock_list":[],"total_stock_nums":30,"sell_stock_nums":6,"rebalance_days":22,"random_seed":42}

Input: 做一个价值策略，全市场选股，持仓30只
Output:
{"strategy_type":"brandes_value","stock_pool_type":"all","stock_list":[],"hold_count":30,"rebalance_period_days":1}
"""


def _build_client(api_key=None):
    resolved_api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    if not resolved_api_key:
        raise ValueError("Missing DeepSeek API key.")

    return OpenAI(
        api_key=resolved_api_key,
        base_url="https://api.deepseek.com",
    )


def _extract_json_object(content):
    stripped = (content or "").strip()
    if not stripped:
        raise ValueError("Empty response from model.")

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Model did not return JSON.")

    return json.loads(stripped[start : end + 1])


def parse_strategy(text, api_key=None):
    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("Strategy description cannot be empty.")

    client = _build_client(api_key=api_key)
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": normalized_text},
        ],
        temperature=0,
    )

    content = response.choices[0].message.content if response.choices else ""
    return _extract_json_object(content)
