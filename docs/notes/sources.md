# Stage 0 · T0.1 — Source Reconnaissance (registry)

> Status: **DRAFT for review.** This pass covers **SRC_OGD (data.gov.in) only** — the API
> key-verification check plus a proposed shortlist of datasets. SRC_SYNC (DeshSeva/dataful)
> and SRC_MIS (nrega.nic.in) reconnaissance are **pending** (sections stubbed at the bottom).
> No data was fetched to disk yet (that is T0.2). The proposed shortlist is **not settled** —
> it awaits Prateek's review before any T0.2 fetching.
> Authoritative refs: `DATA_CONTRACT.md`, `RULES.md`. Starter metrics (LOCKED): persondays_generated,
> avg_wage_rate_per_day, total_expenditure. Grain (LOCKED): district + monthly.

---

## 0. API KEY-CHECK RESULT — ✅ KEY AUTHENTICATES

`DATA_GOV_API_KEY` in `.env` (56 chars, `579b…87d3`) is **valid**. Verified decisively by
hitting the SAME endpoint with the real key vs. a bad key:

| key used | endpoint | response |
|---|---|---|
| **real key** | `GET api.data.gov.in/resource/<valid-id>?…` | `200 {"status":"ok", total:415834}` — real rows returned |
| real key | `GET .../resource/<nonexistent-id>?…` | `200 {"status":"error","message":"Meta not found"}` (key passed; resource absent) |
| **bad key** | `GET .../resource/<any-id>?…` | `{"error":"Key not authorised"}` |

The flagship pull returned **5 real rows** from *District-wise MGNREGA Data at a Glance*
(resource id `ee03643a-ee4c-48c2-ac30-9f2ff26ab722`) — see §3.

`api.data.gov.in/catalog` (the old search endpoint) is **dead (404)** and the
`datagovindia` package's `sync_metadata()` / the official catalog search **time out** from
this environment. Per-resource calls are fast and reliable; **bulk discovery via api.data.gov.in
is not**. Discovery was instead done via the platform's own backend (see §1).

---

## 1. How datasets & resource IDs are discovered on the rebuilt platform (reproducible method)

The rebuilt data.gov.in is a Nuxt SPA over a Drupal backend; resource pages are JS-rendered
and contain **no resource ID in static HTML**. The working discovery path is the SPA's own
backend search:

```
GET https://www.data.gov.in/backend/dmspublic/v1/resources?query=mgnrega&offset=0&limit=50
```
- `query=<text>` is the full-text filter (NOT `q=` — `q` is ignored, returns the whole catalog).
- Records are at `data.rows[]`; facets at `data.aggregations`. `total=130` MGNREGA matches.
- Each record exposes (all values are 1-element lists): `title`, `node_alias` (slug),
  `ministry_department`, `sector`, `granularity`, `frequency`, `file_format`, `uuid`, `nid`,
  `catalog_reference`, `datafile` (direct file URL), `is_api_available`, `created`/`changed`
  (epoch), `data_time_period_from`/`_to` (epoch).

**Resource-ID → API mapping (the key unlock):** the api.data.gov.in resource ID is the
record's **`uuid` (dashed form)**. i.e.
`https://api.data.gov.in/resource/<uuid>?api-key=…&format=json&limit=N`.
(The uuid WITHOUT dashes, the `nid`, and `catalog_reference` all fail with "Meta not found".)

---

## 2. Fragmentation finding (per spec: note that MGNREGA is spread across many datasets)

MGNREGA on data.gov.in is fragmented across **~130 datasets** (full-text `query=mgnrega`),
across multiple publishers. Of these: **88 expose an API**, 42 are file-only; formats are
128× CSV, 2× XLS. Reported `granularity`: Others 93, Annual 31, Quarterly 5, Daily 1
(NB: this metadata label is unreliable — see §4). The large majority are **one-off
parliamentary Q&A answers** (publisher "Rajya Sabha") for a single state + a few years
(e.g. "District-wise expenditure … Punjab 2017-18 to 2019-20"), NOT a continuous series.
**v1 ingests only the shortlist below; the remaining ~129 are documented candidate sources,
not ingested.**

---

## 3. PROPOSED SRC_OGD SHORTLIST (covers all 3 starter metrics at district + monthly grain)

**The smallest set is ONE dataset** — the flagship national series covers all 3 starter
metrics (and all 9 canonical metrics) at district + monthly grain. No second OGD dataset is
needed for the starter slice.

| field | value (verbatim) |
|---|---|
| dataset title | `District-wise MGNREGA Data at a Glance` |
| slug | `/resource/district-wise-mgnrega-data-glance` |
| **API resource id** | `ee03643a-ee4c-48c2-ac30-9f2ff26ab722` |
| publishing dept | `Ministry of Rural Development` (sector: Development) |
| format | `text/csv` (also queryable as JSON via API) |
| API available | yes (`is_api_available=1`) |
| total rows | **415,834** |
| geography grain | **district** — `state_code`, `state_name`, `district_code`, `district_name` (codes look LGD-aligned, e.g. MP=17) |
| temporal grain | **monthly** — `fin_year` (e.g. `2024-2025`) + `month` (3-letter, e.g. `Dec`) |
| temporal coverage | seen FY **2018-2019 → 2025-2026** (e.g. PUNE has 602 monthly rows across that span) |
| `data_time_period` (meta) | 2023-04-01 → 2023-08-31 (epoch); actual rows extend well beyond this — meta is stale |
| last updated (`changed`) | epoch 1782061218 ≈ 2026-06 (recently refreshed) |
| direct file | `https://data.gov.in/files/ogd20/ogdpv2dms/s3fs-public/NREGA.csv` |

**Verbatim column names (all 35):**
`fin_year`, `month`, `state_code`, `state_name`, `district_code`, `district_name`,
`Approved_Labour_Budget`, `Average_Wage_rate_per_day_per_person`,
`Average_days_of_employment_provided_per_Household`, `Differently_abled_persons_worked`,
`Material_and_skilled_Wages`, `Number_of_Completed_Works`, `Number_of_GPs_with_NIL_exp`,
`Number_of_Ongoing_Works`, `Persondays_of_Central_Liability_so_far`, `SC_persondays`,
`SC_workers_against_active_workers`, `ST_persondays`, `ST_workers_against_active_workers`,
`Total_Adm_Expenditure`, `Total_Exp`, `Total_Households_Worked`, `Total_Individuals_Worked`,
`Total_No_of_Active_Job_Cards`, `Total_No_of_Active_Workers`,
`Total_No_of_HHs_completed_100_Days_of_Wage_Employment`, `Total_No_of_JobCards_issued`,
`Total_No_of_Workers`, `Total_No_of_Works_Takenup`, `Wages`, `Women_Persondays`,
`percent_of_Category_B_Works`, `percent_of_Expenditure_on_Agriculture_Allied_Works`,
`percent_of_NRM_Expenditure`, `percentage_payments_gererated_within_15_days`, `Remarks`.

### Starter-metric mapping (verbatim source field → canonical) — feeds Stage 2
| canonical (starter) | SRC_OGD verbatim field | note |
|---|---|---|
| `persondays_generated` | `Persondays_of_Central_Liability_so_far` | ⚠ likely **cumulative YTD**, not monthly — see §4 / OQ-OGD-1 |
| `avg_wage_rate_per_day` | `Average_Wage_rate_per_day_per_person` | INR; high precision (e.g. `245.41163886348`) |
| `total_expenditure` | `Total_Exp` | unit assumed INR lakhs (e.g. `3884.10`) — confirm (OQ-OGD-2). Components also present: `Wages`, `Material_and_skilled_Wages`, `Total_Adm_Expenditure` → enables R4-DEF-01 derive-and-compare |

The remaining 6 canonical metrics are also present here (for the later slice):
`Total_Households_Worked`, `Total_No_of_HHs_completed_100_Days_of_Wage_Employment`,
`Total_No_of_Active_Workers`, `Wages`, `Material_and_skilled_Wages`, `Total_Adm_Expenditure`.

---

## 4. Findings / caveats (real, surfaced — not papered over)

- **Grain LOCKED-requirement: SATISFIED for OGD.** Despite the dataset's `granularity`
  metadata label being "Daily", the actual rows are **district + monthly** (`fin_year`+`month`).
  Evidence: a single district (PUNE) returns 602 rows across distinct (fin_year, month) pairs
  spanning 2018-19 to 2025-26. So the monthly-grain STOP condition (OQ-3 in stage0-todo) does
  **not** trigger for SRC_OGD. (The "granularity" metadata field is unreliable platform-wide.)
- **⚠ persondays is cumulative-within-FY, not discrete-monthly (OQ-OGD-1).** Field is named
  `…_so_far` and rises monotonically through the FY for a fixed district (PUNE 2024-25: Dec
  488,238 < Jan 558,170 < Feb 663,695). To get a discrete month's persondays you'd difference
  consecutive months. This is a genuine harmonization decision (Stage 4), and it also affects
  how the divergence check (T0.3) compares persondays across sources. **Flagging, not resolving.**
- **Duplicate/near-duplicate rows.** PUNE 2024-25 "Jan" appears twice with slightly different
  values (558,170 vs 552,427) — likely snapshot revisions returned by the API. Stage 1 will
  need a dedupe/latest-snapshot rule; noting here as a data-quality reality.
- **Missing values** present as the literal string `"NA"` (e.g. `Remarks: "NA"`) — must map to
  `null`, never 0 (RULES R4-FMT-01).
- **Discovery is backend-dependent.** Because api.data.gov.in/catalog is dead and the package
  sync times out, the dataset registry must be built via `…/backend/dmspublic/v1/resources?query=`.
  The T0.2 fetch script can hardcode the one shortlisted resource id; full re-discovery uses §1.

---

## 5. SRC_SYNC (DeshSeva / dataful) — PENDING
Not investigated in this pass. Next: confirm live site, access method (API vs scrape),
verbatim field names for the 3 starter metrics, geo/period fields, and its own sync/as-of date
(DeshSeva reportedly warns its syncs lag). `deshseva.in/tools/mgnrega` surfaced in search as a
starting point.

## 6. SRC_MIS (nrega.nic.in) — PENDING
Not investigated in this pass. Known to be JS-rendered/operational; sequenced last. Next:
locate the district-monthly report page, record on-page field labels, note rendering blocker.

---

## 7. OPEN QUESTIONS (surface before T0.2)
- **OQ-OGD-1 — persondays semantics:** is `Persondays_of_Central_Liability_so_far` cumulative
  YTD (evidence says yes)? If so, the canonical `persondays_generated` (monthly) must be
  derived by differencing — a Stage 4 rule, and it changes what T0.3 compares. Confirm intent.
- **OQ-OGD-2 — expenditure unit:** confirm `Total_Exp` / `Wages` / `Material_and_skilled_Wages`
  / `Total_Adm_Expenditure` are INR **lakhs** (assumed from magnitude) before any R4-UNIT-01 work.
- **OQ-OGD-3 — shortlist size:** is a single OGD dataset (the flagship) an acceptable SRC_OGD
  shortlist for v1, given it already carries all 9 metrics at district+monthly grain? (I
  recommend yes — the other ~129 are one-off parliamentary tables.) **Proposing, not settling.**
