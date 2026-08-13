#!/usr/bin/env python3
"""Check every link on the built site actually resolves.

Collects hrefs and srcs from the built HTML, resolves site-relative ones
against the live host, and requests each unique target. HEAD first, falling
back to GET for servers that reject it. Reports anything that is not 2xx/3xx.

Publisher sites routinely answer automated requests with 403 even when the
page is fine, so those are reported separately from real failures rather than
being hidden or counted as broken.

Usage: check_links.py <built-site-dir> [--live https://host/base]
"""

import collections
import concurrent.futures as futures
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# hosts that answer bots with 403/429 regardless of whether the page exists
BOT_HOSTILE = ("ieeexplore.ieee.org", "linkedin.com", "researchgate.net", "sciencedirect.com",
               "onlinelibrary.wiley.com", "link.springer.com", "dl.acm.org", "portal.acm.org",
               "webofscience.com", "scopus.com", "tandfonline.com", "jstor.org",
               "scholar.google.com", "youtube.com", "youtu.be", "x.com", "twitter.com",
               # Pure refuses automated requests for every path, including its own search
               "research.manchester.ac.uk", "unsplash.com", "doi.org")

BLOCKED_CODES = (401, 403, 429, 999)  # 999 is LinkedIn's bot response

SKIP_SCHEMES = ("mailto:", "javascript:", "tel:", "data:")


def collect(root):
    """Map every unique link target to the pages that reference it."""
    found = collections.defaultdict(set)
    for dirpath, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".html"):
                continue
            path = os.path.join(dirpath, name)
            page = os.path.relpath(path, root)
            text = open(path, encoding="utf-8", errors="ignore").read()
            for url in re.findall(r'(?:href|src)="([^"]+)"', text):
                url = url.strip()
                if url and not url.startswith("#") and not url.startswith(SKIP_SCHEMES):
                    found[url.split("#")[0]].add(page)
    return found


def request(url, method):
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
    })
    with urllib.request.urlopen(req, timeout=35) as resp:
        return resp.status


def check(url):
    """HEAD, then GET on any failure: plenty of servers answer HEAD with 404 or
    405 for pages that serve fine, so HEAD alone produces false alarms."""
    try:
        return url, request(url, "HEAD"), ""
    except Exception:
        pass
    try:
        return url, request(url, "GET"), ""
    except urllib.error.HTTPError as e:
        return url, e.code, ""
    except Exception as e:
        return url, 0, type(e).__name__


def main():
    root = sys.argv[1]
    live = "https://ssvlab.github.io/lucasccordeiro"
    if "--live" in sys.argv:
        live = sys.argv[sys.argv.index("--live") + 1]
    live = live.rstrip("/")

    found = collect(root)
    targets = {}
    for url, pages in found.items():
        if url.startswith("//"):
            absolute = "https:" + url
        elif url.startswith("http"):
            absolute = url
        elif url.startswith("/"):
            host = "/".join(live.split("/")[:3])
            absolute = host + url
        else:
            absolute = live + "/" + url.lstrip("./")
        targets.setdefault(absolute, set()).update(pages)

    print("pages scanned  : %d" % sum(1 for _, _, f in os.walk(root) for n in f if n.endswith(".html")))
    print("unique targets : %d\n" % len(targets))

    results = []
    with futures.ThreadPoolExecutor(max_workers=8) as pool:
        for i, (url, status, err) in enumerate(pool.map(check, targets), 1):
            results.append((url, status, err))
            if i % 50 == 0:
                print("  checked %d/%d" % (i, len(targets)), file=sys.stderr)

    ok, blocked, broken = [], [], []
    for url, status, err in results:
        host = urllib.parse.urlparse(url).netloc
        if 200 <= status < 400:
            ok.append(url)
        elif status in BLOCKED_CODES and any(h in host for h in BOT_HOSTILE):
            blocked.append((url, status))
        else:
            broken.append((url, status or err, sorted(targets[url])[:3]))

    print("ok                 : %d" % len(ok))
    print("blocked to bots    : %d (publisher sites; not evidence of breakage)" % len(blocked))
    print("failing            : %d" % len(broken))
    for url, status, pages in sorted(broken, key=lambda r: str(r[1])):
        print("\n  %-6s %s" % (status, url[:110]))
        print("         linked from: %s" % ", ".join(pages))

    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
