import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from text_tokens import validate, signature


class TokenTests(unittest.TestCase):
    def test_preserves_every_observed_control_form(self):
        validate('Press [b=RDUp] %1\\n[c=DARK_RED]{s}[c=RESET]\x1e\x1f\xa0',
                 '按 [b=RDUp] %1\\n[c=DARK_RED]{s}[c=RESET]\x1e\x1f\xa0')

    def test_real_newline_is_not_literal_escape(self):
        with self.assertRaises(ValueError):
            validate('Line\\nNext', '第一行\n下一行')
        with self.assertRaises(ValueError):
            validate('Line\r\nNext', '第一行\n下一行')

    def test_reordered_or_changed_tokens_rejected(self):
        for translation in ['%2 %1', '%1 %1', '%1', '%１ %2']:
            with self.assertRaises(ValueError):
                validate('%1 %2', translation)
        with self.assertRaises(ValueError):
            validate('[b=Lstick]', '[b=LStick]')

    def test_line_movement_rejected(self):
        with self.assertRaises(ValueError):
            validate('%1\\nText', '文本\\n%1')

    def test_repeated_breaks_and_literal_percent(self):
        validate('50%\\n\\nYes', '50%\\n\\n是')
        with self.assertRaises(ValueError):
            validate('50%\\n\\nYes', '50％\\n是')

    def test_printf_and_terminator(self):
        self.assertEqual(signature('%1 %2 %03d %.2f %%'), ['%1', '%2', '%03d', '%.2f', '%%'])
        with self.assertRaises(ValueError):
            validate('Text', '文本\0')


if __name__ == '__main__':
    unittest.main()
