"""Conservative preservation checks for localization control tokens.

Real newlines and literal backslash escapes are deliberately different tokens.
Unknown bracket/brace content is protected until its purpose is established.
"""
import re

TOKENS = re.compile(
    r'\r\n|[\x00-\x1f\x7f]|\\(?:[A-Za-z]|[^\w\s])'
    r'|\[[^\]\r\n]*\]|\{[^}\r\n]*\}|<[^>\r\n]*>'
    r'|%(?:\d+\$)?[-+#0]*\d*(?:\.\d+)?[diouxXeEfFgGcs]'
    r'|%\d+|%%|%'
    r'|[\u00a0\u200b-\u200f\u2028\u2029\u202a-\u202e\u2060-\u2069\ufeff]'
)
BREAKS = re.compile(r'(\r\n|\r|\n|\\n|\\r)')


def signature(text):
    return TOKENS.findall(text)


def validate(source, translated):
    if '\0' in translated:
        raise ValueError('Translation contains a NUL string terminator')
    if signature(source) != signature(translated):
        raise ValueError('Control token sequence differs')
    # Keep tokens on the same logical line as in the source. Do not normalize
    # whitespace, escapes, CRLF, Unicode, case, button names or formatting tags.
    old, new = BREAKS.split(source), BREAKS.split(translated)
    if len(old) != len(new):
        raise ValueError('Line structure differs')
    for a, b in zip(old, new):
        if signature(a) != signature(b):
            raise ValueError('Control token moved across a line boundary')
