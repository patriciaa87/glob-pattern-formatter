"""Command-line entry point for globfmt."""

from __future__ import annotations

import argparse
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

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
