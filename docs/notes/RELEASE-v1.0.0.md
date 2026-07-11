# Release v1.0.0 — draft note + Zenodo/DOI instructions (maintainer actions)

Everything below is a **draft for the maintainer**. The Zenodo/DOI steps are Prateek's manual
actions — they are described, not performed.

**Decisions made (2026-07-06):** code = MIT, dataset = CC BY 4.0 (+ GODL-India attribution),
archive-in-deposit = **Option A** (include the frozen ~628 MB archive). → use **Route 2** below.
Before tagging: commit `LICENSE`, `LICENSE-DATA`, and the docs in this sprint.

---

## Draft GitHub release note

> ### MGNREGA Canonical Series v1.0.0
>
> The definitive, reconciled, lineage-traced record of **MGNREGA** — India's rural employment
> guarantee scheme — assembled from the full offline data.gov.in archive into one canonical series,
> **FY 2006-07 → FY 2026-27**.
>
> **What's inside (`dist/v1.0/`)**
> - `state_annual_series` — 4,219 facts, 8 metrics, FY 2010-11 → 2026-27 (CSV + Parquet)
> - `national_annual_series` — 148 facts, FY 2006-07 → 2026-27 (CSV + Parquet)
> - `district_flagship` — 57,181 flagship-era facts, single-grain district-annual (incl. complete-FY wage rate)
> - `lineage.jsonl` — 61,548 per-fact provenance records, joined on `fact_id`
>
> Every column and metric is defined in `DATA_DICTIONARY.md`. The series is built deterministically
> and offline; repeated runs are byte-identical (`REPRODUCIBILITY.md`).
>
> **Highlights of the reconciliation**
> - Person-days corrected from cumulative-YTD to financial-year-final (naive monthly summing inflates
>   badly — e.g. 6.31× on Goa FY 2022-23).
> - Geography anchored to LGD codes by name-join (no code crosswalk exists); unresolvable rows are
>   quarantined with a reason, never dropped.
> - After separating period-mismatch and one-publisher re-issues (edition supersession, 470 cells),
>   **9** genuine cross-publisher disagreements remain in the pre-2018 series (4 in `households_employed`,
>   5 in `total_expenditure`) — each published with its rejected value and full lineage.
>
> **Honest limitations** and the full coverage account are in `DATA_DICTIONARY.md` (§8).
>
> **Cite:** see `CITATION.cff`; a DOI is minted with this release via Zenodo.
>
> **License:** see `LICENSE` (code) and the dataset attribution statement.
>
> Built with an agentic workflow (human architect/reviewer + Claude Code execution under a strict
> test/type/lint gate); the commit history reflects that process.

---

## Zenodo → DOI: step-by-step (maintainer)

Two routes, depending on the archive-in-deposit decision (`REPRODUCIBILITY.md`):

### Route 1 — GitHub↔Zenodo webhook (simplest; deposits the committed repo only)
Use this if depositing **code + committed docs** (Option B), since the webhook captures only the
git source tarball — it does **not** include `data/archive/` or `dist/` (both gitignored).

1. Sign in at https://zenodo.org with the GitHub account (`Prateek718`).
2. Zenodo → **Account → GitHub**; flip the toggle **ON** for `Prateek718/Data-Platform`.
3. Confirm `CITATION.cff` is committed on the default branch (drives the Zenodo metadata).
4. On GitHub: **Releases → Draft a new release**, tag **`v1.0.0`** on `main`, title
   "MGNREGA Canonical Series v1.0.0", paste the release note above, **Publish**.
5. Zenodo auto-archives the tagged source and mints two DOIs: a **version DOI** (this release) and a
   **concept DOI** (always-latest). Copy the version DOI.
6. Add the DOI to `CITATION.cff` (`doi:` / `identifiers:`) and a DOI badge to `README.md`; commit.

### Route 2 — Manual Zenodo deposit (required to include the ~628 MB raw archive + outputs, Option A)
Use this if depositing the **frozen archive + `dist/` outputs + code** for full reproducibility.

1. Sign in at https://zenodo.org → **New upload**.
2. Upload: (a) a source zip of the repo at the `v1.0.0` tag (`git archive`), (b) `dist/v1.0/`
   (the outputs), and (c) the `data/archive/` snapshot (~628 MB; within Zenodo's 50 GB limit). Include
   the GODL-India attribution statement (`LICENSE-PROPOSAL.md`) at the deposit root.
3. Fill metadata from `CITATION.cff` (title, author, version 1.0.0, keywords); set the license once
   decided; Upload type = Dataset.
4. **Reserve DOI** (Zenodo shows it before publishing), then **Publish** to mint it.
5. Add the DOI to `CITATION.cff` + a `README.md` badge; also create the matching GitHub release
   (tag `v1.0.0`, same note) so the repo and deposit line up.

> Prerequisite for either route: the two decisions in `LICENSE-PROPOSAL.md` and `REPRODUCIBILITY.md`
> are made, and `LICENSE` (+ `LICENSE-DATA` if CC BY 4.0) is committed.
