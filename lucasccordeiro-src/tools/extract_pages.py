#!/usr/bin/env python3
"""Generate the grants, awards and supervisions pages from the legacy site.

Each of those sections is a flat run of <p> entries (with <h4> subheadings in
supervisions), so they convert to markdown directly. Kept as a script rather
than hand-copied so the pages can be regenerated if the old page changes.

Usage: extract_pages.py <legacy/index.html> <_pages dir>
"""

import html
import os
import re
import sys

SITE = "https://ssvlab.github.io/lucasccordeiro/"

PAGES = [
    ("grants", "grants", 3,
     "Research funding secured as Principal or Co-Investigator, most recent first."),
    ("awards", "awards", 4,
     "Awards and competition medals for our work on software verification and testing."),
    ("supervisions", "supervisions", 5,
     "Doctoral, masters and undergraduate students supervised, and their theses."),
    ("tools", "tools", 7,
     "Open-source verification and testing tools developed with my students and collaborators."),
    ("courses", "courses", 8,
     "Course units created and delivered at Manchester and the Federal University of Amazonas."),
]


def to_markdown(fragment):
    # links are relative to the legacy page, which is not where these pages live
    fragment = re.sub(r'href="\./', 'href="%s' % SITE, fragment)
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


def render_tools(body):
    """Each tool is an <a> wrapping a <figure> with a name or logo and a caption."""
    out = []
    for m in re.finditer(r'<a href="([^"]+)"[^>]*>\s*<figure.*?</figure>', body, re.S):
        block, url = m.group(0), m.group(1)
        logo = re.search(r'<img[^>]*src="([^"]+)"', block)
        caption = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", block, re.S)
        name = re.search(r"<span[^>]*>(.*?)</span>", block, re.S)
        title = to_markdown(name.group(1)) if name else ""
        if not title and caption:
            # logo-only tools name themselves in the caption's first bold run
            bold = re.search(r"<b>(.*?)</b>", caption.group(1), re.S)
            title = to_markdown(bold.group(1)) if bold else ""
        if not title:
            alt = re.search(r'alt="([^"]+)"', block)
            title = alt.group(1) if alt else url
        out.append("## [%s](%s)\n" % (title, url))
        if logo:
            out.append("![%s](%s){: width=\"180\" }\n" % (title, logo.group(1)))
        if caption:
            out.append(to_markdown(caption.group(1)) + "\n")
    return "\n".join(out) + "\n" + EXTRA_TOOLS


# listed under "Selected Tools" in the legacy sidebar rather than the Tools section
EXTRA_TOOLS = """
## [JBMC](http://www.cprover.org/jbmc/)

**JBMC** is a bounded model checker for Java bytecode, built on the CProver framework. It verifies
memory safety, exceptions and user-specified assertions, and takes part in the Java track of the
international competition on software verification.
"""


def render_courses(body):
    out = []
    for m in re.finditer(r"<li>(.*?)</li>", body, re.S):
        text = to_markdown(m.group(1))
        if text:
            out.append("- %s" % text)
    return "\n".join(out)


def render(body, kind):
    if kind == "tools":
        return render_tools(body)
    if kind == "courses":
        return render_courses(body)
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
