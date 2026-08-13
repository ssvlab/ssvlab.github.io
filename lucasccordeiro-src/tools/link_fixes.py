"""Repairs for link targets on the legacy page that no longer resolve.

Checked with tools/check_links.py. REPLACE maps a dead URL to a verified
working equivalent; DROP lists URLs with no equivalent, whose text is kept
but no longer hyperlinked. Both are applied by the extractors, so a rerun
never reintroduces a dead link.
"""

REPLACE = {
    # domain no longer resolves; the project pages live on the lab's site
    "http://dsverifier.org/": "https://ssvlab.github.io/dsverifier/",
    "http://dsverifier.org": "https://ssvlab.github.io/dsverifier/",
    # malformed: a video id used as a path
    "https://www.youtube.com/p71ysF9S460": "https://www.youtube.com/watch?v=p71ysF9S460",
    # publisher short link retired; DOI confirmed against Crossref
    "http://ietdl.org/t/D7Q6k": "https://doi.org/10.1049/iet-cps.2018.5006",
    # journal host no longer resolves; DOI confirmed against Crossref
    "http://www.revistaieeela.pea.usp.br/issues/vol15issue10Oct.2017/15TLA10_19CostaLucenaFilho.pdf":
        "https://doi.org/10.1109/TLA.2017.8071238",
    # EPSRC retired Grants on the Web in favour of Gateway to Research
    "https://gow.epsrc.ukri.org/NGBOViewGrant.aspx?GrantRef=EP/T026995/1":
        "https://gtr.ukri.org/projects?ref=EP%2FT026995%2F1",
    "https://gow.epsrc.ukri.org/NGBOViewGrant.aspx?GrantRef=EP/V000497/1":
        "https://gtr.ukri.org/projects?ref=EP%2FV000497%2F1",
}

DROP = {
    # 404: EAGE reorganised its archive and the 2004 paper has no stable URL
    "http://earthdoc.eage.org/publication/publicationdetails/?publication=47542",
    # 404: the UKRI announcement was removed
    "https://www.ukri.org/news/rd-investments-spearhead-push-to-block-cyber-security-attacks/",
    # the 2019 syllabus host was retired and the unit has no public page
    "http://syllabus.cs.manchester.ac.uk/ugt/2019/COMP26120/",
    # the old UFAM personal page is gone and the deck is not archived locally
    "http://home.ufam.edu.br/lucascordeiro/talks/fie2016_slides.pdf",
}


def fix(url):
    """Return the working URL, or None when the link should be dropped."""
    if url in DROP:
        return None
    return REPLACE.get(url, url)


# The legacy page attached one filename to two different papers. Keyed by
# title because the wrong URL is also the right URL for the other entry.
PDF_BY_TITLE = {
    # tr2018.pdf is the IEEE Trans. Reliability paper; Sim3Tanks is IEEE Access
    "Sim3Tanks: A Benchmark Model Simulator for Process Control and Monitoring":
        "https://ssvlab.github.io/lucasccordeiro/papers/access2018.pdf",
}


def fix_pdf(title, url):
    """Return the PDF that belongs to this entry."""
    return PDF_BY_TITLE.get(title.strip(), url)
