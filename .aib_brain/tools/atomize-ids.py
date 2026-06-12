#!/usr/bin/env python3
"""Replace numeric indexes in context-atomic.md with hash-based IDs.

Each atomic statement ID (e.g. D-0001, FR-0023A) is replaced with
AREA-XXXXXXXX where XXXXXXXX = sha1(area + statement_text)[:8].
"""
import hashlib
import re
import sys
from pathlib import Path

PATTERN = re.compile(r'^(\s*- )([A-Z]+)-[0-9]+[A-Z]*(:[ \t]+.+)$')


def text_hash(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:8]


def process(content: str) -> str:
    lines = []
    for line in content.splitlines(keepends=True):
        m = PATTERN.match(line)
        if m:
            prefix, area, rest = m.group(1), m.group(2), m.group(3)
            statement = rest[2:].rstrip('\n')  # strip ": " prefix and newline
            h = text_hash(area + statement)
            line = f"{prefix}{area}-{h}{rest.rstrip()}\n"
        lines.append(line)
    return ''.join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: atomize-ids.py <path/to/context-atomic.md>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])
    original = path.read_text(encoding='utf-8')
    updated = process(original)

    if original == updated:
        print("No changes needed.")
        return

    path.write_text(updated, encoding='utf-8')
    changed = sum(1 for a, b in zip(original.splitlines(), updated.splitlines()) if a != b)
    print(f"Updated {changed} line(s) in {path}.")


if __name__ == '__main__':
    main()
