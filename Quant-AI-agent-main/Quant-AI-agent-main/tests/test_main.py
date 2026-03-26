from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from main import generate_and_save_strategy


class MainTests(TestCase):
    def test_generate_and_save_strategy_writes_output(self):
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "generated_strategy.py"

            with patch("main.parse_strategy", return_value={"strategy_type": "momentum"}):
                with patch("main.generate_strategy_code", return_value="print('ok')"):
                    code = generate_and_save_strategy(
                        "最近20天涨幅最高的10只股票",
                        api_key="test-key",
                        output_path=output_path,
                    )

            self.assertEqual(code, "print('ok')")
            self.assertEqual(output_path.read_text(encoding="utf-8"), "print('ok')")

    def test_generate_and_save_strategy_rejects_empty_text(self):
        with self.assertRaises(ValueError):
            generate_and_save_strategy("   ", api_key="test-key")
