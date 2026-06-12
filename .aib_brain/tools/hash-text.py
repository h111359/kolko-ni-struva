#!/usr/bin/env python3
import hashlib
import sys

if len(sys.argv) < 2:
    print("Usage: hash-text.py <text>", file=sys.stderr)
    sys.exit(1)

text = sys.argv[1]
digest = hashlib.sha1(text.encode()).hexdigest()[:8]
print(digest)
