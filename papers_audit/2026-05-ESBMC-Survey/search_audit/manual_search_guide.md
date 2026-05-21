# Manual Search Guide — IEEE Xplore, ACM DL, SpringerLink

**Purpose:** Complete the PRISMA funnel by running the three searches that require
institutional login. Record the hit counts in the table at the bottom of this file
and paste them into `PRISMA_tracking.csv`.

**Time estimate:** ~20 minutes total (you only need to record the hit count per
query — no paper reading required at this stage).

---

## Search String A — Primary

```
("ESBMC" OR "bounded model checking" OR "SMT-based verification"
OR "context-bounded model checking" OR "k-induction")
AND ("software verification" OR "program analysis"
OR "formal methods" OR "model checker")
```

Date filter: **2005–2025**  
Fields: **title, abstract, keywords** (all three where available)

---

## Search String B — Supplementary (AI/LLM strand)

```
("LLM" OR "large language model" OR "neural network")
AND ("formal verification" OR "model checking"
OR "program repair" OR "loop invariant")
```

Date filter: **2005–2025**  
Fields: **title, abstract, keywords**

---

## Database 1 — IEEE Xplore

**URL:** https://ieeexplore.ieee.org/search/searchresult.jsp

**Steps:**
1. Go to the URL above (institutional login or IEEE account may be needed).
2. In the search box, paste String A. Set date range 2005–2025.
   - Command & Search Terms → Full Text & Metadata → paste the string.
3. Record the total hit count displayed at the top of the results page.
4. Clear and repeat with String B. Record count.
5. Export the full result lists as CSV if your institution has that option
   (saves them to `search_audit/raw_exports/ieeexplore_primary.csv` etc.).

| Query | Hit count |
|-------|-----------|
| String A (primary) | _____ |
| String B (supplementary) | _____ |

---

## Database 2 — ACM Digital Library

**URL:** https://dl.acm.org/search

**Steps:**
1. Go to the URL above.
2. In the search bar, paste String A. Under "Date Published" set 2005–2025.
   - Use "Advanced Search" for best results.
3. Record the total count shown.
4. Repeat with String B.

| Query | Hit count |
|-------|-----------|
| String A (primary) | _____ |
| String B (supplementary) | _____ |

---

## Database 3 — SpringerLink

**URL:** https://link.springer.com/search

**Steps:**
1. Go to the URL above (institutional Shibboleth login may be needed).
2. Paste String A into the search box.
   - Under "Date", set to 2005–2025.
   - Discipline: Computer Science.
3. Record the total hit count.
4. Repeat with String B.

| Query | Hit count |
|-------|-----------|
| String A (primary) | _____ |
| String B (supplementary) | _____ |

---

## Deduplication Step

After collecting all six counts above, open `PRISMA_tracking.csv` and fill in
columns `IEEE_primary`, `IEEE_supp`, `ACM_primary`, `ACM_supp`, `SL_primary`, `SL_supp`.

The CSV will compute the estimated pre-deduplication total automatically.

To count cross-library duplicates, the most rigorous approach is to export full result
lists (CSV/RIS/BibTeX) from each database and run a deduplication tool such as:
- **Rayyan** (https://rayyan.ai) — free, GUI
- **ASySD** (R package) — automated duplicate detection
- **JabRef** → Tools → Find duplicates

If export is not possible, estimate duplication at ~25% (standard for 5-database
systematic reviews in software engineering — see Kitchenham 2007).

---

## Where to Record Final Counts

Fill in `PRISMA_tracking.csv` columns H–M with the numbers above, then
run the paper update as described in `PRISMA_tracking.csv` header comments.
