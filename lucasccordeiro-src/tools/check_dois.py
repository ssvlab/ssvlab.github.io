#!/usr/bin/env python3
"""Verify every DOI in the bibliography resolves, and to the right paper.

Publishers answer automated requests with 403, so a plain HTTP check of
doi.org tells us nothing. DOI content negotiation returns registry metadata
instead, which confirms the DOI exists and lets us compare its registered
title against ours: a DOI that resolves to a different paper is worse than
one that 404s, because nothing looks wrong.

Usage: check_dois.py <papers.bib>
"""

import concurrent.futures as futures
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from difflib import SequenceMatcher

HEADERS = {"Accept": "application/vnd.citationstyles.csl+json",
           "User-Agent": "link-check (mailto:lucas.cordeiro@manchester.ac.uk)"}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def entries(path):
    text = open(path, encoding="utf-8").read()
    for block in re.findall(r"@\w+\{.*?\n\}", text, re.S):
        doi = re.search(r"\n\s*doi\s*=\s*\{([^}]+)\}", block)
        title = re.search(r"\n\s*title\s*=\s*\{(.+?)\},\n", block, re.S)
        if doi and title:
            yield doi.group(1).strip(), " ".join(title.group(1).split())


def resolve(item):
    doi, title = item
    url = "https://doi.org/" + urllib.parse.quote(doi, safe="/:")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            meta = json.load(resp)
    except urllib.error.HTTPError as e:
        return doi, title, None, "HTTP %d" % e.code
    except Exception as e:
        return doi, title, None, type(e).__name__

    registered = meta.get("title")
    if isinstance(registered, list):
        registered = registered[0] if registered else ""
    return doi, title, registered or "", None


def main():
    items = sorted(set(entries(sys.argv[1])))
    print("DOIs in bibliography : %d\n" % len(items))

    unresolved, mismatched, ok = [], [], 0
    with futures.ThreadPoolExecutor(max_workers=6) as pool:
        for doi, title, registered, err in pool.map(resolve, items):
            if err:
                unresolved.append((doi, title, err))
                continue
            ours, theirs = norm(title), norm(registered)
            ratio = SequenceMatcher(None, ours, theirs).ratio()
            # some registries store only the short name, e.g. "BMCLua" for a
            # paper titled "BMCLua: A Translator for Model Checking Lua Programs"
            if theirs and ours.startswith(theirs):
                ratio = 1.0
            if ratio < 0.80:
                mismatched.append((doi, title, registered, ratio))
            else:
                ok += 1

    print("resolve, title matches : %d" % ok)
    print("did not resolve        : %d" % len(unresolved))
    for doi, title, err in unresolved:
        print("   %-34s %-10s %s" % (doi, err, title[:60]))
    print("resolve, title differs : %d" % len(mismatched))
    for doi, title, registered, ratio in sorted(mismatched, key=lambda r: r[3]):
        print("\n   %s  (similarity %.2f)" % (doi, ratio))
        print("     ours      : %s" % title[:96])
        print("     registered: %s" % registered[:96])

    return 1 if unresolved or mismatched else 0


if __name__ == "__main__":
    import urllib.parse
    sys.exit(main())
