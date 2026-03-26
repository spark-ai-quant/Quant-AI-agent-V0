import importlib
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def load_strategy_map():
    strategy_map = {}

    for template_path in TEMPLATE_DIR.glob("*.py"):
        if template_path.name.startswith("__"):
            continue

        module_name = template_path.stem
        module = importlib.import_module(f"templates.{module_name}")

        if hasattr(module, "generate"):
            strategy_map[module_name] = module.generate

    return strategy_map


STRATEGY_MAP = load_strategy_map()


def generate_strategy_code(params):
    strategy_type = params.get("strategy_type")
    if strategy_type not in STRATEGY_MAP:
        raise ValueError(f"Unknown strategy type: {strategy_type}")

    return STRATEGY_MAP[strategy_type](params)
