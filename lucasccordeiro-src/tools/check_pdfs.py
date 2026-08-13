#!/usr/bin/env python3
"""Check each entry's PDF is actually that paper.

A link can resolve and still be wrong: the legacy page reused some filenames
across different papers, so an entry could carry a PDF belonging to another
publication. Compares each entry's title against the text of its PDF's first
two pages.

Usage: check_pdfs.py <papers.bib> <site-root-dir>
"""

import os
import re
import subprocess
import sys
import unicodedata
from difflib import SequenceMatcher

SITE = "https://ssvlab.github.io/lucasccordeiro/"


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def entries(path):
    text = open(path, encoding="utf-8").read()
    for block in re.findall(r"@\w+\{(.*?)\n\}", text, re.S):
        key = block.split(",", 1)[0].strip()
        pdf = re.search(r"\n\s*pdf\s*=\s*\{([^}]+)\}", block)
        title = re.search(r"\n\s*title\s*=\s*\{(.+?)\},\n", block, re.S)
        if pdf and title:
            yield key, " ".join(title.group(1).split()), pdf.group(1).strip()


def first_pages(path):
    try:
        out = subprocess.run(["pdftotext", "-f", "1", "-l", "2", path, "-"],
                             capture_output=True, timeout=40)
        return norm(out.stdout.decode("utf-8", "ignore"))
    except Exception:
        return ""


def best_window(haystack, needle):
    """How well the title matches anywhere in the extracted text."""
    if not haystack or not needle:
        return 0.0
    if needle in haystack:
        return 1.0
    words = needle.split()
    span = len(needle)
    best = 0.0
    for start in range(0, max(1, len(haystack) - span), 40):
        best = max(best, SequenceMatcher(None, needle, haystack[start:start + span]).ratio())
        if best > 0.85:
            break
    # a distinctive run of the title appearing verbatim is also good evidence
    if best < 0.85 and len(words) >= 5:
        probe = " ".join(words[:5])
        if probe in haystack:
            best = max(best, 0.85)
    return best


def main():
    bib, root = sys.argv[1], sys.argv[2]
    missing, weak, ok, unreadable = [], [], 0, []

    for key, title, url in entries(bib):
        if not url.startswith(SITE):
            continue
        path = os.path.join(root, url[len(SITE):])
        if not os.path.exists(path):
            missing.append((key, title, path))
            continue
        text = first_pages(path)
        if not text:
            unreadable.append((key, os.path.basename(path)))
            continue
        score = best_window(text, norm(title))
        if score < 0.60:
            weak.append((key, title, os.path.basename(path), score))
        else:
            ok += 1

    print("entries with a local PDF : %d" % (ok + len(weak) + len(missing) + len(unreadable)))
    print("title found in the PDF   : %d" % ok)
    print("file not on disk         : %d" % len(missing))
    for key, title, path in missing:
        print("   %-28s %s" % (key, path))
    print("no extractable text      : %d" % len(unreadable))
    for key, name in unreadable:
        print("   %-28s %s" % (key, name))
    print("title not found          : %d" % len(weak))
    for key, title, name, score in sorted(weak, key=lambda r: r[3]):
        print("\n   %s  (best match %.2f)" % (name, score))
        print("     entry: %s" % title[:96])

    return 1 if weak or missing else 0


if __name__ == "__main__":
    sys.exit(main())
