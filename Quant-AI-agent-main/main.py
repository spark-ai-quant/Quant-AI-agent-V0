from agent.strategy_parser import parse_strategy
from agent.code_generator import generate_strategy_code

text = input("请输入你的策略描述: ")

params = parse_strategy(text)

print("\n解析参数:")
print(params)

code = generate_strategy_code(params)

# 保存策略文件
file_name = "generated_strategy.py"

with open(file_name, "w", encoding="utf-8") as f:
    f.write(code)

print(f"\n策略代码已生成: {file_name}")