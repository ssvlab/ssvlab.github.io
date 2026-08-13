#!/usr/bin/env python3
"""Turn the legacy page's News section into al-folio _news entries.

Each <p> becomes one inline announcement. Dates come from the leading
"(Month-Year)" label; year-only labels land on 1 July so they sort inside
their year without implying a precision the source does not have.

Usage: extract_news.py <legacy/index.html> <_news dir>
"""

import html
import os
import re
import sys

MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"])}


def to_markdown(fragment):
    md = re.sub(r'<a href="([^"]+)"\s*>(.*?)</a>',
                lambda m: "[%s](%s)" % (re.sub(r"<[^>]+>", "", m.group(2)).strip(), m.group(1)),
                fragment, flags=re.S)
    md = re.sub(r"</?b>", "**", md)
    md = re.sub(r"<[^>]+>", "", md)
    return " ".join(html.unescape(md).split())


def parse_date(text):
    m = re.match(r"\s*\**\(?(?:News\s*)?\(?([A-Za-z]+)[-\s](\d{4})\)?", text)
    if m:
        word = m.group(1).lower()
        month = MONTHS.get(word) or next(
            (v for k, v in MONTHS.items() if k.startswith(word) and len(word) >= 3), None)
        if month:
            return "%s-%02d-01" % (m.group(2), month), m.end()
    m = re.match(r"\s*\**\(?(?:News\s*)?\(?(\d{4})\)?", text)
    if m:
        return "%s-07-01" % m.group(1), m.end()
    return None, 0


def main():
    doc = open(sys.argv[1], encoding="utf-8").read()
    outdir = sys.argv[2]
    start = doc.index('<section id="news">')
    end = doc.index("</section>", start)

    written, seen = 0, {}
    for chunk in re.findall(r"<p>.*?</p>", doc[start:end], re.S):
        md = to_markdown(chunk)
        if not md:
            continue
        date, cut = parse_date(md)
        if not date:
            continue
        body = md[cut:].lstrip(" *:!)-—")
        body = re.sub(r"^\**\s*", "", body)
        if not body:
            continue

        seen[date] = seen.get(date, 0) + 1
        name = "%s-%02d.md" % (date, seen[date])
        with open(os.path.join(outdir, name), "w", encoding="utf-8") as fh:
            fh.write("---\nlayout: post\ndate: %s\ninline: true\nrelated_posts: false\n---\n\n%s\n"
                     % (date, body))
        written += 1

    print("news items written: %d" % written)


if __name__ == "__main__":
    main()
