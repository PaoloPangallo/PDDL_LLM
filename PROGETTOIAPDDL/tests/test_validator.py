"""Fast Downward wrapper checks using a fake driver; no external planner needed."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.validator import find_fast_downward, validate_pddl, generate_plan_with_fd

FAKE_DRIVER = """from pathlib import Path
import sys

args = sys.argv[1:]
domain = next((Path(a) for a in args if a.endswith('domain.pddl')), None)
if domain and 'INVALID' in domain.read_text(encoding='utf-8'):
    print('Translator rejected PDDL')
    sys.exit(12)
if '--translate' in args:
    Path('output.sas').write_text('SAS artifact', encoding='utf-8')
    print('Translation succeeded')
    sys.exit(0)
if '--plan-file' in args:
    plan_file = Path(args[args.index('--plan-file') + 1])
    plan_file.write_text('(walk a b)\\n', encoding='utf-8')
    print('Solution found.')
    sys.exit(0)
sys.exit(5)
"""


class FastDownwardTests(unittest.TestCase):
    def test_missing_driver_fails_cleanly(self):
        with patch.dict(os.environ, {"FAST_DOWNWARD_PATH": "/does/not/exist.py"}):
            result = validate_pddl("(define (domain x))", "(define (problem x))")
            self.assertFalse(result["valid_syntax"])
            self.assertEqual(result["translate_exit_code"], 127)
            plan = generate_plan_with_fd("(define (domain x))", "(define (problem x))")
            self.assertFalse(plan["found_plan"])

    def test_translation_and_plan_uses_isolated_cwd(self):
        with tempfile.TemporaryDirectory() as d:
            driver = Path(d) / "fake-downward.py"
            driver.write_text(FAKE_DRIVER, encoding="utf-8")
            with patch.dict(os.environ, {"FAST_DOWNWARD_PATH": str(driver)}):
                self.assertEqual(find_fast_downward(), str(driver.resolve()))
                ok = validate_pddl("(define (domain x))", "(define (problem x))")
                self.assertTrue(ok["valid_syntax"])
                self.assertEqual(ok["translate_exit_code"], 0)
                bad = validate_pddl("INVALID", "(define (problem x))")
                self.assertFalse(bad["valid_syntax"])
                self.assertEqual(bad["translate_exit_code"], 12)
                plan = generate_plan_with_fd("(define (domain x))", "(define (problem x))")
                self.assertTrue(plan["found_plan"])
                self.assertIn("(walk a b)", plan["plan"])
            self.assertFalse((Path.cwd() / "output.sas").exists())
            self.assertFalse((Path.cwd() / "plan.txt").exists())


if __name__ == "__main__":
    unittest.main()
