# Quarantine Transparency Report — Stage 3.5 Geography Resolution

## 1. What this document is

The canonical MGNREGA dataset takes rows from many separately-published government
datasets and resolves each one to a **current official geography** — a state, union
territory, or district as it exists today in the **Local Government Directory (LGD)**, the
Government of India's authoritative register of administrative areas. Every canonical fact
is anchored to an LGD code so that figures from different sources can be compared on the
same map.

Some source rows cannot be resolved to a current LGD geography honestly. Rather than drop
them silently or force them onto a code that does not fit, those rows are **quarantined** —
set aside and kept, each tagged with a specific machine-readable reason and its full
origin (which dataset, which period, the original label). "Quarantine" here means
*preserved-with-a-reason*, not deleted.

This document is the complete, honest account of those quarantined rows: how many there
are, why each group was set aside, and the single principle behind every decision —
**never invent a geography the source does not support; quarantine over discard.**

**Scope.** The tables below cover the **107 archived datasets wired through this stage**
(the historical and cross-source datasets newly carried into the canonical series). The
main national series (district figures reported monthly) and the datasets set aside for
other reasons are accounted for separately in section 6, so that all 130 discovered
datasets are traceable. All numbers are computed fresh from the resolution pipeline over
the committed data, not transcribed.

## 2. Summary

Across the 107 wired datasets:

| Outcome | Rows | Share |
|---|---|---|
| Resolved to a current LGD geography | **23,843** | 93.5% |
| Quarantined (preserved with a reason) | **1,644** | 6.5% |
| **Total** | **25,487** | 100% |

So about **1 row in 15** could not be placed on the current map — and every one of those is
itemized below. The quarantine splits into two machine-readable reasons:

| Reason | Rows | Distinct datasets |
|---|---|---|
| `unresolved_geography` — no current geography matched | 331 | 64 |
| `historical_geography_not_in_current_lgd` — a real past place, since reorganized away | 1,313 | 60 |

The 331 `unresolved_geography` rows break down further into **322 non-place artifacts** and
**9 genuinely-ambiguous rows held rather than guessed** (explained below and listed in full
in section 4).

## 3. The three reasons, explained

### 3a. Non-place artifacts — 322 rows

These are rows whose "geography" was never a real place, so setting them aside is correct,
not a coverage gap:

- **Subtotal / roll-up rows** — a `Total` line at the bottom of a state table (189 rows).
  Resolving it as if it were a place would double-count every real state above it.
- **Blank or aggregate labels inside state tables** — a missing/empty label recorded as
  `None` (115 rows), or the word `National` / `National Average` (8 rows) sitting in the
  state-name column. These are summary lines, not states.
- **Stray numeric code-as-name** — a serial number or code (e.g. `30`, `13`, `27`) that
  landed in the state-name column instead of a name, from a source formatting slip
  (10 rows).

None of these denote a location, so none can — or should — resolve to an LGD code.

### 3b. Historical / reorganized entities — 1,313 rows

These were **real places at the time the record was written**, but they are absent from
the *current* LGD because India's administrative map changed — areas were split, merged, or
renamed. The two clear cases here:

- **Dadra & Nagar Haveli and Daman & Diu** — until 2020 these were two separate union
  territories (a union territory, or "UT", is a centrally-administered region). On 26
  January 2020 they merged into a single UT. Rows from before the merger name the two
  *separate* old territories, which no longer exist as distinct entities in the current
  directory (1,273 rows across the historical series).
- **Sikkim's `East` / `North` / `South` / `West` districts** — renamed in 2021 (to Gangtok,
  Mangan, Namchi, and Gyalshing). The old directional names are gone from current LGD
  (40 rows).

Why these are **not** mapped onto a current code: when an old area was split or merged, the
source gives no basis to divide its figures across the new areas (or to attribute a merged
figure back to one old part). Any such mapping would be a number the source never
published — a fabrication. The same integrity rule that governs the whole dataset — never
invent a value or a geography the source does not support — requires holding these instead.
They are preserved with full origin lineage and **could be resolved in future if a
period-accurate historical geography reference (an "era gazetteer": a record of which
places existed in which years, with official successor relationships) is added** to the
platform.

### 3c. Genuinely ambiguous, held rather than guessed — 9 rows

A small residual was held because resolving it would require a guess the data does not
support. Holding a genuinely ambiguous row is a feature of a trustworthy dataset, not a
shortfall — it keeps the row visible and honest instead of quietly picking an answer.

- **`ANDAMAN &` and `NICOBAR` as two rows** (a wage-comparison table, 2016-17) — the single
  territory "Andaman & Nicobar" appears split across two rows carrying **different wage
  values**. Merging them into one Andaman & Nicobar fact would either duplicate the
  territory or force an arbitrary choice between the two values, so both are held (4 rows).
- **`HIMACHAL PRADESH - Schedule Areas` and `- Non-Schedule Areas`** (same table, 2016-17) —
  Himachal Pradesh is split into two internal partitions with **different wage values**.
  The geography of both is simply Himachal Pradesh, so mapping both would create two
  conflicting Himachal facts for the same year; held rather than duplicate the state
  (4 rows).
- **`Dada and Nagar Haveli`** (2019-20) — a misspelling of the *standalone* Dadra & Nagar
  Haveli, appearing in the financial year that straddles the 2020 merger. Because it names
  the old standalone territory in the boundary year, whether it means the pre-merger area
  or the merged UT is genuinely unclear, so it is held (1 row).

## 4. Full residual name listing

Every distinct unresolved geography name in the 331-row residual, with its row count and a
tag — `artifact` (never a place) or `held-ambiguous` (a real-place question held rather than
guessed). This is the complete list, not a sample.

| Unresolved name | Rows | Tag |
|---|---|---|
| `Total` | 189 | artifact |
| `None` (blank/missing label) | 115 | artifact |
| `National` | 7 | artifact |
| `30` | 2 | artifact |
| `ANDAMAN &` | 2 | held-ambiguous |
| `HIMACHAL PRADESH - Non-Schedule Areas` | 2 | held-ambiguous |
| `HIMACHAL PRADESH - Schedule Areas` | 2 | held-ambiguous |
| `NICOBAR` | 2 | held-ambiguous |
| `13` | 1 | artifact |
| `24` | 1 | artifact |
| `27` | 1 | artifact |
| `33` | 1 | artifact |
| `34` | 1 | artifact |
| `51` | 1 | artifact |
| `75` | 1 | artifact |
| `9` | 1 | artifact |
| `National Average` | 1 | artifact |
| `Dada and Nagar Haveli` | 1 | held-ambiguous |

Totals: 322 `artifact` + 9 `held-ambiguous` = 331 `unresolved_geography` rows.

## 5. What this means for a data consumer

The quarantined rows are **not silently missing**. Every one is recorded here with a reason
and retained in the pipeline with its full origin, so a researcher can see precisely what
the canonical series covers and what it deliberately sets aside — and why. Coverage is
honestly uneven: the deep historical years lean on datasets with old place-names and
reorganized boundaries, and some source rows are summary lines or ambiguous fragments that
no honest rule can place. This document is how that unevenness is made **traceable rather
than hidden**. A figure is either anchored to a real current geography, or it is here, with
its reason.

### Status of historical-geography handling (stated plainly)

Historical entities that are absent from the current LGD are **labelled and quarantined via
an explicit, hand-reviewed list** of known reorganizations (the pre-2020 standalone Dadra &
Nagar Haveli / Daman & Diu, and the renamed Sikkim districts). **Automatic detection of
arbitrary historical place-names is not implemented** — it awaits a period-accurate
historical geography reference. Names outside the reviewed list that fail to resolve are
kept under the neutral `unresolved_geography` reason rather than guessed to be historical.

## 6. Whole-archive accounting

For completeness, all **130 discovered datasets** are accounted for:

| Group | Datasets | Notes |
|---|---|---|
| Main national series (districts, reported monthly) | 1 | Resolved separately: 69,188 of 69,407 rows resolved (99.68%); 219 quarantined as unresolved geography. |
| Wired archived datasets (this report) | 107 | 23,843 rows resolved, 1,644 quarantined (sections 2–4). |
| Deferred datasets | 22 | Set aside whole, each with a reason, because their layout isn't yet supported: 11 give no usable time period (no year column and no year in the title), 6 report districts without naming the state (so a district can't be pinned to the right state), 3 name their single state only in the title, 1 has no identified publisher, and 1 could not be downloaded (no file). |

The 99.68% above is measured per row (69,188 of 69,407 rows, after de-duplication); an earlier
project figure of 98.8% measured the same series over distinct (state, district) geographies
(749 of 758), so the two differ only in denominator — per row versus per distinct place — not in
the underlying data.

No dataset and no row is dropped without a recorded reason.
