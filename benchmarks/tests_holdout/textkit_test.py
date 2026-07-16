"""Held-out acceptance tests for the textkit toolkit (24 functions).

Entrypoint: textkit.py exposing the functions below.
"""
import textkit as T


def test_slugify():
    assert T.slugify("Hello,  World!") == "hello-world"
    assert T.slugify("  a__b  ") == "a-b"


def test_snake_case():
    assert T.snake_case("Hello World-Foo") == "hello_world_foo"


def test_title_case():
    assert T.title_case("hELLo woRLD") == "Hello World"


def test_capitalize_first():
    assert T.capitalize_first("hello WORLD") == "Hello WORLD"


def test_snake_to_camel():
    assert T.snake_to_camel("foo_bar_baz") == "fooBarBaz"


def test_camel_to_snake():
    assert T.camel_to_snake("fooBarBaz") == "foo_bar_baz"


def test_ordinal_normal():
    assert [T.ordinal(n) for n in (1, 2, 3, 4, 21, 22, 23)] == \
        ["1st", "2nd", "3rd", "4th", "21st", "22nd", "23rd"]


def test_ordinal_teens_exception():
    assert [T.ordinal(n) for n in (11, 12, 13, 111, 112, 113)] == \
        ["11th", "12th", "13th", "111th", "112th", "113th"]


def test_truncate():
    assert T.truncate("hello world", 8) == "hello w…"  # 7 chars + ellipsis = 8
    assert T.truncate("hi", 8) == "hi"


def test_pluralize():
    assert T.pluralize("city") == "cities"
    assert T.pluralize("boy") == "boys"
    assert T.pluralize("box") == "boxes"
    assert T.pluralize("church") == "churches"
    assert T.pluralize("child") == "children"


def test_count_words():
    assert T.count_words("  a  b   c ") == 3
    assert T.count_words("") == 0


def test_reverse_words():
    assert T.reverse_words("hello there world") == "world there hello"


def test_is_palindrome():
    assert T.is_palindrome("A man, a plan, a canal: Panama") is True
    assert T.is_palindrome("hello") is False


def test_format_bytes():
    assert T.format_bytes(500) == "500.0 B"
    assert T.format_bytes(1024) == "1.0 KB"
    assert T.format_bytes(1536) == "1.5 KB"
    assert T.format_bytes(1048576) == "1.0 MB"


def test_clamp():
    assert T.clamp(5, 0, 10) == 5
    assert T.clamp(-3, 0, 10) == 0
    assert T.clamp(99, 0, 10) == 10


def test_percent():
    assert T.percent(1, 3) == "33%"
    assert T.percent(2, 3) == "67%"
    assert T.percent(1, 0) == "0%"


def test_initials():
    assert T.initials("john ronald tolkien") == "JRT"


def test_dedupe_spaces():
    assert T.dedupe_spaces("a  b   c ") == "a b c"


def test_wrap_words():
    assert T.wrap_words("the quick brown fox", 9) == ["the quick", "brown fox"]


def test_mask():
    assert T.mask("1234567890", 4) == "******7890"
    assert T.mask("abc", 5) == "abc"


def test_roman():
    assert T.roman(4) == "IV"
    assert T.roman(9) == "IX"
    assert T.roman(40) == "XL"
    assert T.roman(1994) == "MCMXCIV"


def test_from_roman():
    assert T.from_roman("MCMXCIV") == 1994
    assert T.from_roman("XLII") == 42


def test_is_anagram():
    assert T.is_anagram("listen", "silent") is True
    assert T.is_anagram("hello", "world") is False


def test_caesar():
    assert T.caesar("abc", 1) == "bcd"
    assert T.caesar("xyz", 3) == "abc"
    assert T.caesar("Hello, World!", 13) == "Uryyb, Jbeyq!"


def test_count_vowels():
    assert T.count_vowels("Hello World") == 3
