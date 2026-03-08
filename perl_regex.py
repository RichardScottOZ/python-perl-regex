"""perl_regex - Perl regular expressions for Python with Perl-compatible syntax.

This module provides Perl-like regex operations in Python, supporting:
- m/pattern/flags  - match/search (also bare /pattern/flags)
- s/pattern/replacement/flags  - substitution
- tr/chars/replacement/flags   - transliteration (also y///)

Perl flags supported:
- i  - case insensitive
- g  - global (match/replace all occurrences)
- m  - multiline (^ and $ match line boundaries)
- s  - single-line/dotall (. matches newlines)
- x  - extended/verbose (ignore whitespace and comments in pattern)
- e  - eval replacement as Python expression (substitution only)

Transliteration-specific flags:
- c  - complement the search characters (operates over the Latin-1 range U+0000–U+00FF)
- d  - delete unmatched characters
- s  - squeeze duplicate replaced characters

Alternate delimiters are supported for all operations, e.g.:
- m|pattern|, m{pattern}, m(pattern), m<pattern>
- s|old|new|, s{old}{new}, etc.

Security note:
    The ``e`` flag for substitution (``s/pat/expr/e``) evaluates the
    replacement string as a Python expression using :func:`eval`.  **Only
    use the ``e`` flag with trusted, hard-coded replacement strings.**
    Never pass untrusted user input as the replacement expression.

Example usage::

    from perl_regex import match, search, findall, sub, tr

    # Match
    m = match(r'/^hello/i', 'Hello World')

    # Find all
    nums = findall(r'/\\d+/g', 'foo 42 bar 7 baz')

    # Substitute
    result = sub(r's/foo/bar/g', 'foo and foo')

    # Transliterate
    result, count = tr(r'tr/a-z/A-Z/', 'hello')
"""

import re
from typing import List, Optional, Tuple, Union

__version__ = "0.1.0"
__all__ = [
    "PerlRegex",
    "match",
    "search",
    "findall",
    "sub",
    "tr",
    "split",
]

# Paired delimiters
_PAIRED = {"(": ")", "[": "]", "{": "}", "<": ">"}


def _parse_delimited_section(s: str, pos: int, open_d: str, close_d: str) -> Tuple[str, int]:
    """Parse one delimited section starting after the opening delimiter.

    Returns (content, position_after_close_delimiter).
    Handles nested paired delimiters and backslash escapes.
    """
    depth = 1 if open_d != close_d else 0
    content: List[str] = []
    paired = open_d != close_d

    while pos < len(s):
        ch = s[pos]
        if ch == "\\":
            # Consume escape sequence verbatim
            content.append(ch)
            pos += 1
            if pos < len(s):
                content.append(s[pos])
                pos += 1
        elif paired and ch == open_d:
            depth += 1
            content.append(ch)
            pos += 1
        elif ch == close_d:
            if paired:
                depth -= 1
                if depth == 0:
                    return "".join(content), pos + 1
                content.append(ch)
                pos += 1
            else:
                return "".join(content), pos + 1
        else:
            content.append(ch)
            pos += 1

    raise ValueError(f"Unterminated regex section at position {pos}")


def _parse_perl_regex(perl_str: str) -> Tuple[str, str, Optional[str], str]:
    """Parse a Perl regex string.

    Returns ``(operation, pattern, replacement, flags_str)`` where
    *operation* is one of ``'m'``, ``'s'``, ``'tr'``, *replacement* is
    ``None`` for match operations, and *flags_str* is the trailing flags.

    Raises :exc:`ValueError` on malformed input.
    """
    s = perl_str.strip()
    if not s:
        raise ValueError("Empty regex string")

    # Determine operation and consume the operator prefix
    if s.startswith("s") and len(s) > 1 and not s[1].isalpha():
        op = "s"
        pos = 1
    elif (s.startswith("tr") and len(s) > 2 and not s[2].isalpha()) or (
        s.startswith("y") and len(s) > 1 and not s[1].isalpha()
    ):
        op = "tr"
        pos = 2 if s.startswith("tr") else 1
    elif s.startswith("m") and len(s) > 1 and not s[1].isalpha():
        op = "m"
        pos = 1
    elif s[0] in r"/!@#%^&*|~;,":
        # Bare /pattern/ shorthand for m//
        op = "m"
        pos = 0
    else:
        raise ValueError(
            f"Unrecognised Perl regex operation in: {perl_str!r}. "
            "Expected m//, s///, tr///, y///, or bare /pattern/."
        )

    if pos >= len(s):
        raise ValueError(f"Missing delimiter in: {perl_str!r}")

    open_d = s[pos]
    close_d = _PAIRED.get(open_d, open_d)
    pos += 1  # skip opening delimiter

    # --- parse first section (pattern) ---
    pattern, pos = _parse_delimited_section(s, pos, open_d, close_d)

    if op == "m":
        # flags are everything that remains
        flags_str = s[pos:]
        return op, pattern, None, flags_str

    # For s/// and tr/// we need a second section.
    # With paired delimiters the second section can have its own delimiter.
    if open_d != close_d:
        # Skip optional whitespace between sections
        while pos < len(s) and s[pos].isspace():
            pos += 1
        if pos >= len(s):
            raise ValueError(f"Missing replacement delimiter in: {perl_str!r}")
        open_d2 = s[pos]
        close_d2 = _PAIRED.get(open_d2, open_d2)
        pos += 1
    else:
        open_d2 = open_d
        close_d2 = close_d

    replacement, pos = _parse_delimited_section(s, pos, open_d2, close_d2)
    flags_str = s[pos:]
    return op, pattern, replacement, flags_str


def _perl_flags_to_re(flags_str: str) -> int:
    """Convert Perl flag characters to a ``re`` flags integer."""
    py_flags = 0
    if "i" in flags_str:
        py_flags |= re.IGNORECASE
    if "m" in flags_str:
        py_flags |= re.MULTILINE
    if "s" in flags_str:
        py_flags |= re.DOTALL
    if "x" in flags_str:
        py_flags |= re.VERBOSE
    if "u" in flags_str:
        py_flags |= re.UNICODE
    return py_flags


def _expand_char_class(chars: str) -> str:
    """Expand a character-class string that may contain ``a-z`` ranges."""
    result: List[str] = []
    i = 0
    while i < len(chars):
        if i + 2 < len(chars) and chars[i + 1] == "-":
            start_ord = ord(chars[i])
            end_ord = ord(chars[i + 2])
            if start_ord > end_ord:
                raise ValueError(
                    f"Invalid range {chars[i]!r}-{chars[i+2]!r} in transliteration"
                )
            result.extend(chr(c) for c in range(start_ord, end_ord + 1))
            i += 3
        else:
            result.append(chars[i])
            i += 1
    return "".join(result)


def _build_tr_table(search_chars: str, replace_chars: str, flags_str: str) -> dict:
    """Build a translation table for :func:`tr`.

    *flags_str* may contain:
    - ``c`` - complement *search_chars*
    - ``d`` - delete characters not in *replace_chars*
    - ``s`` - squeeze consecutive identical output characters
    """
    src = _expand_char_class(search_chars)
    dst = _expand_char_class(replace_chars)

    complement = "c" in flags_str
    delete = "d" in flags_str

    if complement:
        # Complement is computed over the Latin-1 range (U+0000–U+00FF).
        # For full Unicode complement support, supply an explicit character
        # list instead of relying on the ``c`` flag.
        all_chars = set(chr(i) for i in range(256))
        src_set = set(src)
        src = "".join(sorted(all_chars - src_set, key=ord))

    table: dict = {}

    for i, ch in enumerate(src):
        if i < len(dst):
            table[ord(ch)] = dst[i]
        elif delete:
            table[ord(ch)] = None
        else:
            # Map to last replacement character
            table[ord(ch)] = dst[-1] if dst else None

    return table


class PerlRegex:
    """Object representing a compiled Perl regex operation.

    Instantiate with a Perl regex string::

        pr = PerlRegex(r's/foo/bar/gi')
        result = pr.execute('foo and FOO')   # 'bar and bar'

        pr2 = PerlRegex(r'/\\d+/g')
        matches = pr2.execute('a1b22c333')   # ['1', '22', '333']
    """

    def __init__(self, perl_str: str) -> None:
        self._perl_str = perl_str
        self._op, self._pattern, self._replacement, self._flags_str = _parse_perl_regex(
            perl_str
        )
        self._re_flags = _perl_flags_to_re(self._flags_str)
        self._global = "g" in self._flags_str
        self._eval_repl = "e" in self._flags_str

        if self._op in ("m", "s"):
            self._compiled = re.compile(self._pattern, self._re_flags)
        else:
            self._compiled = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def op(self) -> str:
        """Operation type: ``'m'``, ``'s'``, or ``'tr'``."""
        return self._op

    @property
    def pattern(self) -> str:
        """The pattern portion of the Perl regex."""
        return self._pattern

    @property
    def replacement(self) -> Optional[str]:
        """The replacement portion (``None`` for match operations)."""
        return self._replacement

    @property
    def flags(self) -> str:
        """The raw flags string (e.g. ``'gi'``)."""
        return self._flags_str

    # ------------------------------------------------------------------
    # Execute against a string
    # ------------------------------------------------------------------

    def execute(self, string: str):
        """Execute this Perl regex operation against *string*.

        Return values depend on the operation:

        - ``'m'`` without ``g``: the first :class:`re.Match` object, or
          ``None`` if no match.
        - ``'m'`` with ``g``: a list of strings (captured groups, or the
          whole match when there are none), like :func:`re.findall`.
        - ``'s'``: the resulting string after substitution.
        - ``'tr'``: a ``(result_string, count)`` tuple where *count* is
          the number of characters translated.
        """
        if self._op == "m":
            return self._do_match(string)
        if self._op == "s":
            return self._do_sub(string)
        return self._do_tr(string)

    def match(self, string: str) -> Optional[re.Match]:
        """Return the first match of the pattern against *string* (match op only)."""
        if self._op != "m":
            raise TypeError("match() is only available for m// operations")
        return self._compiled.search(string)

    def search(self, string: str) -> Optional[re.Match]:
        """Alias for :meth:`match`."""
        return self.match(string)

    def findall(self, string: str) -> List[str]:
        """Return all non-overlapping matches (match op only)."""
        if self._op != "m":
            raise TypeError("findall() is only available for m// operations")
        return self._compiled.findall(string)

    def sub(self, string: str) -> str:
        """Apply substitution to *string* (s/// op only)."""
        if self._op != "s":
            raise TypeError("sub() is only available for s/// operations")
        return self._do_sub(string)

    # ------------------------------------------------------------------
    # Internal implementations
    # ------------------------------------------------------------------

    def _do_match(self, string: str):
        if self._global:
            return self._compiled.findall(string)
        return self._compiled.search(string)

    def _do_sub(self, string: str) -> str:
        repl = self._replacement
        count = 0 if self._global else 1

        if self._eval_repl:
            # Security note: the /e flag evaluates the replacement string as a
            # Python expression.  Only use this flag with trusted replacement
            # strings — never with untrusted user input.
            def _eval_repl_fn(m: re.Match) -> str:
                # Make match groups available via positional names
                env = {"m": m}
                env.update({f"_{i}": g for i, g in enumerate(m.groups(), 1)})
                return str(eval(repl, env))  # noqa: S307

            return self._compiled.sub(_eval_repl_fn, string, count=count)

        # Convert Perl-style backreferences ($1, $2, \1) to Python (\1, \2)
        py_repl = _perl_repl_to_python(repl)
        return self._compiled.sub(py_repl, string, count=count)

    def _do_tr(self, string: str) -> Tuple[str, int]:
        table = _build_tr_table(self._pattern, self._replacement or "", self._flags_str)
        squeeze = "s" in self._flags_str

        result: List[str] = []
        count = 0
        prev_out: Optional[str] = None

        for ch in string:
            key = ord(ch)
            if key in table:
                out = table[key]
                count += 1
                if out is None:
                    prev_out = None
                    continue
                if squeeze and out == prev_out:
                    continue
                result.append(out)
                prev_out = out
            else:
                result.append(ch)
                prev_out = ch

        return "".join(result), count

    def __repr__(self) -> str:
        return f"PerlRegex({self._perl_str!r})"


# ---------------------------------------------------------------------------
# Helper: convert Perl replacement string backreferences to Python style
# ---------------------------------------------------------------------------

_PERL_BACKREF_RE = re.compile(r"\$(\d+)|\$\{(\d+)\}|\\(\d+)")


def _perl_repl_to_python(repl: str) -> str:
    r"""Convert Perl-style ``$1``/``${1}``/``\1`` backreferences to Python ``\1``."""

    def _replace(m: re.Match) -> str:
        group_num = m.group(1) or m.group(2) or m.group(3)
        return "\\" + group_num

    return _PERL_BACKREF_RE.sub(_replace, repl)


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


def match(perl_str: str, string: str) -> Optional[re.Match]:
    """Match *perl_str* (a ``m//`` or bare ``/pattern/`` expression) against *string*.

    Returns the first :class:`re.Match` object, or ``None``.

    Example::

        m = match(r'/hello/i', 'say Hello')
        if m:
            print(m.group())
    """
    pr = PerlRegex(perl_str)
    if pr.op not in ("m",):
        raise ValueError(f"Expected a match operation, got {pr.op!r}")
    return pr.match(string)


def search(perl_str: str, string: str) -> Optional[re.Match]:
    """Alias for :func:`match` — search *string* for *perl_str*."""
    return match(perl_str, string)


def findall(perl_str: str, string: str) -> List[str]:
    """Return all non-overlapping matches of *perl_str* in *string*.

    Example::

        nums = findall(r'/\\d+/g', 'foo 42 bar 7')
        # ['42', '7']
    """
    pr = PerlRegex(perl_str)
    if pr.op != "m":
        raise ValueError(f"Expected a match operation, got {pr.op!r}")
    return pr.findall(string)


def sub(perl_str: str, string: str) -> str:
    """Apply a Perl substitution *perl_str* to *string* and return the result.

    Example::

        result = sub(r's/foo/bar/g', 'foo and foo')
        # 'bar and bar'
    """
    pr = PerlRegex(perl_str)
    if pr.op != "s":
        raise ValueError(f"Expected a substitution operation, got {pr.op!r}")
    return pr.sub(string)


def tr(perl_str: str, string: str) -> Tuple[str, int]:
    """Apply a Perl transliteration *perl_str* to *string*.

    Returns ``(result, count)`` where *count* is the number of characters
    that were translated/deleted.

    Example::

        result, n = tr(r'tr/a-z/A-Z/', 'hello')
        # ('HELLO', 5)
    """
    pr = PerlRegex(perl_str)
    if pr.op != "tr":
        raise ValueError(f"Expected a transliteration operation, got {pr.op!r}")
    return pr._do_tr(string)


def split(perl_str: str, string: str, maxsplit: int = 0) -> List[str]:
    """Split *string* using the pattern in *perl_str*.

    Example::

        parts = split(r'/\\s+/', 'one  two   three')
        # ['one', 'two', 'three']
    """
    pr = PerlRegex(perl_str)
    if pr.op != "m":
        raise ValueError(f"Expected a match operation for split, got {pr.op!r}")
    return pr._compiled.split(string, maxsplit=maxsplit)
