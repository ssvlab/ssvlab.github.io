/**
 * ESBMC DASHBOARD DATA
 * ─────────────────────────────────────────────
 * This is the ONLY file you need to edit each week.
 * Update the numbers below and refresh index.html.
 *
 * Last updated: 2026-05-29
 */

const ESBMC_DATA = {

  /* ── Top-line KPIs ─────────────────────────────── */
  lastUpdated:  "29 May 2026",
  totalPapers:  62,
  totalAwards:  43,          // SV-COMP + Test-Comp combined
  svcompAwards: 35,
  testcompAwards: 8,
  goldMedals:   4,
  yearsEntered: 13,          // years in competition since 2012
  languages:    9,
  fundingLabel: "£9.3M+",   // display string
  accelerationPct: 88,       // % increase vs 2009–2017 pace

  /* ── Papers per year (add a new entry each time) ── */
  papersByYear: {
    2009: 1, 2010: 2, 2011: 2, 2012: 2, 2013: 2,
    2014: 3, 2015: 5, 2016: 6, 2017: 5, 2018: 5,
    2019: 2, 2020: 2, 2021: 3, 2022: 8, 2023: 7,
    2024: 5, 2025: 3
  },

  /* ── Research topics ───────────────────────────── */
  topics: [
    ["BMC core / verification",    26],
    ["Fuzzing & hybrid",           12],
    ["Language front-ends",        11],
    ["Digital controllers",         9],
    ["Concurrent programs",         8],
    ["AI / LLM integration",        7],
    ["Smart contracts",             6],
    ["Test generation",             5]
  ],

  /* ── Languages ─────────────────────────────────── */
  langColors: {
    C:        "#378ADD",
    "C++":    "#1D9E75",
    Python:   "#7F77DD",
    Kotlin:   "#D4537E",
    Rust:     "#D85A30",
    Solidity: "#BA7517",
    CUDA:     "#888780",
    CHERI:    "#0F6E56"
  },
  langCounts: { C: 58, "C++": 8, CUDA: 2, Solidity: 2, Kotlin: 1, Python: 1, CHERI: 1, Rust: 1 },

  /* ── Key milestones (add new ones at the bottom) ── */
  milestones: [
    { year: 2009, text: "First publication at ASE" },
    { year: 2012, text: "SV-COMP debut — Gold Medal" },
    { year: 2018, text: "ESBMC 5.0 — industrial grade" },
    { year: 2021, text: "FuSeBMC fuzzing platform born" },
    { year: 2022, text: "Solidity + Kotlin front-ends added" },
    { year: 2024, text: "LLM-guided invariant inference" }
  ]

};
