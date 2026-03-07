"""Tests for perl_regex module."""

import re
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from perl_regex import (
    PerlRegex,
    findall,
    match,
    search,
    split,
    sub,
    tr,
    _parse_perl_regex,
    _perl_repl_to_python,
)


# ---------------------------------------------------------------------------
# Parsing tests
# ---------------------------------------------------------------------------


class TestParsing:
    def test_bare_slash_match(self):
        op, pattern, replacement, flags = _parse_perl_regex("/hello/")
        assert op == "m"
        assert pattern == "hello"
        assert replacement is None
        assert flags == ""

    def test_m_operator(self):
        op, pattern, replacement, flags = _parse_perl_regex("m/hello/i")
        assert op == "m"
        assert pattern == "hello"
        assert replacement is None
        assert flags == "i"

    def test_m_alternate_delimiter(self):
        op, pattern, replacement, flags = _parse_perl_regex("m|hello world|x")
        assert op == "m"
        assert pattern == "hello world"
        assert flags == "x"

    def test_m_paired_delimiter(self):
        op, pattern, replacement, flags = _parse_perl_regex("m{hello}")
        assert op == "m"
        assert pattern == "hello"
        assert flags == ""

    def test_m_angle_delimiter(self):
        op, pattern, replacement, flags = _parse_perl_regex("m<hello>i")
        assert op == "m"
        assert pattern == "hello"
        assert flags == "i"

    def test_s_operator(self):
        op, pattern, replacement, flags = _parse_perl_regex("s/foo/bar/g")
        assert op == "s"
        assert pattern == "foo"
        assert replacement == "bar"
        assert flags == "g"

    def test_s_alternate_delimiter(self):
        op, pattern, replacement, flags = _parse_perl_regex("s|foo|bar|g")
        assert op == "s"
        assert pattern == "foo"
        assert replacement == "bar"
        assert flags == "g"

    def test_s_paired_delimiter(self):
        op, pattern, replacement, flags = _parse_perl_regex("s{foo}{bar}")
        assert op == "s"
        assert pattern == "foo"
        assert replacement == "bar"
        assert flags == ""

    def test_tr_operator(self):
        op, pattern, replacement, flags = _parse_perl_regex("tr/a-z/A-Z/")
        assert op == "tr"
        assert pattern == "a-z"
        assert replacement == "A-Z"
        assert flags == ""

    def test_y_operator(self):
        op, pattern, replacement, flags = _parse_perl_regex("y/a-z/A-Z/")
        assert op == "tr"
        assert pattern == "a-z"
        assert replacement == "A-Z"
        assert flags == ""

    def test_escaped_delimiter(self):
        op, pattern, replacement, flags = _parse_perl_regex(r"m/foo\/bar/")
        assert op == "m"
        assert pattern == r"foo\/bar"

    def test_empty_pattern(self):
        op, pattern, replacement, flags = _parse_perl_regex("m//")
        assert op == "m"
        assert pattern == ""

    def test_invalid_empty_string(self):
        with pytest.raises(ValueError, match="Empty regex string"):
            _parse_perl_regex("")

    def test_invalid_operation(self):
        with pytest.raises(ValueError):
            _parse_perl_regex("q/foo/")


# ---------------------------------------------------------------------------
# Match / search tests
# ---------------------------------------------------------------------------


class TestMatch:
    def test_simple_match(self):
        m = match("/hello/", "hello world")
        assert m is not None
        assert m.group() == "hello"

    def test_no_match(self):
        m = match("/xyz/", "hello world")
        assert m is None

    def test_case_insensitive(self):
        m = match("/HELLO/i", "hello world")
        assert m is not None

    def test_m_prefix(self):
        m = match("m/world/", "hello world")
        assert m is not None

    def test_multiline_flag(self):
        m = match("/^world/m", "hello\nworld")
        assert m is not None

    def test_dotall_flag(self):
        m = match("/hello.world/s", "hello\nworld")
        assert m is not None

    def test_capturing_group(self):
        m = match(r"/(\d+)/", "abc 42 def")
        assert m is not None
        assert m.group(1) == "42"

    def test_alternate_delimiter(self):
        m = match("m|hello|", "say hello")
        assert m is not None

    def test_search_alias(self):
        m = search("/hello/", "say hello there")
        assert m is not None

    def test_wrong_op_raises(self):
        with pytest.raises(ValueError):
            match("s/foo/bar/", "foo")


# ---------------------------------------------------------------------------
# Findall tests
# ---------------------------------------------------------------------------


class TestFindall:
    def test_findall_numbers(self):
        result = findall(r"/\d+/g", "foo 42 bar 7 baz 100")
        assert result == ["42", "7", "100"]

    def test_findall_no_matches(self):
        result = findall(r"/\d+/", "no numbers here")
        assert result == []

    def test_findall_with_group(self):
        result = findall(r"/(\w+)@(\w+)/g", "a@b c@d")
        assert result == [("a", "b"), ("c", "d")]

    def test_findall_case_insensitive(self):
        result = findall(r"/foo/ig", "FOO foo Foo")
        assert result == ["FOO", "foo", "Foo"]


# ---------------------------------------------------------------------------
# Substitution tests
# ---------------------------------------------------------------------------


class TestSub:
    def test_simple_sub(self):
        result = sub("s/foo/bar/", "foo baz")
        assert result == "bar baz"

    def test_global_sub(self):
        result = sub("s/foo/bar/g", "foo and foo")
        assert result == "bar and bar"

    def test_case_insensitive_sub(self):
        result = sub("s/foo/bar/gi", "FOO and Foo")
        assert result == "bar and bar"

    def test_no_match_sub(self):
        result = sub("s/xyz/bar/", "hello world")
        assert result == "hello world"

    def test_sub_with_backreference(self):
        result = sub(r"s/(\w+) (\w+)/$2 $1/", "hello world")
        assert result == "world hello"

    def test_sub_with_perl_backref_dollar(self):
        result = sub(r"s/(\d+)/[$1]/g", "a1b22c333")
        assert result == "a[1]b[22]c[333]"

    def test_sub_alternate_delimiter(self):
        result = sub("s|foo|bar|g", "foo and foo")
        assert result == "bar and bar"

    def test_sub_paired_delimiter(self):
        result = sub("s{foo}{bar}g", "foo and foo")
        assert result == "bar and bar"

    def test_sub_multiline(self):
        result = sub(r"s/^foo/bar/m", "foo\nfoo")
        assert result == "bar\nfoo"

    def test_sub_global_multiline(self):
        result = sub(r"s/^foo/bar/gm", "foo\nfoo")
        assert result == "bar\nbar"

    def test_wrong_op_raises(self):
        with pytest.raises(ValueError):
            sub("/foo/", "foo")

    def test_sub_eval_flag(self):
        # s/(\d+)/int(m.group(1)) * 2/ge — double each number (global)
        result = sub(r"s/(\d+)/int(m.group(1)) * 2/ge", "x5y10z")
        assert result == "x10y20z"

    def test_sub_eval_flag_single(self):
        # Without /g, only the first match is replaced
        result = sub(r"s/(\d+)/int(m.group(1)) * 2/e", "x5y10z")
        assert result == "x10y10z"


# ---------------------------------------------------------------------------
# Transliteration tests
# ---------------------------------------------------------------------------


class TestTr:
    def test_simple_uppercase(self):
        result, count = tr("tr/a-z/A-Z/", "hello")
        assert result == "HELLO"
        assert count == 5

    def test_simple_lowercase(self):
        result, count = tr("tr/A-Z/a-z/", "HELLO")
        assert result == "hello"
        assert count == 5

    def test_tr_no_match(self):
        result, count = tr("tr/a-z/A-Z/", "HELLO123")
        assert result == "HELLO123"
        assert count == 0

    def test_tr_partial(self):
        result, count = tr("tr/aeiou/AEIOU/", "hello world")
        assert result == "hEllO wOrld"
        assert count == 3  # e, o, o

    def test_tr_delete_flag(self):
        result, count = tr("tr/aeiou//d", "hello world")
        assert result == "hll wrld"
        assert count == 3  # e, o, o

    def test_tr_squeeze_flag(self):
        result, count = tr("tr/a-z/a-z/s", "aaabbbccc")
        assert result == "abc"
        assert count == 9

    def test_y_alias(self):
        result, count = tr("y/a-z/A-Z/", "hello")
        assert result == "HELLO"
        assert count == 5

    def test_tr_digit_to_x(self):
        result, count = tr("tr/0-9/X/", "abc123def456")
        assert result == "abcXXXdefXXX"
        assert count == 6

    def test_tr_count_only_matching(self):
        # tr/a/a/ counts occurrences of 'a'
        _, count = tr("tr/a/a/", "banana")
        assert count == 3

    def test_wrong_op_raises(self):
        with pytest.raises(ValueError):
            tr("/foo/", "foo")


# ---------------------------------------------------------------------------
# Split tests
# ---------------------------------------------------------------------------


class TestSplit:
    def test_split_whitespace(self):
        result = split(r"/\s+/", "one  two   three")
        assert result == ["one", "two", "three"]

    def test_split_comma(self):
        result = split(r"/,/", "a,b,c")
        assert result == ["a", "b", "c"]

    def test_split_maxsplit(self):
        result = split(r"/\s+/", "one two three four", maxsplit=2)
        assert result == ["one", "two", "three four"]

    def test_wrong_op_raises(self):
        with pytest.raises(ValueError):
            split("s/foo/bar/", "foo")


# ---------------------------------------------------------------------------
# PerlRegex class tests
# ---------------------------------------------------------------------------


class TestPerlRegexClass:
    def test_repr(self):
        pr = PerlRegex("/hello/")
        assert "PerlRegex" in repr(pr)
        assert "hello" in repr(pr)

    def test_properties(self):
        pr = PerlRegex("s/foo/bar/gi")
        assert pr.op == "s"
        assert pr.pattern == "foo"
        assert pr.replacement == "bar"
        assert "g" in pr.flags
        assert "i" in pr.flags

    def test_execute_match(self):
        pr = PerlRegex("/hello/i")
        result = pr.execute("say Hello there")
        assert result is not None

    def test_execute_match_global(self):
        pr = PerlRegex(r"/\d+/g")
        result = pr.execute("1 fish 2 fish")
        assert result == ["1", "2"]

    def test_execute_sub(self):
        pr = PerlRegex("s/foo/bar/g")
        result = pr.execute("foo and foo")
        assert result == "bar and bar"

    def test_execute_tr(self):
        pr = PerlRegex("tr/a-z/A-Z/")
        result = pr.execute("hello")
        assert result == ("HELLO", 5)

    def test_match_method_wrong_op(self):
        pr = PerlRegex("s/foo/bar/")
        with pytest.raises(TypeError):
            pr.match("foo")

    def test_findall_method_wrong_op(self):
        pr = PerlRegex("s/foo/bar/")
        with pytest.raises(TypeError):
            pr.findall("foo")

    def test_sub_method_wrong_op(self):
        pr = PerlRegex("/foo/")
        with pytest.raises(TypeError):
            pr.sub("foo")


# ---------------------------------------------------------------------------
# Backreference conversion helper
# ---------------------------------------------------------------------------


class TestPerlReplToPython:
    def test_dollar_backref(self):
        assert _perl_repl_to_python("$1") == r"\1"

    def test_dollar_braced_backref(self):
        assert _perl_repl_to_python("${2}") == r"\2"

    def test_backslash_backref(self):
        assert _perl_repl_to_python(r"\1") == r"\1"

    def test_mixed(self):
        result = _perl_repl_to_python(r"$2-\1")
        assert result == r"\2-\1"

    def test_no_backref(self):
        assert _perl_repl_to_python("hello") == "hello"


# ---------------------------------------------------------------------------
# Edge-case / integration tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_nested_braces_in_pattern(self):
        # Perl: m{(\w{3})} — pattern contains nested braces
        pr = PerlRegex(r"m{(\w{3})}")
        m = pr.match("hello world")
        assert m is not None
        assert m.group(1) == "hel"

    def test_empty_replacement(self):
        result = sub("s/foo//g", "foo bar foo")
        assert result == " bar "

    def test_multiline_string_dotall(self):
        result = sub(r"s/start.*end/REPLACED/s", "start\nmiddle\nend of text")
        assert result == "REPLACED of text"

    def test_verbose_pattern(self):
        # Extended/verbose mode — spaces and # comments are ignored in pattern
        m = match(
            r"m/   \d+  # one or more digits /x",
            "price: 42 dollars",
        )
        assert m is not None
        assert m.group() == "42"

    def test_tr_complement_delete(self):
        # Delete everything that is NOT a digit
        result, count = tr("tr/0-9//cd", "abc123def456")
        assert result == "123456"

    def test_global_findall_no_g_flag(self):
        # Without /g flag, findall still works on the PerlRegex object
        pr = PerlRegex(r"/\d+/")
        result = pr.findall("1 2 3")
        assert result == ["1", "2", "3"]
