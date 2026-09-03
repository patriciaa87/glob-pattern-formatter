# globfmt

Glob patterns accumulate mess. They get pasted between a `.gitignore`, a
`package.json` `files` array, and a webpack config; someone edits one on
Windows and leaves a backslash in it; a string-concatenation bug doubles
a slash; an editing pass leaves a single-item `{foo}` brace group behind.
Most things that consume globs (`fnmatch`, `pathlib`, ripgrep-style ignore
parsers) don't error on this - they just quietly match the wrong files,
or nothing at all. A broken glob doesn't announce itself.

globfmt reads a list of patterns, one per line, and normalizes each one.
Blank lines and `#` comments pass through untouched.

## Usage

```
$ cat patterns.txt
./src/**/*.py
build\output\*.log
src//utils/*.js
*.{ts,tsx}

$ python -m globfmt patterns.txt
error: patterns.txt:1: redundant leading './': './src/**/*.py'
error: patterns.txt:2: backslash not followed by a glob metacharacter ('o') (position 5); use '/' for path separators: 'build\\output\\*.log'
error: patterns.txt:3: empty path segment ('//'): 'src//utils/*.js'
3 pattern(s) rejected; rerun with --lenient to auto-repair them
```

By default globfmt is strict: anything ambiguous is rejected with a
message pointing at the pattern and the reason, rather than silently
guessed at. Pass `--lenient` to have it repair what it safely can:

```
$ python -m globfmt --lenient patterns.txt
src/**/*.py
build/output\*.log
src/utils/*.js
*.{ts,tsx}
```

Notice the second line only lost its first backslash. The one before `*`
matches the escape lookahead (`\*` is a valid escaped literal asterisk), so
lenient mode keeps it rather than assuming it was also meant as a path
separator - see "Why strict-by-default" below.

It also reads stdin:

```
$ echo 'src/[Ttest*.py' | python -m globfmt --lenient
src/\[Ttest*.py
```

That last example is deliberate: an unterminated `[...]` character class
almost never matches what the author meant, so lenient mode escapes the
stray bracket into a literal rather than trying to guess where the class
was supposed to end.

## Why strict-by-default

A backslash in a glob is genuinely ambiguous - it might be escaping the
next character (`\*` meaning a literal asterisk) or it might be a stray
Windows path separator that should have been a `/`. globfmt resolves that
by metacharacter lookahead (`\*`, `\?`, `\[` etc. are treated as escapes;
anything else is treated as a separator), but that's a heuristic, not a
certainty. Strict mode exists so patterns that depend on the heuristic
have to be reviewed and opted into `--lenient` deliberately, instead of
being silently rewritten in a way the author didn't intend.

## Pattern dialect

- `*`, `?`, `[...]` character classes (with `!`/`^` negation)
- `**` for recursive matches (not expanded or validated beyond syntax)
- `{a,b,c}` brace alternation, one level deep
- `\` escapes any of the characters above

This is the informal dialect shared by most glob-consuming config files.
It is not Python's `glob` module, which doesn't understand `{...}` at all.

## Library use

```python
from globfmt import normalize_pattern, GlobSyntaxError

normalize_pattern("./src/*.py")                       # raises GlobSyntaxError
normalize_pattern("./src/*.py", lenient=True)          # "src/*.py"
```

## Install

No dependencies beyond the standard library.

```
pip install -e .
```

## Status

Early skeleton. See the issue tracker for what's missing before this is
useful as more than a demo.
