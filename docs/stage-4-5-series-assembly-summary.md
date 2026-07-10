# Stage 4.5 — Series Assembly Summary

The deliverable: **one continuous canonical MGNREGA series at STATE-ANNUAL grain**, one
authoritative value per `(state, financial-year, metric)`, each fully lineage-traced — plus a
**parallel NATIONAL-ANNUAL spine**. Both are assembled by the same era policy, using the Stage-4
reconcile engine purely as the trust tool (no new adjudication machinery).

Numbers below are produced over the local archive by
`tests/harmonize/test_series_integration.py` (the committed, archive-gated proof) and reproduce
exactly. This is a coverage report, not new logic.

## Era policy (as built)

- **2018-19 → 2026-27** — the flagship (district-monthly MIS) rolled up to state-annual is
  authoritative (`authority_rank = 0`, basis `flagship (district-monthly, rolled up)`). The finer
  district-monthly detail is not discarded; it rides beneath, reachable via lineage.
- **2006-07 → 2017-18** — assembled from historical sources (`authority_rank = 10`), labelled by
  INDEPENDENCE: `cross-publisher` when ≥2 distinct publishers agree, `single-publisher` when only
  multiple editions/vintages of ONE publisher agree (weaker evidence); a lone source →
  `single-source`. Where one publisher's DATED EDITIONS of the same table disagree, the latest
  edition is taken and the earlier recorded as `edition-superseded` (R4-REC-10, a grounded editorial
  hierarchy); where two INDEPENDENT publishers disagree materially, a winner is taken on authority
  and the rejected value recorded (`flagged`).
- The **seam is continuous** at state-annual grain: each fact carries its `basis` + `confidence` +
  the full `Reconciliation` lineage (sources seen with ids and as-of, any disagreement, the rule).

## STATE-annual spine

- **4,216 facts**, 8 canonical metrics, **35 states/UTs**, **FY 2010-11 → FY 2026-27**.

> **Stage-5 note.** These figures are the Stage-4.5 harmonize output (this test uses the pre-2018
> `HISTORICAL_STATE_SOURCES` only). The Stage-5 **export** additionally reconciles four flagship-era
> Rajya Sabha state peers — person-days (`cea6ee41`, `e289a8fe`), total-expenditure (`57bff16a`),
> 100-days (`a1c9803c`) — against the flagship rollup and the historical sources, so the exported
> state spine is **4,219** facts. Two consequences: (1) 2018+ cells across those metrics are no
> longer all single-source — **180** corroborated, **25** flagged, **10** unadjudicated, **3**
> RS-only; and pre-2018 the RS expenditure/100-days tables add **137** cross-publisher corroborations
> and **5** genuine `total_expenditure` disagreements. (2) The amended **R4-REC-11** now excludes
> MoSPI's SYB2018 FY2017-18 mid-year partial even with no superseding edition — filled by an RS
> full-year peer where one exists, else withheld (**164** `partial-period-only` cells). Because of
> (2), the per-metric table below no longer reflects FY2017-18 (now withheld); `DATA_DICTIONARY.md`
> §8 is the authoritative current account.
>
> **Reclassifications from the amendment (Step 4a).** No cell moved *out of* `unadjudicated`. The
> amended R4-REC-11 moves the FY2017-18 SYB2018 terminal cells from `single-source` (a partial
> published as an annual) to `partial-period-only` (withheld); and the single two-floor materiality
> standard's money floor moves West Bengal FY2018-19 `total_expenditure` from a would-be R4-REC-05
> unadjudicated to R4-REC-08 `immaterial` (0.83% < 1%). (The review's "8→7 unadjudicated" projection
> did not materialize — unadjudicated in fact grew 7→10 as the expenditure/100-days peers came in.)
>
> **v1.1 (Step 4b).** The FY2017-18 nulls are expected to be temporary: the deferred RS vintages
> `7efb084d`/`ec1ee20d` carry FY2017-18 as a NON-terminal (full) year and are queued to fill them.

The table below is the **pre-2018** confidence mix per metric (where all the multi-source
reconciliation happens); **2018+ is 304 single-source flagship cells** for every metric (before the
Stage-5 export peers above). Labels:
`cross-publisher` = ≥2 INDEPENDENT publishers agreed; `single-publisher` = ≥2 editions/vintages of
ONE publisher agreed; `edition-superseded` = a later edition of one publisher's table restated an
earlier one and the latest edition was taken (R4-REC-10); `single-source` = one source only;
`flagged` = a material cross-PUBLISHER disagreement, a winner taken and the rejected value recorded
(R4-REC-02); `immaterial` = a divergence below the magnitude floor (near-zero base, R4-REC-08).

| metric | pre-2018 cells | cross-publisher | single-publisher | edition-superseded | single-source | flagged | immaterial |
|---|--:|--:|--:|--:|--:|--:|--:|
| households_employed | 254 | 118 | 14 | 48 | 33 | 4 | 37 |
| households_completed_100_days | 254 | 0 | 83 | 106 | 65 | 0 | 0 |
| persondays_generated | 254 | 0 | 110 | 78 | 66 | 0 | 0 |
| active_workers | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| wages_expenditure | 255 | 0 | 123 | 67 | 65 | 0 | 0 |
| material_skilled_expenditure | 257 | 0 | 118 | 72 | 67 | 0 | 0 |
| admin_expenditure | 255 | 0 | 148 | 42 | 65 | 0 | 0 |
| total_expenditure | 255 | 0 | 131 | 59 | 65 | 0 | 0 |

`households_employed` is the ONLY pre-2018 state metric with two independent publishers (MoSPI +
Rajya Sabha), so it is the only one with `cross-publisher` cells; every other pre-2018 metric is
MoSPI-only — its multiple files are dated EDITIONS of one MoSPI table, so it is `single-publisher`
(agreeing editions) or `edition-superseded` (latest edition taken) at best, never overstated as
independent corroboration.

- **No pre-2018 cell is left unadjudicated for want of a peer.** With edition supersession OFF, the
  MoSPI-only cells where a publisher's dated editions disagree would be `single-publisher divergence`
  (R4-REC-09, value = null): admin 76, material 106, wages 100, total 95, 100-days 78, persondays 97,
  households 20 — **572 state cells**. Edition supersession (R4-REC-10) adjudicates every one to the
  latest edition, so **R4-REC-09 is now 0**; **472** of the resolved cells carry the
  `edition-superseded` label (a later edition actually restated an earlier one), the rest resolving
  to plain single-/cross-publisher agreement.
- **The only genuine cross-PUBLISHER material disagreements remaining are 4** — all in
  `households_employed` (MoSPI's latest edition vs a Rajya Sabha answer). Collapsing the MoSPI
  editions to the latest before comparing to RS also un-hid real agreement: `cross-publisher` rose
  53 → 118 and household `flagged` fell 69 → 4.

Sources wired: flagship (2018+, all metrics); MoSPI Financial Outcomes state files (expenditure,
INR lakh); MoSPI Implementation Report state files (households / 100-days as raw counts, persondays
in lakh); Rajya Sabha "households provided employment" (lakh) and "completed 100 days" (raw) tables.
The MoSPI Financial Outcomes files (3: SYB 2016/2017/2018) and MoSPI Implementation Report files
(4: SYB 2015/2016/2017/2018) are each an **edition family** — see edition supersession below.

## NATIONAL-annual spine (parallel — no LGD anchor, not merged into the state series)

- **148 facts**, 8 metrics. Households / 100-days / persondays span **FY 2006-07 → 2026-27**;
  expenditure spans **FY 2008-09 → 2026-27** (the national financial sources begin 2008-09).
- Pre-2018 (2006-07 → 2017-18) comes from the wide national historical sources — MoSPI
  Implementation (national) and Financial Outcomes (national); 2018+ is the flagship rolled to a
  national total (national = sum of reporting states, additive metrics). persondays corroborates
  across up to **7** national sources pre-2018.

The national historical sources are all MoSPI, so national agreement is `single-publisher`
(cross-edition) — never `cross-publisher` (0 across every metric). The `flagged` column here still
lumps the not-yet-resolved single-publisher divergences: **edition supersession (R4-REC-10) was
scoped to the two VERIFIED state edition families and is NOT yet applied to the national tier.** The
national MoSPI files are the same SYB-edition structure (Table 35.1 / 35.3 national), so extending
R4-REC-10 there is a same-mechanism follow-up — deferred here only because the national families
were not put through the empirical unidirectional-restatement check the state families passed.

| metric | cross-publisher | single-publisher | single-source | flagged |
|---|--:|--:|--:|--:|
| households_employed | 0 | 4 | 11 | 6 |
| households_completed_100_days | 0 | 4 | 13 | 4 |
| persondays_generated | 0 | 7 | 11 | 3 |
| active_workers | 0 | 0 | 9 | 0 |
| wages_expenditure | 0 | 5 | 11 | 3 |
| material_skilled_expenditure | 0 | 4 | 11 | 4 |
| admin_expenditure | 0 | 4 | 11 | 4 |
| total_expenditure | 0 | 5 | 11 | 3 |

## Honest gaps (year × metric × state cells with NO source)

- **FY 2006-07 → 2009-10 has no STATE-level source.** The earliest wired historical *state* source
  is FY 2010-11, so the state spine starts there. These four years exist only in the **national**
  spine (national historical sources reach back to 2006-07). Not filled — a visible gap, never
  synthesized.
- **`active_workers` has no pre-2018 value** in either spine. The one historical candidate
  (`c8687507…`) is a single FY 2016-17 mid-year snapshot with zero flagship overlap and no
  corroborating peer; it is coverage, not a defensible series value, so it is excluded. Active
  workers is a flagship-era (2018+) metric.
- **`avg_wage_rate_per_day` is not in the state-annual spine.** It is a *rate* (INR/day/person),
  native to district-monthly grain and single-source; it does not sum to a state-annual total, so
  it is kept at its native grain (via flagship lineage), not forced into this series.
- Within 2010-2017, coverage is 32-33 states/UTs per metric-year (not the full 35) — states that a
  given historical source did not report that year are simply absent (null ≠ 0).

## How divergence is kept truthful

The `flagged` count means ONE thing only: a material disagreement between two INDEPENDENT publishers.
Everything that is not that — a shorter reporting period, a rounding difference, a near-zero swing, or
one publisher restating its own earlier edition — is separated out FIRST, so the flag is signal, not
noise. Five mechanisms do this, in the order reconciliation applies them:

- **Edition supersession (R4-REC-10).** Most pre-2018 corroboration comes from ONE publisher (MoSPI)
  that re-issued the same table across successive **Statistical Year Book editions** — Financial
  Outcomes as SYB 2016/2017/2018, Implementation Report as SYB 2015/2016/2017/2018. These are not
  three or four independent readings; they are one publisher's successive drafts, each restating the
  earlier years. Where a later edition restated an earlier one, the **latest edition is taken** and
  the earlier value is kept in lineage as `edition_superseded` — not a conflict, not a rejected peer.
  This is a source-grounded editorial hierarchy (same catalog + dated edition markers + verified
  one-directional restatement, see below), NOT a blind "newest file wins". It carries the
  `edition-superseded` label on **472 state cells**, and adjudicates every one of the 572 cells the
  earlier build could not (leaving them null) to a value.
- **Partial-terminal-year exclusion (R4-REC-11) — the "incompleteness" rule.** An edition's LAST
  year is a mid-year partial (e.g. SYB 2016's 2014-15 is "as on 31.12.2014" — three quarters of a
  year). When a later edition carries that year in full, the earlier edition's part-year value is a
  DIFFERENT period and is excluded before comparison (`partial_period` in lineage), never flagged as
  a disagreement. Real example: `households_employed` state 17, FY 2014-15 — the SYB 2016 edition's
  182,449 (part-year) vs the full-year 351,192; the partial is dropped, the full-year value stands.
- **Partial-year *columns* excluded (Stage-2 reshape).** The same principle for a compound header
  like `..._2015_16_upto_30_09_2015`: reshape detects the `upto`/`till`/`as-on` suffix and refuses
  to promote that value into the full-year cell. The two RS cases (`34a83496` FY2015-16, `6c12385f`
  FY2016-17) previously injected a ~half-year value into every state; excluded, they no longer flag.
- **Precision-aware count agreement (R4-REC-01a).** A lakh-rounded count (RS 36.07 lakh → 3,607,000)
  agrees with a raw count (MoSPI 3,606,783) within the source's OWN declared precision (2-dp lakh →
  ±500), instead of being flagged by exact-match. Genuine small-state gaps (RS 129,000 vs MoSPI
  94,674, a real 26 %) still flag. This surfaces real MoSPI+RS agreement exact-match had hidden.
- **Near-zero materiality (R4-REC-08).** A percentage on a near-zero base is meaningless: 77 vs 174
  completers is 126 % but a 97-household spread. A disagreement is `immaterial` unless it clears BOTH
  an absolute floor AND a relative floor — so tiny UTs (Lakshadweep, etc.) are recorded, not counted
  as a material conflict. 37 pre-2018 `households_employed` cells land here.

**What "single-publisher divergence" (R4-REC-09) means to a reader.** When ONE publisher's sources
disagree materially and there is NO groundable edition hierarchy to order them (they are peer
vintages, not dated editions), no winner is invented — the value is published as `unadjudicated`
with every reading in lineage. After edition supersession, the state spine has **zero** such cells
(the MoSPI expenditure/household editions are now ordered as editions, not left as peer vintages).

**The one 10× scale bug is corrected, never averaged.** `households_employed` state 2, FY 2013-14:
the MoSPI editions carried 539,223 / 53,890 / 539,024 (53,890 is a dropped-digit error, ≈ 539,000 ÷
10). Edition supersession takes the latest edition (539,024) and records the erroneous 53,890 as
superseded/partial lineage; RS corroborates at 539,000. The final value is 539,000 — the bad figure
is excluded, never blended into an average. (The cross-publisher form of this is R4-REC-07 scale
quarantine.)

*Labeling nuance:* in this cell the two `53,890` copies are recorded under `edition_superseded` and
`partial_period`, NOT under a distinct scale-error reason. Edition normalization (R4-REC-10/11) runs
BEFORE scale detection (R4-REC-07) and removes them first, so `_scale_errors` never sees them.
Re-attributing them to a scale-error reason would mean running scale detection ahead of the edition
logic — entangled with it, and it would perturb the verified edition-supersession result set — so it
is left as-is. The outcome is unchanged (the `53,890` is excluded and never averaged); only the
recorded *reason* is edition/partial rather than scale.

## Design fork flagged for review — pre-2018 peer authority

The MoSPI-vs-MoSPI question is now **resolved by R4-REC-10**: those files are dated editions, so the
latest edition is authoritative (grounded, not guessed). What remains is the **cross-publisher**
peer question: MoSPI and Rajya Sabha are still given **equal `authority_rank = 10`**, because a
MoSPI-over-RS ordering is an entity/harmonization decision not written in `RULES.md` — an Open
Question, not something to guess (TIER 1 rule 1).

Consequence: the only cells this affects are the **4** pre-2018 `households_employed` cells where
MoSPI's latest edition and an RS answer disagree materially. There the reconcile engine's
deterministic tiebreak (**latest `source_as_of`, then latest edition, then `source_id`**) takes a
winner and records the rejected peer + max pairwise % as `flagged` — divergence published, not
hidden. Median pre-2018 household disagreement is now ≈2 %, and every larger gap is explained by the
mechanisms above (verified by a spot-check of the 5-50 % band — no unexplained pattern remains).

**Question for review:** should a grounded authority ordering between the two *independent
publishers* (MoSPI/MoRD final figures over an RS answer for the same fact) be written into
`RULES.md`, or is the equal-rank recency tiebreak the intended resolution for those 4 cells?

**Question for review:** is the equal-rank recency tiebreak the desired resolution for pre-2018 peer
disagreement, or should a grounded authority ordering (e.g. MoSPI/MoRD final figures over an RS
answer for the same fact) be written into `RULES.md` and applied? Proceeding with equal-rank peers
until that rule is decided.
