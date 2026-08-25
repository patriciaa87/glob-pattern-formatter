"""Core normalization logic for glob patterns.

The dialect assumed here is the informal one shared by most glob-consuming
tools (npm's "files" field, .prettierignore, ripgrep-style ignore files,
webpack loaders): '*', '?' and '[...]' character classes, '**' for
recursive matches, '{a,b}' brace alternation, and '\\' as an escape
character for any of those metacharacters. It is not tied to Python's own
glob module, which doesn't understand braces at all.

A pattern is ambiguous whenever a human and a naive matcher could
reasonably disagree about what it means - a backslash that might be an
escape or might be a stray Windows path separator, a bracket class that
was never closed. normalize_pattern() refuses those by default rather
than guessing, because a glob that silently matches the wrong thing (or
nothing) is worse than a formatter that stops and asks.
"""

from __future__ import annotations

ESCAPABLE = set("*?[]{}!\\")


class GlobSyntaxError(ValueError):
    """Raised in strict mode when a pattern can't be normalized safely."""

    def __init__(self, message: str, *, pattern: str, position: int | None = None):
        self.pattern = pattern
        self.position = position
        located = f" (position {position})" if position is not None else ""
        super().__init__(f"{message}{located}: {pattern!r}")


def normalize_pattern(pattern: str, *, lenient: bool = False) -> str:
    """Return a normalized form of a single glob pattern line.

    In strict mode (the default) any ambiguity raises GlobSyntaxError
    instead of guessing. --lenient trades that safety for best-effort
    repair.
    """
    original = pattern
    text = pattern.rstrip("\r\n")

    if text.strip() == "" or text.lstrip().startswith("#"):
        return text.rstrip()

    stripped = text.strip()
    if stripped != text:
        if not lenient:
            raise GlobSyntaxError("leading or trailing whitespace", pattern=original)
        text = stripped

    text = _normalize_backslashes(text, lenient=lenient, original=original)
    text = _normalize_path_separators(text, lenient=lenient, original=original)
    text = _normalize_brackets_and_braces(text, lenient=lenient, original=original)
    return text


def _normalize_backslashes(text: str, *, lenient: bool, original: str) -> str:
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        if i + 1 >= n:
            if not lenient:
                raise GlobSyntaxError(
                    "dangling escape character at end of pattern", pattern=original
                )
            i += 1
            continue
        nxt = text[i + 1]
        if nxt in ESCAPABLE:
            out.append(ch)
            out.append(nxt)
            i += 2
            continue
        if not lenient:
            raise GlobSyntaxError(
                f"backslash not followed by a glob metacharacter ({nxt!r}); "
                "use '/' for path separators",
                pattern=original,
                position=i,
            )
        out.append("/")
        i += 1
    return "".join(out)


def _normalize_path_separators(text: str, *, lenient: bool, original: str) -> str:
    if text.startswith("./"):
        if not lenient:
            raise GlobSyntaxError("redundant leading './'", pattern=original)
        text = text[2:]

    if "//" in text:
        if not lenient:
            raise GlobSyntaxError("empty path segment ('//')", pattern=original)
        while "//" in text:
            text = text.replace("//", "/")

    return text


def _normalize_brackets_and_braces(text: str, *, lenient: bool, original: str) -> str:
    """Validate bracket classes and brace groups; escape stray ones in lenient mode.

    A lone '[' with no closing ']' is treated literally by most matchers,
    which almost never matches what the author intended, so it's flagged.
    A lone ']' with no opening '[' is genuinely harmless (shells treat it
    as a literal character) and is left alone.
    """
    n = len(text)
    problem_positions: list[int] = []
    i = 0
    in_bracket = False
    bracket_start = -1
    in_brace = False
    brace_start = -1

    while i < n:
        ch = text[i]
        if ch == "\\" and i + 1 < n:
            i += 2
            continue

        if in_bracket:
            is_literal_close = i == bracket_start + 1 or (
                i == bracket_start + 2 and text[bracket_start + 1] in "!^"
            )
            if ch == "]" and not is_literal_close:
                in_bracket = False
            i += 1
            continue

        if ch == "[":
            in_bracket = True
            bracket_start = i
            i += 1
            continue

        if ch == "{":
            if in_brace:
                if not lenient:
                    raise GlobSyntaxError(
                        "nested brace groups are not supported",
                        pattern=original,
                        position=i,
                    )
                problem_positions.append(i)
            else:
                in_brace = True
                brace_start = i
            i += 1
            continue

        if ch == "}":
            in_brace = False
            i += 1
            continue

        i += 1

    if in_bracket:
        if not lenient:
            raise GlobSyntaxError(
                "unterminated character class '['",
                pattern=original,
                position=bracket_start,
            )
        problem_positions.append(bracket_start)

    if in_brace:
        if not lenient:
            raise GlobSyntaxError(
                "unterminated brace group '{'", pattern=original, position=brace_start
            )
        problem_positions.append(brace_start)

    if not problem_positions:
        return text

    chars = list(text)
    for pos in problem_positions:
        chars[pos] = "\\" + chars[pos]
    return "".join(chars)
