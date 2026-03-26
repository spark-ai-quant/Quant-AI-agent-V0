from unittest import TestCase

from templates.alpaca_rotation import generate as generate_alpaca
from templates.brandes_value import generate as generate_brandes


class TemplatePlatformTests(TestCase):
    def test_alpaca_rotation_generates_joinquant_code(self):
        code = generate_alpaca({})
        self.assertIn("from jqdata import *", code)
        self.assertNotIn("from bigmodule import M", code)

    def test_brandes_value_generates_joinquant_code(self):
        code = generate_brandes({})
        self.assertIn("from jqdata import *", code)
        self.assertNotIn("from bigmodule import M", code)
