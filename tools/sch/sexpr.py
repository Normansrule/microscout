# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2
"""Minimal S-expression reader/writer for KiCad files (MIT)."""
import re

_TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


class Sym(str):
    """An unquoted atom (keyword or number)."""


def parse(text):
    stack, cur = [], []
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOKEN.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError(f"bad token at {pos}: {text[pos:pos+40]!r}")
        pos = m.end()
        if m.group(1):
            stack.append(cur)
            cur = []
        elif m.group(2):
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif m.group(3) is not None:
            cur.append(m.group(3).replace('\\"', '"').replace("\\\\", "\\"))
        else:
            cur.append(Sym(m.group(4)))
    assert not stack, "unbalanced parentheses"
    return cur


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def dump(x, indent=0):
    """Serialise a nested list. Strings that are not Sym are quoted."""
    if isinstance(x, list):
        if not x:
            return "()"
        simple = all(not isinstance(e, list) for e in x)
        parts = [dump(e, indent + 1) for e in x]
        if simple or len(x) <= 2 and sum(len(p) for p in parts) < 60:
            return "(" + " ".join(parts) + ")"
        out = "(" + parts[0]
        for e, p in zip(x[1:], parts[1:]):
            if isinstance(e, list):
                out += "\n" + "  " * (indent + 1) + p
            else:
                out += " " + p
        return out + ")"
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, (int, float)):
        return fmt_num(x)
    return q(x)


def fmt_num(v):
    if isinstance(v, int):
        return str(v)
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def find(node, key):
    """First child list whose head is key."""
    for e in node:
        if isinstance(e, list) and e and e[0] == key:
            return e
    return None


def find_all(node, key):
    return [e for e in node if isinstance(e, list) and e and e[0] == key]
