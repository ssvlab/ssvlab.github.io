#!/usr/bin/env python3
"""Recover metadata for entries DBLP does not index, from the CV PDF's text.

The CV cites every publication in a consistent form:

    Authors. "Title". In Venue, pp. N-M, YEAR.

Only venue, pages, volume and year are taken from here. Author lists wrap
across lines in the extracted text and come out mangled; the web page lists
them cleanly, so make_bib.py keeps using those. Writes overrides.json, merged
by make_bib.py, so regenerating from DBLP never clobbers these.

Usage: cv_overrides.py <cv.txt> <publications.json> <overrides.json>
"""

import json
import re
import sys
import unicodedata

QUOTES = "“”‘’\"'"


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def cv_entries(text):
    """Yield (authors, title, tail) for every quoted citation in the CV.

    Keyed off the quotes rather than the leading numbers: entries wrap and
    indent unpredictably in the extracted text, but every title is quoted.
    """
    text = re.sub(r"-\n\s*", "", text)            # de-hyphenate the PDF's line wraps
    text = re.sub(r"\n\s*\d{1,3}\s*\n", "\n", text)  # drop page numbers
    text = re.sub(r"\s+", " ", text)              # one continuous string

    spans = list(re.finditer(r"[%s]([^%s]{8,300}?)[%s]" % (QUOTES, QUOTES, QUOTES), text))
    for i, q in enumerate(spans):
        prev_end = spans[i - 1].end() if i else 0
        authors = text[prev_end:q.start()]
        # keep only the trailing author run, not the previous entry's tail
        authors = re.split(r"(?<=[.;])\s(?=[A-ZÀ-Ý])", authors)[-1]
        authors = re.sub(r"^\s*\*?\d{1,3}\*?[.\s]\s*", "", authors).strip(" .,:")
        tail = text[q.end(): spans[i + 1].start() if i + 1 < len(spans) else len(text)]
        # the last entry of a section runs into the next heading
        tail = re.split(r"\s(?=[A-Z][A-Z][A-Z ,&/-]{6,})", tail)[0]
        yield authors, q.group(1).strip(" ."), tail.strip(" .,:")[:300]


def split_tail(tail):
    """Pull venue, pages, volume and year out of the CV's trailing prose."""
    out = {}
    y = re.findall(r"\b(19|20)(\d{2})\b", tail)
    if y:
        out["year"] = "".join(y[-1])
    p = re.search(r"pp?\.\s*([\divxlIVXL]+)\s*[-–]+\s*([\divxlIVXL]+)", tail)
    if p:
        out["pages"] = "%s--%s" % (p.group(1), p.group(2))
    v = re.search(r"\bv\.?\s*(\d+)\s*\((\d+)\)", tail)
    if v:
        out["volume"], out["number"] = v.group(1), v.group(2)

    venue = tail
    venue = re.sub(r"^In\s+(?:the\s+)?", "", venue)
    venue = re.split(r",?\s*(?:pp?\.\s|\bv\.?\s*\d|\bvol\b)", venue)[0]
    venue = re.sub(r"[,\s]+(19|20)\d{2}\s*\.?$", "", venue.strip(" .,;"))
    venue = re.sub(r"\s+", " ", venue).strip(" .,;")
    if len(venue) > 4:
        out["venue"] = venue
    return out


def main():
    cv_text = open(sys.argv[1], encoding="utf-8").read()
    recs = json.load(open(sys.argv[2], encoding="utf-8"))

    by_title = {}
    for authors, title, tail in cv_entries(cv_text):
        by_title.setdefault(norm(title), (authors, tail))


    overrides, hit = {}, 0
    for rec in recs:
        if rec.get("dblp"):
            continue
        found = by_title.get(rec["ntitle"])
        if not found:
            # the CV sometimes carries a longer subtitle than the page
            for n, val in by_title.items():
                if n.startswith(rec["ntitle"][:40]) and len(rec["ntitle"]) >= 25:
                    found = val
                    break
        if not found:
            continue
        _, tail = found
        fields = split_tail(tail)  # venue, pages, volume, year only: see module docstring
        if fields:
            overrides[rec["title"]] = fields
            hit += 1

    json.dump(overrides, open(sys.argv[3], "w"), indent=1, ensure_ascii=False, sort_keys=True)
    missing = [r["title"] for r in recs if not r.get("dblp") and r["title"] not in overrides]
    print("entries without DBLP : %d" % sum(1 for r in recs if not r.get("dblp")))
    print("recovered from CV    : %d" % hit)
    print("still unresolved     : %d" % len(missing))
    for t in missing:
        print("   - %s" % t[:88])


if __name__ == "__main__":
    main()
