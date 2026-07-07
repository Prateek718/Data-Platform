# Licensing proposal & decision record

> **RESOLVED (2026-07-06).** The maintainer chose: **code → MIT** (`LICENSE`); **derived dataset →
> CC BY 4.0** with the GODL-India attribution statement (`LICENSE-DATA`). This document is retained
> as the decision record and the verified reference for the upstream GODL-India terms below.

This repository contains two different kinds of work that are conventionally licensed separately:

1. **The code** — the pipeline, export, and tests (original authorship).
2. **The derived dataset** — `dist/v1.0/` (CSV/Parquet/lineage), a reconciled derivative of
   government data published on data.gov.in under the **Government Open Data License – India
   (GODL-India)**.

The standard pattern is a permissive code license + an open-data license for the dataset, with an
attribution statement satisfying the upstream GODL-India terms.

---

## Part 1 — Code license  **[DECIDE: MIT vs Apache-2.0]**

**Recommended: MIT** — shortest, most permissive, ubiquitous for tooling and portfolio work; no
patent clause to reason about. **Alternative: Apache-2.0** — same permissive posture but adds an
explicit patent grant and a NOTICE mechanism; slightly heavier. There are no patents at stake here,
so MIT is the leaner fit; choose Apache-2.0 if you prefer the explicit patent grant.

Draft `LICENSE` (MIT), ready to commit if chosen:

```
MIT License

Copyright (c) 2026 Prateek

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

(If Apache-2.0 is preferred, use the standard Apache-2.0 text with the same copyright line and add a
`NOTICE` file.)

---

## Part 2 — Dataset license  **[DECIDE: confirm CC BY 4.0 for the derived dataset]**

**Recommended: CC BY 4.0** for the derived dataset in `dist/v1.0/`, with the GODL-India attribution
statement below.

**Why this is defensible.** GODL-India grants a *worldwide, royalty-free, non-exclusive* license to
"use, adapt, publish … translate, add value, and create derivative works … for all lawful commercial
and non-commercial purposes." It is **attribution + non-endorsement**, with **no share-alike**
requirement, so it is broadly compatible with releasing a *derived* dataset under CC BY 4.0 provided
the upstream GODL-India sources remain attributed. This is the maintainer's (or legal counsel's) call
to confirm — the platform does not assert it as settled law.

### Draft attribution statement (satisfies GODL-India §4.a and §4.c)

> This dataset is a reconciled derivative of MGNREGA data published on the Open Government Data (OGD)
> Platform India (https://data.gov.in) by the Ministry of Rural Development (MoRD), the Ministry of
> Statistics and Programme Implementation (MoSPI), and Rajya Sabha parliamentary answers, licensed
> under the Government Open Data License – India (GODL-India,
> https://data.gov.in/government-open-data-license-india). The original data providers do not
> endorse this derivative work or its author. The data is provided "as is", without warranty of any
> kind. The specific source resource identifiers for every fact are recorded in
> `dist/v1.0/lineage.jsonl` (`contributing_resource_ids`), satisfying GODL-India's requirement to
> publish the source URL/URI of each dataset used (§4.b permits a linked list for multiple sources).

---

## GODL-India — the exact upstream requirements (verified from the license text)

The raw sources are governed by GODL-India; any release of the derived dataset must carry these
forward. Verified terms:

- **Rights granted (§3):** a worldwide, royalty-free, non-exclusive license to *use, adapt, publish
  (original or adapted/derivative), translate, display, add value, and create derivative works
  (including products and services), for all lawful commercial and non-commercial purposes.*
- **Attribution (§4.a):** the user *must acknowledge the provider, source, and license of data by
  explicitly publishing the attribution statement, including the DOI, URL, or URI of the data
  concerned.*
- **Multiple data (§4.b):** where listing every source is impractical, the user *may provide a link
  to a separate page/list that includes the attribution statements and specific URL/URI of all data
  used* — which is exactly what `lineage.jsonl` provides.
- **Non-endorsement (§4.c):** the user *must not indicate or suggest in any manner that the data
  provider(s) endorses their use and/or the user.*
- **No warranty / liability (§4.d):** the data provider(s) are *not liable for any errors or
  omissions … any direct, indirect, special, incidental or consequential loss … caused by its use.*
- **Exemptions (§6):** personal/sensitive information, official symbols/logos, IP-protected content,
  and identity documents are out of scope — none of which appear in this aggregate statistical data.
- **Governing law (§9):** Indian law.

Sources: [GODL-India (Punjab OGD mirror)](https://punjab.data.gov.in/Godl),
[GODL-India (data.gov.in)](https://www.data.gov.in/government-open-data-license-india),
[Template:GODL-India (Wikipedia)](https://en.wikipedia.org/wiki/Template:GODL-India).

---

## What I will do once you decide

1. Commit `LICENSE` with your chosen code license (MIT draft above, or Apache-2.0).
2. Add `LICENSE-DATA` (CC BY 4.0 full text) + the attribution statement, if you confirm CC BY 4.0.
3. Update the README "License" section and `CITATION.cff` `license:` field to match.
