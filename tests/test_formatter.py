import unittest

from globfmt.formatter import GlobSyntaxError, normalize_pattern


class PassthroughTests(unittest.TestCase):
    def test_blank_line(self):
        self.assertEqual(normalize_pattern(""), "")

    def test_comment_line(self):
        self.assertEqual(normalize_pattern("# not a pattern"), "# not a pattern")

    def test_indented_comment_line(self):
        self.assertEqual(normalize_pattern("  # still a comment"), "  # still a comment")

    def test_trailing_newline_stripped(self):
        self.assertEqual(normalize_pattern("*.py\n"), "*.py")

    def test_already_clean_pattern_unchanged(self):
        self.assertEqual(normalize_pattern("src/**/*.py"), "src/**/*.py")

    def test_brace_alternation_unchanged(self):
        self.assertEqual(normalize_pattern("*.{ts,tsx}"), "*.{ts,tsx}")


class WhitespaceTests(unittest.TestCase):
    def test_strict_rejects_leading_whitespace(self):
        with self.assertRaises(GlobSyntaxError):
            normalize_pattern(" *.py")

    def test_strict_rejects_trailing_whitespace(self):
        with self.assertRaises(GlobSyntaxError):
            normalize_pattern("*.py ")

    def test_lenient_strips_whitespace(self):
        self.assertEqual(normalize_pattern("  *.py  ", lenient=True), "*.py")


class BackslashTests(unittest.TestCase):
    def test_escaped_metacharacter_preserved(self):
        self.assertEqual(normalize_pattern(r"foo\*bar"), r"foo\*bar")

    def test_escaped_backslash_preserved(self):
        self.assertEqual(normalize_pattern(r"foo\\bar"), r"foo\\bar")

    def test_strict_rejects_dangling_backslash(self):
        with self.assertRaises(GlobSyntaxError):
            normalize_pattern("foo\\")

    def test_lenient_drops_dangling_backslash(self):
        self.assertEqual(normalize_pattern("foo\\", lenient=True), "foo")

    def test_strict_rejects_windows_path_separator(self):
        with self.assertRaises(GlobSyntaxError):
            normalize_pattern(r"build\output\*.log")

    def test_lenient_repairs_windows_path_separator(self):
        # The first backslash (before 'o') isn't an escape candidate, so it
        # becomes '/'. The second (before '*') *is* a valid escape lookahead,
        # so the heuristic keeps it as a literal-asterisk escape rather than
        # guessing it was also meant as a separator.
        self.assertEqual(
            normalize_pattern(r"build\output\*.log", lenient=True),
            "build/output\\*.log",
        )


class PathSeparatorTests(unittest.TestCase):
    def test_strict_rejects_leading_dot_slash(self):
        with self.assertRaises(GlobSyntaxError):
            normalize_pattern("./src/*.py")

    def test_lenient_strips_leading_dot_slash(self):
        self.assertEqual(normalize_pattern("./src/*.py", lenient=True), "src/*.py")

    def test_strict_rejects_doubled_slash(self):
        with self.assertRaises(GlobSyntaxError):
            normalize_pattern("src//utils/*.js")

    def test_lenient_collapses_doubled_slash(self):
        self.assertEqual(normalize_pattern("src//utils/*.js", lenient=True), "src/utils/*.js")

    def test_lenient_collapses_multiple_doubled_slashes(self):
        self.assertEqual(normalize_pattern("a//b///c", lenient=True), "a/b/c")


class BracketTests(unittest.TestCase):
    def test_valid_character_class_unchanged(self):
        self.assertEqual(normalize_pattern("src/[Tt]est*.py"), "src/[Tt]est*.py")

    def test_valid_negated_character_class_unchanged(self):
        self.assertEqual(normalize_pattern("src/[!Tt]est*.py"), "src/[!Tt]est*.py")

    def test_valid_caret_negated_character_class_unchanged(self):
        self.assertEqual(normalize_pattern("src/[^Tt]est*.py"), "src/[^Tt]est*.py")

    def test_literal_closing_bracket_as_first_char(self):
        # ']' immediately after '[' is a literal member, not a closer.
        self.assertEqual(normalize_pattern("[]ab]"), "[]ab]")

    def test_literal_closing_bracket_after_negation(self):
        self.assertEqual(normalize_pattern("[!]ab]"), "[!]ab]")

    def test_strict_rejects_unterminated_bracket(self):
        with self.assertRaises(GlobSyntaxError):
            normalize_pattern("src/[Ttest*.py")

    def test_lenient_escapes_unterminated_bracket(self):
        self.assertEqual(
            normalize_pattern("src/[Ttest*.py", lenient=True),
            r"src/\[Ttest*.py",
        )

    def test_lone_closing_bracket_is_harmless(self):
        self.assertEqual(normalize_pattern("foo]bar"), "foo]bar")


class BraceTests(unittest.TestCase):
    def test_strict_rejects_nested_braces(self):
        with self.assertRaises(GlobSyntaxError):
            normalize_pattern("*.{a,{b,c}}")

    def test_lenient_escapes_nested_brace(self):
        self.assertEqual(normalize_pattern("*.{a,{b,c}}", lenient=True), r"*.{a,\{b,c}}")

    def test_strict_rejects_unterminated_brace(self):
        with self.assertRaises(GlobSyntaxError):
            normalize_pattern("*.{ts,tsx")

    def test_lenient_escapes_unterminated_brace(self):
        self.assertEqual(normalize_pattern("*.{ts,tsx", lenient=True), r"*.\{ts,tsx")

    def test_escaped_brace_not_flagged(self):
        self.assertEqual(normalize_pattern(r"literal\{brace"), r"literal\{brace")


class ErrorDetailTests(unittest.TestCase):
    def test_error_carries_original_pattern(self):
        try:
            normalize_pattern("./src/*.py")
        except GlobSyntaxError as exc:
            self.assertEqual(exc.pattern, "./src/*.py")
        else:
            self.fail("expected GlobSyntaxError")

    def test_error_carries_position_when_known(self):
        try:
            normalize_pattern(r"build\output\*.log")
        except GlobSyntaxError as exc:
            self.assertEqual(exc.position, 5)
        else:
            self.fail("expected GlobSyntaxError")

    def test_error_message_includes_pattern_repr(self):
        try:
            normalize_pattern("src//utils/*.js")
        except GlobSyntaxError as exc:
            self.assertIn(repr("src//utils/*.js"), str(exc))
        else:
            self.fail("expected GlobSyntaxError")


if __name__ == "__main__":
    unittest.main()
