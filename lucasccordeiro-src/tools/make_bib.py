#!/usr/bin/env python3
"""Turn publications.json into _bibliography/papers.bib for jekyll-scholar.

DBLP metadata where we have it, the legacy page's own text where we don't.
Local PDFs, slide decks and DOIs are carried over as al-folio fields so no
link on the current site is lost.

Usage: make_bib.py <publications.json> <out.bib> [overrides.json]
"""

import json
import os
import re
import sys
import unicodedata

# jekyll-scholar reads these; al-folio renders them as buttons on each entry
CARRIED = ["pdf", "slides", "poster", "video", "doi", "html", "award"]

DROP_DBLP = {"key", "kind", "biburl", "bibsource", "timestamp", "ee", "_preprint"}

VENUE_ABBR = [
    (r"\bICSE\b|International Conference on Software Engineering", "ICSE"),
    (r"\bTACAS\b|Tools and Algorithms for the Construction", "TACAS"),
    (r"\bFASE\b|Fundamental Approaches to Software Engineering", "FASE"),
    (r"\bASE\b|Automated Software Engineering", "ASE"),
    (r"\bISSTA\b|Software Testing and Analysis", "ISSTA"),
    (r"\bFSE\b|Foundations of Software Engineering|ESEC/FSE", "FSE"),
    (r"Transactions on Software Engineering", "TSE"),
    (r"Transactions on Reliability", "TR"),
    (r"Transactions on Computers", "TC"),
    (r"\bCAV\b|Computer Aided Verification", "CAV"),
    (r"\bSAS\b|Static Analysis Symposium", "SAS"),
    (r"Automation of Software Test\b", "AST"),
    (r"Requirements Engineering Conference", "RE"),
    (r"\bESOP\b|European Symposium on Programming", "ESOP"),
    (r"Empirical Software Engineering", "EMSE"),
    (r"Science of Computer Programming", "SCP"),
    (r"Software Testing, Verification and Reliability", "STVR"),
    (r"Software Tools for Technology Transfer", "STTT"),
    (r"Consumer Electronics", "ICCE"),
]


def cite_key(rec, seen):
    surname = "cordeiro"
    author = (rec.get("dblp") or {}).get("author", "")
    if author:
        first = author.split(" and ")[0]
        surname = first.split(",")[0] if "," in first else first.split()[-1]
    surname = re.sub(r"[^a-z]", "", strip_accents(surname).lower()) or "anon"
    word = next(
        (w for w in re.findall(r"[A-Za-z]{4,}", rec["title"]) if w.lower() not in STOP),
        "paper",
    )
    base = "%s%s%s" % (surname, rec.get("year") or "nd", word.lower())
    key, n = base, 1
    while key in seen:
        n += 1
        key = "%s%d" % (base, n)
    seen.add(key)
    return key


STOP = {"using", "with", "from", "into", "that", "this", "their", "based", "towards", "toward"}


def strip_accents(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def venue_abbr(text):
    text = text.split("@")[0]  # "AST@ICSE" is AST, hosted by ICSE
    for pat, abbr in VENUE_ABBR:
        if re.search(pat, text, re.I):
            return abbr
    return None


def guess_venue(rec):
    """When DBLP has nothing, recover the venue from the page's own prose."""
    raw = rec["raw"]
    tail = raw.split(rec["title"], 1)[-1] if rec["title"] in raw else raw
    m = re.search(r"\bIn\s+(?:the\s+)?([^.]{6,140})", tail)
    venue = m.group(1) if m else tail[:140]
    venue = re.sub(r"\s*\[(Presentation|Youtube|Poster|here)\]\s*", " ", venue, flags=re.I)
    venue = re.sub(r"\s*\bDOI\b\s*$", "", venue.strip(" .,;"))
    venue = re.sub(r"[,\s]+(19|20)\d{2}\s*$", "", venue)
    return " ".join(venue.split())


def authors_from_raw(rec):
    """The page writes 'Surname, X., Surname, Y.' ahead of the title."""
    head = rec["raw"].split(rec["title"])[0] if rec["title"] in rec["raw"] else ""
    head = head.strip(" .:")
    if not head or len(head) > 400:
        return None
    parts = [p.strip(" .") for p in re.split(r",(?![^(]*\))", head) if p.strip(" .")]
    if not parts:
        return None

    # "J.T.D. Alkmin, A.C. de Melo Junior": each comma already separates a
    # whole name, so pairing them surname-first would run them together
    initials_first = sum(bool(re.match(r"^(?:[A-Z]\.){2,}\s*[A-Z]", p)) for p in parts)
    if initials_first >= max(2, len(parts) // 2):
        # a stray surname-first name in the run leaves its initials orphaned
        merged = []
        for p in parts:
            if merged and re.fullmatch(r"(?:[A-Z]\.?\s*){1,4}", p):
                merged[-1] = "%s, %s" % (merged[-1], p)
            else:
                merged.append(p)
        return " and ".join(merged)

    names, buf = [], []
    for p in parts:
        buf.append(p)
        if re.fullmatch(r"(?:[A-Z]\.?\s*)+|[A-Z][a-z]+", p) and len(buf) >= 2:
            names.append("%s, %s" % (buf[0], " ".join(buf[1:])))
            buf = []
    if buf:
        names.append(" ".join(buf))
    return " and ".join(n for n in names if n) or None


def emit(rec, key):
    d = rec.get("dblp") or {}
    kind = d.get("kind")
    if not kind:
        group = (rec.get("group") or "").lower()
        kind = {"journals": "article", "theses": "phdthesis"}.get(group, "inproceedings")
        if "book" in group:
            kind = "book" if "edited" in group else "incollection"

    thesis_type = None
    if kind == "phdthesis":
        if re.search(r"\bB\.?Sc|Bachelor", rec["raw"], re.I):
            kind, thesis_type = "mastersthesis", "Bachelor's thesis"
        elif re.search(r"\bM\.?Sc|Master", rec["raw"], re.I):
            kind = "mastersthesis"

    fields = {k: v for k, v in d.items() if k not in DROP_DBLP}
    fields.pop("title", None)
    fields["title"] = re.sub(r"[{}]", "", d.get("title") or rec["title"]).rstrip(".")
    if not fields.get("author"):
        fields["author"] = authors_from_raw(rec) or "Cordeiro, Lucas C."
    if not fields.get("year") and rec.get("year"):
        fields["year"] = str(rec["year"])
    over = rec.get("_over") or {}
    for k in ("pages", "volume", "number", "year"):
        if over.get(k) and not fields.get(k):
            fields[k] = over[k]
    if kind.endswith("thesis"):
        m = re.search(r"(?:Thesis|Dissertation),\s*([^,]+?),\s*((?:19|20)\d{2})", rec["raw"])
        if m:
            fields["school"], fields["year"] = m.group(1).strip(), m.group(2)
        fields.pop("booktitle", None)
        if thesis_type:
            fields["type"] = thesis_type
    elif not (fields.get("journal") or fields.get("booktitle")):
        venue = over.get("venue") or guess_venue(rec)
        fields["journal" if kind == "article" else "booktitle"] = venue

    for f in CARRIED:
        if rec.get(f):
            fields[f] = rec[f]
    abbr = venue_abbr(fields.get("journal") or fields.get("booktitle") or "")
    if abbr:
        fields["abbr"] = abbr
    fields["bibtex_show"] = "true"

    order = ["abbr", "title", "author", "journal", "booktitle", "school", "type", "volume", "number",
             "pages", "year", "publisher", "series", "doi", "html", "pdf", "slides", "poster",
             "video", "award", "bibtex_show"]
    keys = [k for k in order if k in fields] + [k for k in sorted(fields) if k not in order]
    width = max(len(k) for k in keys)
    body = ",\n".join("  %-*s = {%s}" % (width, k, fields[k]) for k in keys)
    return "@%s{%s,\n%s\n}\n" % (kind, key, body)


def apply_overrides(rec, over):
    """CV-recovered venue/pages/volume/year for entries DBLP does not index."""
    fields = over.get(rec["title"])
    if not fields:
        return
    rec.setdefault("_over", {}).update(fields)


def main():
    recs = json.load(open(sys.argv[1], encoding="utf-8"))
    over = json.load(open(sys.argv[3], encoding="utf-8")) if len(sys.argv) > 3 else {}
    for rec in recs:
        apply_overrides(rec, over)
        if not rec.get("year"):
            m = re.search(r"\b(19|20)\d{2}\b", rec["raw"])
            if m:
                rec["year"] = int(m.group(0))
    recs.sort(key=lambda r: (-(r.get("year") or 0), r["title"]))

    seen, out = set(), ["---\n---\n"]
    for rec in recs:
        out.append(emit(rec, cite_key(rec, seen)))

    extra = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extra.bib")
    if os.path.exists(extra):
        body = open(extra, encoding="utf-8").read()
        out.append(body)
        print("extra entries   : %d" % body.count("\n@"))

    open(sys.argv[2], "w", encoding="utf-8").write("\n".join(out))
    print("entries written : %d" % len(recs))
    print("with pdf        : %d" % sum(1 for r in recs if r.get("pdf")))
    print("with slides     : %d" % sum(1 for r in recs if r.get("slides")))
    print("with doi        : %d" % sum(1 for r in recs if r.get("doi")))
    print("from dblp       : %d" % sum(1 for r in recs if r.get("dblp")))


if __name__ == "__main__":
    main()
