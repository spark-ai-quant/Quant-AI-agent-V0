from pathlib import Path

from agent.ai_parser import parse_strategy
from agent.code_generator import generate_strategy_code

DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent / "generated_strategy.py"


def generate_and_save_strategy(text, api_key=None, output_path=None):
    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("请输入策略描述。")

    target_path = Path(output_path) if output_path else DEFAULT_OUTPUT_PATH
    if not target_path.is_absolute():
        target_path = Path(__file__).resolve().parent / target_path

    params = parse_strategy(normalized_text, api_key=api_key)
    code = generate_strategy_code(params)
    target_path.write_text(code, encoding="utf-8")
    return code


def main():
    text = input("请输入策略描述：").strip()
    generate_and_save_strategy(text)
    print("\n策略已生成: generated_strategy.py")


if __name__ == "__main__":
    main()
