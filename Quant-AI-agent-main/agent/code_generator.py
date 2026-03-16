from templates.joinquant_template import generate_template

def generate_strategy_code(params):

    lookback = params["lookback"]
    stock_num = params["stock_num"]

    code = generate_template(lookback, stock_num)

    return code