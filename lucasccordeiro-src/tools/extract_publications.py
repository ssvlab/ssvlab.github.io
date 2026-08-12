#!/usr/bin/env python3
"""Extract the publication list from the legacy hand-maintained page.

Reads the old index.html, pulls one record per <p> in the Publications
section, and reconciles it against the DBLP BibTeX export to recover proper
metadata. Emits publications.json for the bib generator, plus a report of
entries DBLP does not cover, which need to be written by hand.

Usage: extract_publications.py <index.html> <dblp.bib> <outdir>
"""

import html
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher

SITE = "https://ssvlab.github.io/lucasccordeiro/"

# venue notes DBLP carries that the page drops; anything else means a different paper
NOTE_SUFFIX = r"s|es|(a |an |the )?(competition (contribution|paper)|extended abstract|abstract|tool (paper|demonstration)|journal first.*|invited (talk|paper))"

AWARD_PATTERNS = [
    (r"ACM SIGSOFT Distinguished Paper Award", "ACM SIGSOFT Distinguished Paper Award"),
    (r"Most Influential Paper Award", "Most Influential Paper Award"),
    (r"Best Tool Paper Award", "Best Tool Paper Award"),
    (r"Best [Pp]aper [Aa]ward", "Best Paper Award"),
]


def norm_title(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).replace(" ", " ").strip()


def parse_bib(text):
    """Minimal BibTeX reader: good enough for a well-formed DBLP export."""
    entries = []
    for m in re.finditer(r"@(\w+)\{([^,]+),\n(.*?)\n\}\n", text, re.S):
        kind, key, body = m.group(1).lower(), m.group(2).strip(), m.group(3)
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*\{(.*?)\}(?:,\s*\n|\s*$)", body, re.S):
            fields[fm.group(1).lower()] = " ".join(fm.group(2).split())
        if "title" in fields:
            fields["title"] = fields["title"].rstrip(".")
            entries.append({"kind": kind, "key": key, **fields})
    return entries


def parse_site(path):
    doc = open(path, encoding="utf-8").read()
    start = doc.index('<section id="publications">')
    end = doc.index("</section>", start)
    body = doc[start:end]

    records, year, group = [], None, None
    token = re.compile(
        r'<h4>(?P<group>[^<]+)</h4>|<h5 class="pub-year">(?P<year>\d{4})</h5>|(?P<entry><p>.*?</p>)',
        re.S,
    )
    for m in token.finditer(body):
        if m.group("group"):
            group = strip_tags(m.group("group"))
            year = None
            continue
        if m.group("year"):
            year = int(m.group("year"))
            continue

        chunk = m.group("entry")
        text = strip_tags(chunk)
        if not text:
            continue

        links = re.findall(r'href="([^"]+)"', chunk)
        rec = {
            "group": group,
            "year": year,
            "raw": text,
            "pdf": None,
            "slides": None,
            "poster": None,
            "video": None,
            "doi": None,
            "html": None,
            "award": None,
        }
        for href in links:
            low = href.lower()
            absolute = href if href.startswith("http") else SITE + href.lstrip("./")
            if "poster" in low:
                rec["poster"] = rec["poster"] or absolute
            elif "/papers/" in low:
                rec["pdf"] = rec["pdf"] or absolute
            elif "/talks/" in low:
                rec["slides"] = rec["slides"] or absolute
            elif "youtu" in low or "video.manchester" in low:
                rec["video"] = rec["video"] or href
            elif "doi.org/" in low:
                rec["doi"] = re.sub(r"^.*?doi\.org/", "", href)
            elif rec["html"] is None and href.startswith("http"):
                rec["html"] = href  # al-folio renders a generic link as `html`

        # the bolded run is the title on every entry in this list
        bold = re.search(r"<b>(.*?)</b>", chunk, re.S)
        title = strip_tags(bold.group(1)) if bold else text
        title = re.sub(r"^[\s.]+|[\s.]+$", "", title)
        rec["title"] = title
        rec["ntitle"] = norm_title(title)

        for pat, label in AWARD_PATTERNS:
            if re.search(pat, text):
                rec["award"] = label
                break

        records.append(rec)
    return records


def main():
    index_html, dblp_bib, outdir = sys.argv[1], sys.argv[2], sys.argv[3]

    site = parse_site(index_html)
    dblp = parse_bib(open(dblp_bib, encoding="utf-8").read())

    # prefer a real venue over the arXiv shadow of the same paper
    by_title = {}
    for e in dblp:
        n = norm_title(e["title"])
        preprint = "CoRR" in e.get("journal", "")
        prev = by_title.get(n)
        if prev is None or (prev["_preprint"] and not preprint):
            e["_preprint"] = preprint
            by_title[n] = e

    matched = fuzzy = 0
    for rec in site:
        hit = by_title.get(rec["ntitle"])
        how = "exact"
        if hit is None:
            # DBLP appends venue notes the page omits, e.g. "(Competition Contribution)".
            # Only a note may differ: "Foo" and "Foo Applied to Bar" are different papers.
            for n, cand in by_title.items():
                short, long = sorted((rec["ntitle"], n), key=len)
                if len(short) < 25 or not long.startswith(short):
                    continue
                if re.fullmatch(NOTE_SUFFIX, long[len(short):].strip()):
                    hit, how = cand, "prefix"
                    break
        if hit is None:
            best, score = None, 0.0
            for n, cand in by_title.items():
                r = SequenceMatcher(None, rec["ntitle"], n).ratio()
                if r > score:
                    best, score = cand, r
            if score >= 0.92:
                hit, how = best, "fuzzy-%.2f" % score
        if hit:
            matched += 1
            fuzzy += how != "exact"
            rec["dblp"] = {k: v for k, v in hit.items() if not k.startswith("_")}
            rec["match"] = how
        else:
            rec["dblp"] = None
            rec["match"] = None

    json.dump(site, open(outdir + "/publications.json", "w"), indent=1, ensure_ascii=False)

    unmatched = [r for r in site if not r["dblp"]]
    with open(outdir + "/unmatched.txt", "w", encoding="utf-8") as fh:
        for r in unmatched:
            fh.write("%s | %s | %s\n" % (r["year"], r["group"], r["title"]))

    print("site entries       : %d" % len(site))
    print("dblp entries       : %d (%d unique titles)" % (len(dblp), len(by_title)))
    print("matched            : %d (%d exact, %d fuzzy)" % (matched, matched - fuzzy, fuzzy))
    print("needs hand-entry   : %d  -> unmatched.txt" % len(unmatched))
    for field in ("pdf", "slides", "poster", "video", "doi", "html"):
        print("with %-6s        : %d" % (field, sum(1 for r in site if r[field])))
    print("awards detected    : %d" % sum(1 for r in site if r["award"]))


if __name__ == "__main__":
    main()
