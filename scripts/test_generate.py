"""Tests for scripts/generate.py malformed-source handling (issue #3).

Run: python3 -m unittest discover -s scripts -p 'test_*.py'
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "generate.py"

VALID_SKILL = """---
name: good-skill
description: A well-formed fixture skill.
---
# Good skill

Body text.
"""

NO_FRONTMATTER = "# Broken skill\n\nNo frontmatter block at all.\n"

MISSING_NAME = """---
description: Frontmatter without a name key.
---
Body.
"""


class MalformedSourceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.skills = self.root / "skills"
        self.out = self.root / "site"
        self.skills.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def add_skill(self, dirname, text):
        d = self.skills / dirname
        d.mkdir()
        (d / "SKILL.md").write_text(text)
        return d / "SKILL.md"

    def run_generator(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--skills-dir", str(self.skills), "--out", str(self.out)],
            capture_output=True,
            text=True,
        )

    def test_single_malformed_source_fails_with_path_and_error(self):
        bad = self.add_skill("broken-skill", NO_FRONTMATTER)
        self.add_skill("good-skill", VALID_SKILL)

        result = self.run_generator()
        output = result.stdout + result.stderr

        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn(f"{bad}: ValueError: {bad} has no frontmatter", output)

    def test_all_malformed_sources_are_reported_before_exit(self):
        bad_a = self.add_skill("broken-a", NO_FRONTMATTER)
        bad_b = self.add_skill("broken-b", MISSING_NAME)
        self.add_skill("good-skill", VALID_SKILL)

        result = self.run_generator()
        output = result.stdout + result.stderr

        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn(f"{bad_a}: ValueError: {bad_a} has no frontmatter", output)
        self.assertIn(f"{bad_b}: KeyError: 'name'", output)

    def test_failed_run_does_not_create_index_or_partial_pages(self):
        self.add_skill("broken-skill", NO_FRONTMATTER)
        self.add_skill("good-skill", VALID_SKILL)

        result = self.run_generator()

        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.out / "index.html").exists())
        self.assertFalse((self.out / "good-skill").exists())

    def test_failed_run_leaves_existing_site_untouched(self):
        self.out.mkdir(parents=True)
        sentinel = self.out / "sentinel.txt"
        sentinel.write_text("keep me")
        index = self.out / "index.html"
        index.write_text("previous good index")
        self.add_skill("broken-skill", NO_FRONTMATTER)
        self.add_skill("good-skill", VALID_SKILL)

        result = self.run_generator()

        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(sentinel.read_text(), "keep me")
        self.assertEqual(index.read_text(), "previous good index")
        self.assertFalse((self.out / "good-skill").exists())

    def test_all_valid_sources_exit_zero(self):
        self.add_skill("good-skill", VALID_SKILL)

        result = self.run_generator()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.out / "good-skill" / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
