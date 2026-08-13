#!/usr/bin/env python3
"""Check that no link target on the legacy page is missing from the new site.

Compares every href on the old single-page site against every href across the
built al-folio site, normalising the forms that differ cosmetically (http vs
https, dx.doi.org vs doi.org, trailing slashes, %-escapes). Anything the old
page reached and the new site does not is reported as a loss.

Usage: link_diff.py <legacy/index.html> <built-site-dir>
"""

import html
import os
import re
import sys
import urllib.parse
from collections import defaultdict

SITE = "ssvlab.github.io/lucasccordeiro/"


def hrefs(text):
    return set(re.findall(r'href="([^"]+)"', text)) | set(re.findall(r'src="([^"]+)"', text))


def normalise(url):
    """Collapse the cosmetic differences so only real losses remain."""
    url = html.unescape(urllib.parse.unquote(url.strip()))
    url = re.sub(r"^\./", "", url)  # legacy links are relative to the old page
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"^www\.", "", url)
    url = url.rstrip("/")

    doi = re.match(r"(?:dx\.)?doi\.org/(.+)$", url)
    if doi:
        return "doi:" + doi.group(1).lower()
    # publisher URLs carry the DOI in the path: the same target, differently dressed
    embedded = re.search(r"(?:doi(?:/epdf|/abs|/full)?|article)/(10\.\d{4,9}/[^?#]+)$", url)
    if embedded:
        return "doi:" + embedded.group(1).lower()
    ieee = re.match(r"doi\.ieeecomputersociety\.org/(.+)$", url)
    if ieee:
        return "doi:" + ieee.group(1).lower()
    if url.startswith("ssvlab.github.io/"):
        url = url[len("ssvlab.github.io/"):]
        url = re.sub(r"^lucasccordeiro(?:-preview)?/", "", url)
    return url.lower()


def classify(url):
    for kind in ("papers/", "talks/", "supervisions/", "awards/", "cv/", "courses/", "files/", "vss/"):
        if url.startswith(kind):
            return kind.rstrip("/")
    if url.startswith("doi:"):
        return "doi"
    if url.startswith("#"):
        return "anchor"
    return "external"


def main():
    old_html = open(sys.argv[1], encoding="utf-8").read()
    built = sys.argv[2]

    old = {normalise(u) for u in hrefs(old_html) if not u.startswith(("mailto:", "javascript:"))}
    old.discard("")

    new = set()
    pages = 0
    for root, _, files in os.walk(built):
        for name in files:
            if name.endswith(".html"):
                pages += 1
                new |= {normalise(u) for u in hrefs(open(os.path.join(root, name),
                                                       encoding="utf-8", errors="ignore").read())}

    missing = defaultdict(list)
    for url in sorted(old - new):
        if url.startswith("#"):
            missing["anchor"].append(url)
        else:
            missing[classify(url)].append(url)

    print("old page links      : %d" % len(old))
    print("new site links      : %d across %d pages" % (len(new), pages))
    print("reachable in both   : %d" % len(old & new))
    print("missing from new    : %d" % sum(len(v) for v in missing.values()))
    for kind in sorted(missing):
        print("\n  %s (%d)" % (kind, len(missing[kind])))
        for url in missing[kind]:
            print("    %s" % url[:110])

    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
