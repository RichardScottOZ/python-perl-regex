# python-perl-regex

Perl regular expressions for Python — use Perl regex syntax directly in Python code.

## Features

* `m/pattern/flags` or bare `/pattern/flags` — match / search
* `s/pattern/replacement/flags` — substitution
* `tr/chars/replacement/flags` / `y/chars/replacement/flags` — transliteration
* Alternate delimiters: `m|…|`, `m{…}`, `m(…)`, `m<…>`, etc.
* Perl flags: `i` (case-insensitive), `g` (global), `m` (multiline), `s` (dotall), `x` (verbose), `e` (eval replacement)
* Transliteration flags: `c` (complement), `d` (delete), `s` (squeeze)
* Perl-style back-references (`$1`, `${1}`, `\1`) in substitution replacement strings

## Quick start

```python
from perl_regex import match, findall, sub, tr, split

# Match
m = match(r'/(\w+)\s+(\w+)/i', 'Hello World')
print(m.group(1), m.group(2))          # Hello World

# Find all numbers
nums = findall(r'/\d+/g', 'foo 42 bar 7 baz 100')
print(nums)                             # ['42', '7', '100']

# Substitution
result = sub(r's/foo/bar/gi', 'FOO and Foo and foo')
print(result)                           # bar and bar and bar

# Back-references
result = sub(r's/(\w+) (\w+)/$2 $1/', 'hello world')
print(result)                           # world hello

# Eval replacement (double every number)
result = sub(r's/(\d+)/int(m.group(1)) * 2/ge', 'x5y10z')
print(result)                           # x10y20z

# Transliteration
result, count = tr(r'tr/a-z/A-Z/', 'hello')
print(result, count)                    # HELLO 5

# Split
parts = split(r'/\s+/', 'one  two   three')
print(parts)                            # ['one', 'two', 'three']
```

## `PerlRegex` class

```python
from perl_regex import PerlRegex

pr = PerlRegex(r's/foo/bar/gi')
print(pr.execute('FOO and Foo'))        # bar and bar

pr2 = PerlRegex(r'/\d+/g')
print(pr2.execute('a1b22c333'))         # ['1', '22', '333']
```

## Supported operations

| Operation | Syntax | Returns |
|-----------|--------|---------|
| Match | `m/pat/flags` or `/pat/flags` | `re.Match` or `None` (no `g`); `list[str]` (with `g`) |
| Substitution | `s/pat/repl/flags` | Modified string |
| Transliteration | `tr/chars/repl/flags` or `y/chars/repl/flags` | `(result, count)` tuple |
| Split | `m/pat/` passed to `split()` | `list[str]` |

## Installation

```bash
pip install perl-regex
```

Or clone and install in editable mode:

```bash
git clone https://github.com/RichardScottOZ/python-perl-regex
cd python-perl-regex
pip install -e .
```
