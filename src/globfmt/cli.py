"""Command-line entry point for globfmt."""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from .formatter import GlobSyntaxError, normalize_pattern


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="globfmt",
        description="Normalize a list of glob patterns, one per line.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="pattern files to read, one glob per line (reads stdin if omitted)",
    )
    parser.add_argument(
        "--lenient",
        action="store_true",
        help="best-effort repair ambiguous patterns instead of rejecting them",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit with status 1 if any pattern is not already normalized, "
        "without printing normalized output",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="print a unified diff of the changes normalization would make, "
        "without printing normalized output",
    )
    return parser


def _numbered_lines(paths: list[str]):
    if not paths or paths == ["-"]:
        for number, line in enumerate(sys.stdin, start=1):
            yield "<stdin>", number, line.rstrip("\n")
        return
    for path in paths:
        text = Path(path).read_text()
        for number, line in enumerate(text.splitlines(), start=1):
            yield path, number, line


def _grouped_lines(paths: list[str]):
    """Yield (source, lines) per file so --diff can produce one diff per source."""
    if not paths or paths == ["-"]:
        yield "<stdin>", [line.rstrip("\n") for line in sys.stdin]
        return
    for path in paths:
        yield path, Path(path).read_text().splitlines()


def _run_check(args: argparse.Namespace) -> int:
    had_errors = False
    needs_formatting = False
    for source, lines in _grouped_lines(args.paths):
        normalized_lines = []
        for line_number, source_line in enumerate(lines, start=1):
            try:
                normalized_lines.append(normalize_pattern(source_line, lenient=args.lenient))
            except GlobSyntaxError as exc:
                print(f"{source}:{line_number}: {exc}", file=sys.stderr)
                had_errors = True
                # Keep the original line so the diff below stays aligned.
                normalized_lines.append(source_line)

        if normalized_lines != lines:
            needs_formatting = True
            if args.diff:
                diff = difflib.unified_diff(
                    lines, normalized_lines, fromfile=source, tofile=source, lineterm=""
                )
                sys.stdout.writelines(line + "\n" for line in diff)

    if had_errors:
        print(
            "pattern(s) rejected; rerun with --lenient to auto-repair them",
            file=sys.stderr,
        )
        return 1
    if needs_formatting:
        if not args.diff:
            print("patterns are not normalized; rerun without --check to see them", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.check or args.diff:
        return _run_check(args)

    errors = []
    normalized = []
    for source, line_number, source_line in _numbered_lines(args.paths):
        try:
            normalized.append(normalize_pattern(source_line, lenient=args.lenient))
        except GlobSyntaxError as exc:
            errors.append(f"{source}:{line_number}: {exc}")

    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        print(
            f"{len(errors)} pattern(s) rejected; rerun with --lenient to auto-repair them",
            file=sys.stderr,
        )
        return 1

    for line in normalized:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
