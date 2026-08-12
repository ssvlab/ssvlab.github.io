#!/usr/bin/env python3
"""Generate the grants, awards and supervisions pages from the legacy site.

Each of those sections is a flat run of <p> entries (with <h4> subheadings in
supervisions), so they convert to markdown directly. Kept as a script rather
than hand-copied so the pages can be regenerated if the old page changes.

Usage: extract_pages.py <index.html> <_pages dir>
"""

import html
import os
import re
import sys

PAGES = [
    ("grants", "grants", 3,
     "Research funding secured as Principal or Co-Investigator, most recent first."),
    ("awards", "awards", 4,
     "Awards and competition medals for our work on software verification and testing."),
    ("supervisions", "supervisions", 5,
     "Doctoral, masters and undergraduate students supervised, and their theses."),
]


def to_markdown(fragment):
    md = re.sub(r'<a href="([^"]+)"\s*>(.*?)</a>',
                lambda m: "[%s](%s)" % (re.sub(r"<[^>]+>", "", m.group(2)).strip(), m.group(1)),
                fragment, flags=re.S)
    # strip space inside the bold tags only: the space outside them is real text
    md = re.sub(r"<b>\s*", "**", md)
    md = re.sub(r"\s*</b>", "**", md)
    md = re.sub(r"<[^>]+>", "", md)
    md = html.unescape(md)
    md = md.replace("****", "")               # empty bold left by stripped tags
    return " ".join(md.split())


def section(doc, name):
    start = doc.index('<section id="%s">' % name)
    return doc[start:doc.index("</section>", start)]


def render(body, kind):
    """One markdown line per entry, keeping any <h4> grouping."""
    out = []
    # several <p> in the supervisions list are never closed, so an entry runs
    # until the next paragraph or heading rather than to a matching </p>
    token = re.compile(
        r"<h4>(?P<head>[^<]+)</h4>|<p>(?P<entry>.*?)(?=<p>|</p>|<h4>|<br>|\Z)", re.S)
    for m in token.finditer(body):
        if m.group("head"):
            out.append("\n## %s\n" % to_markdown(m.group("head")))
            continue
        text = to_markdown(m.group("entry") or "")
        if not text:
            continue
        # entries are already numbered on the legacy page; keep the number as
        # plain text so markdown does not renumber them
        numbered = re.match(r"^(\d+)\.\s*(.+)$", text)
        if numbered:
            out.append("%s. %s" % (numbered.group(1), numbered.group(2)))
        elif kind == "supervisions":
            out.append(text)
        else:
            out.append("*%s*\n" % text)  # the leading prose paragraph
    return "\n".join(out)


def main():
    doc = open(sys.argv[1], encoding="utf-8").read()
    outdir = sys.argv[2]

    for sec, title, order, description in PAGES:
        body = render(section(doc, sec), sec)
        front = ("---\nlayout: page\npermalink: /%s/\ntitle: %s\nnav: true\n"
                 "nav_order: %d\ndescription: %s\n---\n\n" % (sec, title, order, description))
        with open(os.path.join(outdir, "%s.md" % sec), "w", encoding="utf-8") as fh:
            fh.write(front + body.strip() + "\n")
        print("%-14s %3d entries" % (title, body.count("\n")))


if __name__ == "__main__":
    main()
