from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from agent.ai_parser import _extract_json_object, parse_strategy


class AiParserTests(TestCase):
    def test_extract_json_object_from_wrapped_response(self):
        content = 'result:\n{"strategy_type": "momentum", "lookback_days": 20, "stock_count": 10}\nend'
        parsed = _extract_json_object(content)

        self.assertEqual(parsed["strategy_type"], "momentum")
        self.assertEqual(parsed["lookback_days"], 20)
        self.assertEqual(parsed["stock_count"], 10)

    def test_parse_strategy_uses_client_response(self):
        fake_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"strategy_type": "kdj_timing", "stock_code": "000001.XSHE", "k_period": 9, "buy_threshold": 20, "sell_threshold": 80}'
                    )
                )
            ]
        )
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **_: fake_response)
            )
        )

        with patch("agent.ai_parser._build_client", return_value=fake_client) as build_client:
            parsed = parse_strategy("我要做一份十只股票的 kdj 策略", api_key="test-key")

        build_client.assert_called_once_with(api_key="test-key")
        self.assertEqual(parsed["strategy_type"], "kdj_timing")
        self.assertEqual(parsed["stock_code"], "000001.XSHE")
