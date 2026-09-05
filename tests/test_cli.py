import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from globfmt.cli import main


def _run(argv, stdin_text=""):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(stdin_text)):
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = main(argv)
    return status, stdout.getvalue(), stderr.getvalue()


class CheckModeTests(unittest.TestCase):
    def test_already_normalized_patterns_pass(self):
        status, out, err = _run(["--check"], stdin_text="src/**/*.py\n*.{ts,tsx}\n")
        self.assertEqual(status, 0)
        self.assertEqual(out, "")

    def test_lenient_repairable_patterns_fail_check(self):
        status, out, err = _run(["--check", "--lenient"], stdin_text="./src/*.py\n")
        self.assertEqual(status, 1)
        self.assertEqual(out, "")
        self.assertIn("not normalized", err)

    def test_strict_ambiguous_pattern_fails_check(self):
        status, out, err = _run(["--check"], stdin_text="./src/*.py\n")
        self.assertEqual(status, 1)
        self.assertIn("redundant leading", err)

    def test_check_does_not_print_normalized_patterns(self):
        status, out, err = _run(["--check", "--lenient"], stdin_text="./src/*.py\n")
        self.assertEqual(status, 1)
        self.assertNotIn("src/*.py", out)


class DiffModeTests(unittest.TestCase):
    def test_diff_shows_the_change(self):
        status, out, err = _run(["--diff", "--lenient"], stdin_text="./src/*.py\n")
        self.assertEqual(status, 1)
        self.assertIn("-./src/*.py", out)
        self.assertIn("+src/*.py", out)

    def test_diff_empty_when_already_normalized(self):
        status, out, err = _run(["--diff"], stdin_text="src/*.py\n")
        self.assertEqual(status, 0)
        self.assertEqual(out, "")

    def test_diff_uses_file_path_in_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            pattern_file = Path(tmp) / "patterns.txt"
            pattern_file.write_text("./src/*.py\n")
            status, out, err = _run(["--diff", "--lenient", str(pattern_file)])
        self.assertEqual(status, 1)
        self.assertIn(str(pattern_file), out)


if __name__ == "__main__":
    unittest.main()
