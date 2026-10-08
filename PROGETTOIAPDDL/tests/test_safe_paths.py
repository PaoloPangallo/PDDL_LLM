"""Stdlib regression tests that do not need Ollama, Fast Downward or SQLite."""
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.safe_paths import validate_thread_id, resolve_lore_file, retrieved_pddl_examples


class SafePathsTests(unittest.TestCase):
    def test_valid_thread_id(self):
        self.assertEqual(validate_thread_id("session-1_2026"), "session-1_2026")

    def test_invalid_thread_ids(self):
        for value in ("../memory", "../../app", "/tmp/session", "x/y", ".", "",
                      "..", "\\test", "name.sqlite", "a" * 65, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_thread_id(value)

    def test_lore_rejects_traversal_and_symlink(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            lore = root / "lore"
            lore.mkdir()
            (lore / "quest.json").write_text("{}", encoding="utf-8")
            self.assertEqual(resolve_lore_file("quest.json", lore), lore / "quest.json")
            for value in ("../quest.json", "sub/quest.json", "missing.json",
                          "quest.pddl", "/etc/passwd", "quest.json/../quest.json"):
                with self.subTest(value=value), self.assertRaises((ValueError, FileNotFoundError)):
                    resolve_lore_file(value, lore)
            (root / "external.json").write_text("{}", encoding="utf-8")
            (lore / "symlink.json").symlink_to(root / "external.json")
            with self.assertRaises(FileNotFoundError):
                resolve_lore_file("symlink.json", lore)

    def test_db_examples_are_not_discarded(self):
        hits = [{"domain": "(define (domain sample) (:action act))",
                 "problem": "(define (problem test))",
                 "similarity": 0.9}]
        result = retrieved_pddl_examples(hits)
        self.assertEqual(len(result), 1)
        self.assertIn("(:action act)", result[0])
        self.assertIn("(problem test)", result[0])
        self.assertEqual(retrieved_pddl_examples([{}, None, {"domain":"X"}]), [])


if __name__ == "__main__":
    unittest.main()
