# Stage 3.5 — Source Inventory & Destination Classification

> **Analysis-only artifact.** No pipeline code, transforms, or source config were changed to
> produce this. It reads every dataset in the local offline archive under `data/archive/` and
> records identity, grain, shape, canonical-metric mapping, temporal span, and cross-source
> overlap, then classifies each into a wiring destination (A/B/C) under the **zero-data-loss**
> rule: classification decides *how* a dataset is wired and served, never *whether* it is kept.
>
> Archive as captured (`_manifest.json`, generated 2026-06-30): 130 datasets discovered on
> data.gov.in — **88 API/JSON retrieved**, **42 file-only** of which **41 downloaded as CSV**
> and **1 was not retrievable**. This inventory covers all **129 on-disk datasets + 1 recorded
> gap = 130**. Values (row counts, columns, FY spans) are read from the bytes on disk, not from
> titles. Authoritative refs: `docs/DATA_CONTRACT.md` §3 (source scope), `docs/RULES.md`.

## Summary

| destination | meaning | count |
|---|---|---|
| **A** — canonical-metric source | measures ≥1 of the 9 canonical metrics; overlaps/cross-checks other sources | **84** |
| **B** — subject-unique source | measures something no canonical metric covers (funds, delayed compensation, assets, works, SHGs…); wire for coverage, no reconciliation peer | **45** |
| **C** — deferred/blocked | cannot be placed yet; preserved and flagged with a specific reason | **1** |
| | **total** | **130** |

Shape distribution (drives the unpivot machinery): **long 34**, **wide-compound 55**
(metric-and-year fused in the column header, e.g. `households_demanded_employment___2014_15`),
**single-period 32** (one snapshot; period fixed by title/"as-on"), **wide-pure 8** (year-only
columns, one title-defined measure, e.g. the RS person-days tables).
Geography distribution: **district 18**, **state 87**, **national 21**, **state-in-title 3**
(single-state datasets whose state appears only in the title, not a column).
Departments: **Rajya Sabha 96**, **MoSPI 20**, **MoRD 11**, **NITI Aayog 2**, **unattributed 1**.

### How A/B/C was decided (important — read before the table)

The three canonical-metric-vs-subject-vs-blocked axes are **not** mutually exclusive with
"can the *current* resolver handle this?" — because the current Stage-3 resolver handles exactly
one shape: flagship-style **district + long** with `state_name`/`district_name` columns. By that
strict reading, *everything except the flagship* is "grain the resolver can't handle" and would
fall into C — which would make the classification useless and contradict the locked scope
(the whole archive is in-scope, DATA_CONTRACT §3).

So destinations here classify by **end-state role**, and the "grain the resolver can't handle
yet" fact is captured as the **machinery each group needs** (the *how*), per group below —
not as a C blocker:

- **A** = carries a canonical metric (reconciliation value), regardless of unpivot/resolve
  machinery still to be built.
- **B** = carries only subject-unique measures (coverage value, no reconciliation peer).
- **C** = genuinely un-placeable *right now*: no bytes on disk, un-parseable structure, or
  geography that cannot be mapped at all (below the district floor / unknown). Only the **1
  un-retrievable dataset** meets this today.

> **Decision flag for review:** if you intended the *strict literal* reading of C ("any grain the
> current resolver can't handle = C"), then A collapses to the flagship alone and ~110 datasets
> become "C-until-machinery." I chose the end-state-role cut because it matches "classification
> decides HOW, never WHETHER" and the zero-data-loss rule. Say the word and I'll re-cut.

Heuristic caveat: canonical-metric mapping and shape are inferred from column names/titles by
pattern, then spot-checked. Cells marked `state(title)` or `wide-compound` especially warrant a
human glance during wiring. The mapping is a *routing signal*, not the final Stage-4 metric map.

## Full inventory (one row per dataset)

Legend — 🚩 flagship anchor · `[RS-pd]` the two RS person-days cross-check tables ·
overlap `Y×n` = shares a canonical metric + geography level + overlapping FY span with `n` other
datasets (cross-check candidate) · `coverage-only` = no such peer. Resource IDs truncated to 8
chars (unique within the archive). Rows sorted destination A→B, then district→state→national.

| resource_id | fmt | dept | rows | grain (geo · time) | shape | canonical-metric map | FY span (read) | overlap | dest |
|---|---|---|---|---|---|---|---|---|---|
| ee03643a 🚩 | JSON | MoRD | 415834 | district · multi-yr series | long | persondays, wage_rate, total_exp, hh_employed… | 2018-19→2026-27 | Y×3 | **A** |
| 79d89e44 | CSV | RS | 76 | district · single-yr snapshot | single-period | persondays, hh_employed | 2019-20→2019-20 | Y×2 | **A** |
| e30835de | JSON | RS | 52 | district · multi-yr series | wide-compound | hh_employed, persondays | 2015-16→2017-18 | Y×3 | **A** |
| fcebf9f9 | JSON | RS | 35 | district · multi-yr series | wide-compound | hh_employed | 2015-16→2017-18 | Y×3 | **A** |
| 530fa100 | JSON | MoRD | 31 | district · single-yr snapshot | long | workers | 2011-12→2011-12 | coverage-only | **A** |
| 12f5a356 | CSV | MoRD | 31 | district · single-yr snapshot | long | workers | 2013-14→2013-14 | coverage-only | **A** |
| 2485c8e1 | CSV | MoRD | 31 | district · single-yr snapshot | long | persondays, hh_employed | 2011-12→2011-12 | coverage-only | **A** |
| 428fa054 | CSV | MoRD | 31 | district · single-yr snapshot | long | persondays, hh_employed | 2014-15→2014-15 | coverage-only | **A** |
| 49214697 | CSV | MoRD | 31 | district · single-yr snapshot | long | persondays, hh_employed | 2015-16→2015-16 | Y×3 | **A** |
| a000738b | CSV | MoRD | 31 | district · single-yr snapshot | long | persondays, hh_employed | 2012-13→2012-13 | coverage-only | **A** |
| a611f7b8 | CSV | MoRD | 31 | district · single-yr snapshot | long | workers | 2014-15→2014-15 | coverage-only | **A** |
| c6575501 | CSV | MoRD | 31 | district · single-yr snapshot | long | persondays, hh_employed | 2013-14→2013-14 | coverage-only | **A** |
| f8f93164 | CSV | MoRD | 31 | district · single-yr snapshot | long | workers | 2012-13→2012-13 | coverage-only | **A** |
| ff821c3b | CSV | MoRD | 31 | district · single-yr snapshot | long | workers | 2015-16→2015-16 | coverage-only | **A** |
| 7371da1e | JSON | RS | 23 | district · multi-yr series | wide-compound | total_exp | 2017-18→2020-21 | Y×1 | **A** |
| cadde395 | JSON | RS | 14 | district · multi-yr series | wide-compound | hh_employed | 2015-16→2019-20 | Y×5 | **A** |
| fc212c38 | JSON | RS | 42 | state · multi-yr series | wide-compound | persondays | 2017-18→2018-19 | Y×6 | **A** |
| fd7c50d2 | CSV | MoSPI | 42 | state · multi-yr series | wide-compound | total_exp, wages, material, admin_exp | 2010-11→2015-16 | Y×7 | **A** |
| 27d1d629 | JSON | RS | 37 | state · single-yr snapshot | single-period | wage_rate | 2016-17→2016-17 | Y×2 | **A** |
| 4c262a70 | JSON | RS | 36 | state · single-yr snapshot | single-period | wage_rate | 2019-20→2019-20 | Y×1 | **A** |
| 15d85eb1 | JSON | RS | 35 | state · single-yr snapshot | single-period | persondays, total_exp | 2016-17→2016-17 | Y×14 | **A** |
| 22f8cdb0 | JSON | RS | 35 | state · multi-yr series | wide-compound | hh_employed, workers, persondays | 2014-15→2015-16 | Y×21 | **A** |
| 2611cc74 | JSON | RS | 35 | state · multi-yr series | wide-compound | hh_employed | 2014-15→2016-17 | Y×15 | **A** |
| 341c9375 | JSON | RS | 35 | state · multi-yr series | wide-pure | persondays | 2012-13→2014-15 | Y×13 | **A** |
| 34a83496 | JSON | RS | 35 | state · multi-yr series | wide-compound | hh_employed | 2012-13→2015-16 | Y×14 | **A** |
| 5183200b | JSON | RS | 35 | state · single-yr snapshot | single-period | total_exp | 2015-16→2015-16 | Y×5 | **A** |
| 630072f2 | JSON | RS | 35 | state · multi-yr series | wide-compound | total_exp | 2014-15→2016-17 | Y×9 | **A** |
| 6c12385f | JSON | RS | 35 | state · multi-yr series | wide-compound | persondays, hh_employed | 2013-14→2016-17 | Y×25 | **A** |
| 73d68992 | JSON | RS | 35 | state · multi-yr series | wide-compound | hh_employed, hh_100d | 2014-15→2015-16 | Y×13 | **A** |
| 8e7b41be | JSON | RS | 35 | state · multi-yr series | wide-pure | total_exp | 2016-17→2019-20 | Y×8 | **A** |
| 923b4373 | JSON | RS | 35 | state · multi-yr series | wide-compound | persondays | 2015-16→2016-17 | Y×15 | **A** |
| b0f2d01a | JSON | RS | 35 | state · multi-yr series | wide-compound | hh_employed | 2014-15→2015-16 | Y×13 | **A** |
| c0350589 | JSON | RS | 35 | state · multi-yr series | wide-compound | material, admin_exp | 2018-19→2021-22 | coverage-only | **A** |
| c5c8858c | JSON | RS | 35 | state · multi-yr series | wide-compound | hh_employed | 2014-15→2015-16 | Y×13 | **A** |
| c8687507 | JSON | RS | 35 | state · single-yr snapshot | single-period | workers | 2016-17→2016-17 | coverage-only | **A** |
| cea6ee41 [RS-pd] | JSON | RS | 35 | state · multi-yr series | wide-pure | persondays | 2019-20→2023-24 | Y×4 | **A** |
| d1d29e37 | JSON | RS | 35 | state · multi-yr series | wide-compound | total_exp | 2019-20→2022-23 | Y×3 | **A** |
| e289a8fe [RS-pd] | JSON | RS | 35 | state · multi-yr series | wide-compound | persondays | 2021-22→2023-24 | Y×1 | **A** |
| e7ee2e1e | JSON | RS | 35 | state · single-yr snapshot | single-period | workers | 2017-18→2017-18 | coverage-only | **A** |
| fa8585f4 | JSON | RS | 35 | state · multi-yr series | wide-compound | persondays | 2015-16→2016-17 | Y×15 | **A** |
| 102ee4c0 | CSV | RS | 35 | state · multi-yr series | wide-pure | wage_rate | 2011-12→2019-20 | Y×5 | **A** |
| 18527128 | CSV | MoSPI | 35 | state · multi-yr series | wide-compound | total_exp, wages, material, admin_exp | 2010-11→2014-15 | Y×5 | **A** |
| 2b43e757 | CSV | RS | 35 | state · multi-yr series | wide-compound | persondays | 2013-14→2016-17 | Y×18 | **A** |
| 2d0a4136 | CSV | MoSPI | 35 | state · multi-yr series | wide-compound | persondays, hh_employed, hh_100d | 2010-11→2015-16 | Y×23 | **A** |
| 42fb2e9f | CSV | RS | 35 | state · multi-yr series | wide-compound | total_exp | 2014-15→2015-16 | Y×6 | **A** |
| 66f18c1a | CSV | RS | 35 | state · single-yr snapshot | single-period | total_exp | 2016-17→2016-17 | Y×5 | **A** |
| 9aefcd0f | CSV | MoSPI | 35 | state · multi-yr series | wide-compound | persondays, hh_employed, hh_100d | 2010-11→2014-15 | Y×19 | **A** |
| a47b1763 | CSV | RS | 35 | state · multi-yr series | wide-compound | persondays | 2014-15→2015-16 | Y×15 | **A** |
| c11b65d4 | CSV | MoSPI | 35 | state · multi-yr series | wide-compound | persondays, hh_employed, hh_100d | 2010-11→2017-18 | Y×29 | **A** |
| cb137c04 | CSV | RS | 35 | state · multi-yr series | wide-compound | persondays, hh_employed | 2013-14→2015-16 | Y×22 | **A** |
| e5491ee9 | CSV | RS | 35 | state · multi-yr series | wide-compound | persondays, hh_employed | 2014-15→2015-16 | Y×21 | **A** |
| 5dcb2b3e | JSON | RS | 34 | state · single-yr snapshot | single-period | wage_rate, hh_employed | 2018-19→2018-19 | Y×4 | **A** |
| 6e2315ad | JSON | RS | 34 | state · single-yr snapshot | single-period | total_exp | 2019-20→2019-20 | Y×3 | **A** |
| 720e21aa | JSON | RS | 34 | state · multi-yr series | wide-compound | persondays, wage_rate | 2012-13→2016-17 | Y×20 | **A** |
| aeca8112 | JSON | RS | 34 | state · multi-yr series | wide-compound | total_exp | 2017-18→2019-20 | Y×5 | **A** |
| 3ebbea46 | CSV | MoSPI | 34 | state · multi-yr series | wide-compound | persondays, hh_employed, hh_100d | 2010-11→2013-14 | Y×11 | **A** |
| d64434e9 | CSV | MoSPI | 34 | state · multi-yr series | wide-compound | total_exp, wages, material, admin_exp | 2010-11→2017-18 | Y×11 | **A** |
| 51a18f1b | JSON | RS | 33 | state · multi-yr series | wide-compound | persondays, hh_employed | 2013-14→2015-16 | Y×22 | **A** |
| 57bff16a | JSON | RS | 33 | state · multi-yr series | wide-pure | total_exp | 2014-15→2018-19 | Y×10 | **A** |
| 7efb084d | JSON | RS | 33 | state · multi-yr series | wide-pure | persondays | 2017-18→2019-20 | Y×8 | **A** |
| 97f6ba47 | JSON | RS | 33 | state · single-yr snapshot | single-period | persondays | 2017-18→2018-19 | Y×6 | **A** |
| a1c9803c | JSON | RS | 33 | state · multi-yr series | wide-pure | hh_employed, hh_100d | 2016-17→2018-19 | Y×5 | **A** |
| bd9922fb | JSON | RS | 33 | state · multi-yr series | wide-compound | hh_employed, persondays | 2016-17→2018-19 | Y×15 | **A** |
| ec1ee20d | JSON | RS | 33 | state · multi-yr series | wide-pure | persondays | 2015-16→2019-20 | Y×20 | **A** |
| eeb479a7 | JSON | RS | 33 | state · multi-yr series | wide-compound | persondays | 2014-15→2018-19 | Y×20 | **A** |
| 0fecf99b | JSON | RS | 32 | state · multi-yr series | wide-compound | persondays | 2019-20→2020-21 | Y×3 | **A** |
| 886d58ec | CSV | RS | 32 | state · single-yr snapshot | single-period | wages | 2015-16→2015-16 | Y×2 | **A** |
| ddd13bbe | JSON | NITI | 31 | state · single-yr snapshot | single-period | persondays | 2010-11→2010-11 | Y×4 | **A** |
| c28ea0d0 | JSON | RS | 30 | state · single-yr snapshot | single-period | total_exp | 2024-25→2024-25 | coverage-only | **A** |
| 26837e5a | JSON | RS | 11 | state · single-yr snapshot | single-period | hh_employed, hh_100d | 2015-16→2015-16 | Y×12 | **A** |
| e0b14917 | JSON | RS | 10 | state · single-yr snapshot | single-period | wage_rate | 2018-19→2018-19 | Y×2 | **A** |
| fca48797 | CSV | — | 18 | national · multi-yr series | long | hh_100d, workers, persondays | 2022-23→2024-25 | coverage-only | **A** |
| 8d734637 | CSV | MoSPI | 17 | national · multi-yr series | long | total_exp, wages, material, admin_exp | 2008-09→2015-16 | Y×4 | **A** |
| d88e2cb6 | CSV | MoSPI | 12 | national · multi-yr series | long | persondays, hh_employed, hh_100d, workers | 2006-07→2017-18 | Y×5 | **A** |
| 1878204d | CSV | MoSPI | 10 | national · multi-yr series | long | persondays, hh_employed, hh_100d, workers | 2006-07→2015-16 | Y×4 | **A** |
| 7496d75d | CSV | MoSPI | 10 | national · multi-yr series | long | total_exp, wages, material, admin_exp | 2008-09→2017-18 | Y×7 | **A** |
| 04476f1d | JSON | MoSPI | 9 | national · multi-yr series | long | persondays, hh_employed, workers | 2006-07→2014-15 | Y×3 | **A** |
| 54d1a5fa | CSV | MoSPI | 8 | national · multi-yr series | long | persondays, hh_employed, hh_100d, workers | 2006-07→2013-14 | Y×3 | **A** |
| 99a91845 | CSV | MoSPI | 7 | national · multi-yr series | long | total_exp, wages, material, admin_exp | 2008-09→2014-15 | Y×3 | **A** |
| 6ae541ca | JSON | RS | 5 | national · multi-yr series | long | wage_rate, wages | 2014-15→2018-19 | Y×4 | **A** |
| 8e9fe253 | JSON | RS | 4 | national · multi-yr series | long | total_exp | 2016-17→2019-20 | Y×4 | **A** |
| 484bf9c5 | JSON | RS | 3 | national · multi-yr series | long | total_exp, wages, material | 2016-17→2018-19 | Y×5 | **A** |
| bf1da9fc | JSON | RS | 2 | national · multi-yr series | long | persondays, total_exp | 2015-16→2018-19 | Y×7 | **A** |
| ea03aba7 | JSON | RS | 2 | national · multi-yr series | long | persondays, total_exp | 2017-18→2018-19 | Y×5 | **A** |
| 41c20814 | JSON | RS | 14 | district · multi-yr series | wide-compound | subject-unique (water/assets) | 2015-16→2019-20 | coverage-only | **B** |
| 24a028ac | JSON | RS | 11 | district · single-yr snapshot | single-period | subject-unique (funds_released) | 2016-17→2016-17 | coverage-only | **B** |
| af6f81cd | CSV | MoSPI | 38 | state · multi-yr series | wide-compound | subject-unique (water/assets) | 2010-11→2015-16 | coverage-only | **B** |
| c3316007 | JSON | RS | 36 | state · single-yr snapshot | single-period | subject-unique (funds_released) | 2016-17→2016-17 | coverage-only | **B** |
| fadc1024 | JSON | RS | 36 | state · single-yr snapshot | single-period | subject-unique (funds_released) | 2016-17→2016-17 | coverage-only | **B** |
| 9bec525d | CSV | RS | 36 | state · single-yr snapshot | single-period | subject-unique (funds_released) | 2016-17→2016-17 | coverage-only | **B** |
| 0b3149e7 | JSON | RS | 35 | state · multi-yr series | wide-compound | subject-unique (grievance/complaint) | 2015-16→2016-17 | coverage-only | **B** |
| 22ca0b64 | JSON | RS | 35 | state · multi-yr series | wide-compound | subject-unique (funds_released) | 2013-14→2016-17 | coverage-only | **B** |
| 4632d771 | JSON | RS | 35 | state · multi-yr series | wide-compound | subject-unique (grievance/complaint) | 2013-14→2015-16 | coverage-only | **B** |
| 92331756 | JSON | RS | 35 | state · multi-yr series | wide-compound | subject-unique (funds_released) | 2017-18→2019-20 | coverage-only | **B** |
| 9ea040fa | JSON | RS | 35 | state · single-yr snapshot | single-period | subject-unique (process/governance) | 2016-17→2016-17 | coverage-only | **B** |
| a0d62cd1 | JSON | RS | 35 | state · single-yr snapshot | single-period | subject-unique (funds_released) | 2019-20→2019-20 | coverage-only | **B** |
| bfea3018 | JSON | RS | 35 | state · single-yr snapshot | single-period | subject-unique (process/governance) | 2023-24→2023-24 | coverage-only | **B** |
| 64e915f4 | CSV | RS | 35 | state · single-yr snapshot | single-period | subject-unique (funds_released) | 2015-16→2015-16 | coverage-only | **B** |
| 68840a65 | CSV | RS | 35 | state · multi-yr series | wide-compound | subject-unique (funds_released) | 2012-13→2016-17 | coverage-only | **B** |
| 7cc62579 | CSV | RS | 35 | state · multi-yr series | wide-compound | subject-unique (funds_released) | 2012-13→2015-16 | coverage-only | **B** |
| 0a4e6ea7 | JSON | MoSPI | 34 | state · multi-yr series | wide-compound | subject-unique (water/assets, works) | 2010-11→2012-13 | coverage-only | **B** |
| f40bf2b4 | CSV | MoSPI | 34 | state · multi-yr series | wide-compound | subject-unique (water/assets) | 2010-11→2012-13 | coverage-only | **B** |
| 1207abc1 | JSON | RS | 33 | state · multi-yr series | wide-compound | subject-unique (funds_released) | 2014-15→2017-18 | coverage-only | **B** |
| 3e87dec0 | JSON | RS | 33 | state · single-yr snapshot | single-period | subject-unique (funds_released) | 2019-20→2019-20 | coverage-only | **B** |
| 3ffbac94 | JSON | RS | 33 | state · single-yr snapshot | single-period | subject-unique (process/governance) | 2018-19→2018-19 | coverage-only | **B** |
| 6827bdf1 | JSON | RS | 33 | state · multi-yr series | wide-compound | subject-unique (process/governance) | 2014-15→2017-18 | coverage-only | **B** |
| 7388bc76 | JSON | RS | 33 | state · multi-yr series | wide-compound | subject-unique (process/governance) | 2016-17→2017-18 | coverage-only | **B** |
| c3b1dffb | JSON | RS | 33 | state · multi-yr series | wide-compound | subject-unique (water/assets) | 2012-13→2016-17 | coverage-only | **B** |
| c47dcff6 | JSON | RS | 33 | state · multi-yr series | wide-compound | subject-unique (process/governance) | 2014-15→2017-18 | coverage-only | **B** |
| c5de960a | JSON | RS | 33 | state · multi-yr series | wide-compound | subject-unique (process/governance) | 2014-15→2018-19 | coverage-only | **B** |
| e6bf3cb1 | JSON | RS | 33 | state · single-yr snapshot | single-period | subject-unique (process/governance) | 2018-19→2018-19 | coverage-only | **B** |
| b30c524a | JSON | RS | 32 | state · single-yr snapshot | single-period | subject-unique (grievance/complaint) | 2015-16→2015-16 | coverage-only | **B** |
| cc1533a1 | JSON | RS | 31 | state · single-yr snapshot | single-period | subject-unique (water/assets) | 2016-17→2016-17 | coverage-only | **B** |
| e6feebe1 | JSON | RS | 26 | state · multi-yr series | wide-compound | subject-unique (grievance/complaint) | 2016-17→2019-20 | coverage-only | **B** |
| ede4109e | JSON | RS | 25 | state · multi-yr series | wide-compound | subject-unique (funds_released) | 2015-16→2016-17 | coverage-only | **B** |
| 41256e58 | JSON | RS | 17 | state · single-yr snapshot | single-period | subject-unique (grievance/complaint) | 2018-19→2018-19 | coverage-only | **B** |
| b0c7c7a4 | JSON | RS | 15 | state · multi-yr series | wide-compound | subject-unique (funds_released) | 2021-22→2022-23 | coverage-only | **B** |
| 418b414a | JSON | RS | 11 | state · single-yr snapshot | single-period | subject-unique (water/assets, works) | 2015-16→2015-16 | coverage-only | **B** |
| 285d7783 | JSON | RS | 4 | state(title) · multi-yr series | long | subject-unique (funds_released) | 2015-16→2018-19 | coverage-only | **B** |
| 657ac6a3 | JSON | RS | 3 | state(title) · multi-yr series | long | subject-unique (process/governance) | 2016-17→2018-19 | coverage-only | **B** |
| 9aa66b7a | JSON | RS | 1 | state(title) · multi-yr series | long | subject-unique (funds_released) | 2016-17→2018-19 | coverage-only | **B** |
| 81043a7e | JSON | RS | 44 | national · single-yr snapshot | single-period | subject-unique (process/governance) | 2018-19→2018-19 | coverage-only | **B** |
| 8efa9ec1 | CSV | MoSPI | 8 | national · multi-yr series | long | subject-unique (water/assets) | 2008-09→2015-16 | coverage-only | **B** |
| 4cc2e26d | JSON | RS | 5 | national · multi-yr series | long | subject-unique (process/governance) | 2013-14→2017-18 | coverage-only | **B** |
| 7b502fe1 | JSON | RS | 5 | national · multi-yr series | long | subject-unique (process/governance) | 2014-15→2018-19 | coverage-only | **B** |
| 1608c4a1 | CSV | MoSPI | 5 | national · multi-yr series | long | subject-unique (water/assets) | 2008-09→2012-13 | coverage-only | **B** |
| b0830b4b | CSV | MoSPI | 5 | national · multi-yr series | long | subject-unique (water/assets) | 2008-09→2012-13 | coverage-only | **B** |
| 2aeef02e | JSON | RS | 3 | national · multi-yr series | long | subject-unique (process/governance) | 2015-16→2017-18 | coverage-only | **B** |
| c8f211d0 | JSON | RS | 3 | national · multi-yr series | long | subject-unique (process/governance) | 2016-17→2018-19 | coverage-only | **B** |
| 8325c8a6 | — | RS | 0 | — (not retrieved) | — | — | — | — | **C** |

## Destination A — canonical-metric sources (84)

**Common pattern.** These carry at least one of the 9 canonical metrics. By geography: **55
state-grain**, **16 district-grain**, **13 national**. By shape: **36 wide-compound, 24 long, 16
single-period, 8 wide-pure**. Canonical coverage across the group: persondays 41, households
32, total_expenditure 23, active_workers 14, 100-days 11, wages 10, material 9, admin 8,
wage_rate 8 — i.e. every one of the 9 metrics is measured by multiple independent sources, which
is exactly the redundancy that makes cross-source reconciliation meaningful.

The flagship (`ee03643a`, district·monthly, 415,834 rows, FY2018-19→2026-27) is the only member
the existing resolver can already process. The RS person-days tables (`cea6ee41`, `e289a8fe`)
are the state·annual cross-checks proven to reconcile in `docs/notes/divergence-findings.md`.

**Machinery needed to wire group A (name only — not built here):**
1. **A simple melt** for the 8 **wide-pure** tables (year-only columns → one row per state×year).
2. **A compound melt** for the 36 **wide-compound** tables — the hard one: split *both* the
   metric stem and the FY out of fused headers like `households_provided_employment___2015_16`,
   emitting (metric, state, year, value). No such transform exists.
3. **A period-from-title/"as-on" extractor** for the 16 **single-period** tables (the FY/as-on
   date lives in the title, not a column) so each snapshot lands at the right period.
4. **A state-grain resolve path** (55 datasets): resolve a `state`/`state_ut` name to LGD state
   identity with **no district** — the current resolver mandates a district and would quarantine
   every row (this is the exact gap flagged in the pre-Stage-4 scoping note).
5. **A national-aggregate store path** (13 datasets): national totals have no geography to
   resolve; they must be filed as national-grain facts, not forced through geo resolution.
6. **Per-source Stage-2/3 config** (column-type spec, grain keys, geo columns) for each new
   source_id — the 16 district-grain non-flagship tables also need this, since the resolver's
   `SOURCE_GEO_COLUMNS` is currently flagship-only.

## Destination B — subject-unique sources (45)

**Common pattern.** These measure things **outside** the 9 canonical metrics and have no
reconciliation peer: **funds released/allocated (16)**, **process/governance — delayed
compensation, timely pay-order %, wage-transaction rejections, SHGs formed, anganwadis built
(16)**, **water & other NRM assets/plantations (10)**, **works approved/started (2)**,
**grievances/social-audit (5)**. By geography: 32 state, 8 national, 3 state-in-title, 2
district. Shape mix mirrors A (19 wide-compound, 16 single-period, 10 long).

**Machinery needed to wire group B (name only):** the *same* unpivot + resolve machinery as A
(items 1–6 above) — nothing extra — **minus** any Stage-4 reconciliation step, because there is
no second source measuring the same quantity. Each B dataset is stored and served as a
single-source, lineage-tagged coverage fact (`sources_seen = 1`, per RULES R4-REC-04). The point
of separating B from A is purely that **B needs no agreement/disagreement logic**, so wiring it
is cheaper and lower-risk — but it must still be served (zero data loss).

## Destination C — deferred/blocked (1)

**`8325c8a6-1bcb-49d9-b127-9e92cc2d4898`** — listed in portal discovery, `is_api_available=0`,
`rows_downloaded=0`, and **no file on disk** (the "42nd" file-only dataset; the archive holds
41). It cannot be inventoried, resolved, or served until the bytes are obtained.

**Reason:** data not retrieved. **Required action (preserve, don't drop):** re-attempt the
file-only fetch (per the `data/archive/csv/` rewrite path that worked for the other 41); if still
unavailable, record it as a known, cited gap in the trust report rather than silently omitting
it. This is the only genuine blocker in the archive today — every other dataset is parseable and
placed in A or B.

## ⚠ Highest-cost-if-lost callout — unique coverage

These are the datasets whose loss would be **unrecoverable** because nothing else in the archive
covers the same period or measures the same thing. They are the strongest reason the "flagship
is enough" framing was wrong.

**Pre-flagship history (the flagship starts FY2018-19).** **81 of 129 datasets end before
FY2018-19** and are the *only* carriers of MGNREGA facts for FY2006-07 → FY2017-18. The deepest,
most irreplaceable are the all-India and state annual history series reaching back to the
scheme's start:

- `04476f1d` [JSON] FY2006-07→2014-15 — All India Implementation Report (persondays, households, workers)
- `1878204d` [CSV] FY2006-07→2015-16 — All India Implementation Report
- `d88e2cb6` [CSV] FY2006-07→2017-18 — All India Implementation Report
- `54d1a5fa` [CSV] FY2006-07→2013-14 — Implementation Report (All India)
- `7496d75d` / `8d734637` / `99a91845` [CSV] FY2008-09→ — All India Financial Outcomes
- `1608c4a1` / `b0830b4b` / `8efa9ec1` [CSV] FY2008-09→ — All India Physical Outcomes
- `ddd13bbe` [JSON] FY2010-11 — Seasonality of MGNREGA employment (a one-off national cut)
- 10 further **state-wise** Implementation/Financial/Physical Outcomes CSVs spanning FY2010-11→2015-18

Losing these = losing the first 12 years of the canonical FY2006-07→2026-27 series. They exist
**nowhere else in the archive** and the flagship does not reach back that far.

**Subject-unique measures (destination B).** The ~45 B datasets are the only measurements of
their subject in the archive — e.g. **delayed-compensation to workers**, **wage-transaction
rejection reasons**, **timely pay-order %**, **SHGs formed / anganwadis constructed**, **NRM
water assets & plantations**, **fund release/allocation**, **grievances / social audit**. None
maps to a canonical metric, so none is recoverable by reconciliation; each must be served on its
own or the platform simply cannot answer questions about that subject.

## Method & limitations

- Extraction: read `_manifest.json` for identity/department, then each `*.json` (data.gov.in
  envelope: `field[]` + `records[]`) and each `csv/*.csv` (header + rows) directly. FY spans read
  from year-bearing column headers and, for long tables, from the year column's row values;
  title used only as a last-resort fallback. Full-form `YYYY-YYYY` end-years were explicitly
  prevented from being double-counted as separate start years.
- Grain, shape, and canonical mapping are pattern-inferred and spot-checked, not exhaustively
  verified per cell — treat as a **routing signal** for wiring, to be confirmed against
  DATA_CONTRACT §2.3 when each source is actually mapped in Stage 4.
- Overlap is a coarse signal (shared canonical tag + same geo level + overlapping FY span); it
  flags cross-check *candidates*, not confirmed same-fact matches (that is Stage 4's job).
- No machinery described above was implemented. This report stops at inventory + classification,
  per the task's explicit "do not proceed to wiring" instruction.
