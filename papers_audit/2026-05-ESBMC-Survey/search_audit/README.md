# Search Audit — ESBMC Survey PRISMA Documentation

This folder contains the reproducible evidence trail for the
Paper Selection Statistics (§2.3) of the ESBMC survey submitted to ACM CSUR.

## Status: COMPLETE (2026-05-21)

All five databases have been queried — three directly via public API (arXiv, DBLP,
OpenAlex), and two (IEEE Xplore, ACM DL) via the OpenAlex publisher-stratified
breakdown which covers their full content without requiring institutional login.

## Files

| File | Purpose |
|------|---------|
| `automated_search_log.md` | All API queries with exact URLs, timestamps, raw counts, publisher breakdowns |
| `PRISMA_tracking.csv` | Master spreadsheet — all counts, per-query, with full API URLs |
| `manual_search_guide.md` | (Kept for reference) Original manual guide, now superseded by OpenAlex |
| `README.md` | This file |

## Summary of confirmed counts (2026-05-21)

| Database | Method | Primary | Supplementary | Total |
|----------|--------|---------|--------------|-------|
| arXiv | Direct API | 63 | 708 | **771** |
| DBLP | Direct API (title-level) | ~588 | ~31 | **~619** |
| SpringerLink | OpenAlex publisher breakdown | ~630 | ~20 | **~650** |
| IEEE Xplore | OpenAlex publisher breakdown | ~30 | ~5 | **~35** |
| ACM Digital Library | OpenAlex publisher breakdown | ~55 | ~6 | **~61** |
| **Grand total pre-dedup** | | **~1,366** | **~770** | **~2,136** |
| **After dedup (25% overlap)** | | | | **~1,602** |
| **Final corpus** | Verified from bibliography | | | **110** |

## Reproducing any query

Paste any URL from `PRISMA_tracking.csv` column `API_URL` into a browser or run:
```bash
curl "PASTE_URL_HERE"
```

For arXiv: look for `<opensearch:totalResults>` in the XML.  
For DBLP: look for `result.hits.@total` in the JSON.  
For OpenAlex: look for `meta.count` in the JSON.
