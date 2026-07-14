# Reproducibility

## The claim, precisely

The pipeline runs **entirely offline** against the local raw archive (`data/archive/`) and produces
the deliverables in `dist/v1.0/` **byte-for-byte identically on every run**. There is no network
dependency at build time (the data.gov.in portal is not a runtime dependency) and no wall-clock or
machine state enters the output: every dated field in the export (`source_as_of`) is read from the
archived source envelopes, not from the clock, and all rows are written in an explicit deterministic
sort order. Repeated runs therefore yield identical CSV, JSONL, and Parquet bytes.

This is enforced by the test suite, not just asserted:

- `tests/export/test_records.py` proves the serializers are byte-identical and the ordering is
  stable (hermetic, no archive needed).
- `tests/export/test_export_integration.py` (archive-gated) rebuilds the full series, writes it
  twice, and asserts the four deliverables are byte-identical across writes — including Parquet —
  and pins the documented row counts (state 4,219 · national 148 · district 57,181 · lineage
  61,548) and the headline reconciliation facts.

Scope note: byte-identity is over a **fixed archive**. If the archive contents change, the outputs
change — which is exactly why the frozen archive is part of the reproducibility story (see the fork
below). Parquet byte-identity holds for a given `pyarrow` version (pinned via `uv.lock`); CSV and
JSONL are unconditionally byte-identical.

## Environment

- **Python 3.12** (developed on 3.12.10).
- **uv** for dependency management, with `uv.lock` pinning every version (developed on uv 0.11.23).
- Runtime deps (pinned in `uv.lock`): `pydantic` and `httpx` for the pipeline; `duckdb` + `mcp` for
  the read-only serving layer; `langgraph` for the report analyst. **`pyarrow`** (dev group) is
  required only to write the `.parquet` files — CSV + `lineage.jsonl` are written without it.

## Steps

```bash
git clone <repo> && cd Data-Platform
uv sync                                             # install exact pinned versions (incl. pyarrow)
uv run ruff check . && uv run mypy src tests && uv run pytest   # gate: lint, types, full suite
data-platform-export                                # data/archive/ → dist/v1.0/
# or: data-platform-export <archive_dir> <out_dir>
```

`uv sync` installs the project itself (src layout, hatchling), so `data_platform` is on the import
path and the console commands — `data-platform-export`, `data-platform-mcp`, `data-platform-analyst`
and `data-platform-bootstrap` — are on `PATH`. Nothing needs a `PYTHONPATH=src` prefix any more; the
"proper package installation" chore that was queued for v1.1 is done.

**To SERVE the released dataset you do not need the raw archive at all.** `data-platform-bootstrap`
downloads the sealed v1.0.0 release (~5 MB), verifies the zip against the SHA-256 the release
published, verifies the seven extracted files against the manifest the server enforces at startup,
and installs them atomically to `dist/v1.0`. Rebuilding the dataset *from source* is the fork below,
and that does need the archive.

The archive-gated tests (and the export itself) **skip / cannot run** without the raw archive at
`data/archive/` — which is the fork below. The hermetic tests run everywhere.

---

## The raw archive in the deposit  — **Decision: Option A (include the frozen archive)**

The raw archive (`data/archive/`) is **required** to reproduce the series but is **gitignored** and
currently lives only on the maintainer's machine. The maintainer chose **Option A**: the frozen
archive snapshot is deposited alongside the code and outputs, so anyone can reproduce the series
exactly and offline. The two options are recorded below for the deposit record.

- **Total size: ~628 MB** — the API/JSON datasets (88 files), the file-only CSVs (41 files), and the
  LGD geography reference.
- The exported deliverables (`dist/v1.0/`) are ~66 MB (dominated by the ~56 MB `lineage.jsonl`); the
  release zip that `data-platform-bootstrap` fetches is ~5 MB compressed.

**Option A (recommended): include the frozen raw archive snapshot in the Zenodo deposit**, alongside
the code and the outputs. Anyone can then reproduce the series exactly, offline, forever — the
strongest possible reproducibility claim, and the one that matches this project's whole premise (a
concluded reference record). ~628 MB is well within Zenodo's per-record limit (50 GB). This is
permissible under **GODL-India**, which grants the right to *publish (original or adapted) … for all
lawful commercial and non-commercial purposes*, provided the attribution statement and non-endorsement
notice are carried (see `docs/notes/LICENSE-PROPOSAL.md`). The deposit would ship that attribution
statement at its root.

**Option B: deposit code + outputs only, with fetch instructions** to rebuild the archive from
data.gov.in. This is a **weaker** claim: portal availability is not guaranteed (data.gov.in throttles
some clients and datasets can be revised or withdrawn), so an exact rebuild is not assured — the
determinism guarantee above only holds *given the same archive*, which Option B cannot promise.

**Chosen: A** — full, durable reproducibility, and GODL-India permits the redistribution. The frozen
`data/archive/` snapshot (~628 MB) is uploaded to the Zenodo deposit alongside `dist/v1.0/` and the
code, with the GODL-India attribution statement (`LICENSE-DATA`) at the deposit root. See
`docs/notes/RELEASE-v1.0.0.md` (Route 2) for the manual-deposit steps.

### Mirrors

The frozen raw archive and the exported deliverables are available from two verified,
checksum-identical mirrors: (a) the **GitHub Release v1.0.0 assets**
(https://github.com/Prateek718/Data-Platform/releases/tag/v1.0.0), and (b) the **Zenodo deposit**
(https://doi.org/10.5281/zenodo.21318927, version DOI). Both carry the same SHA-256 checksums,
published in the release notes and in `SHA256SUMS.txt` within each mirror. Cite the version DOI
(`10.5281/zenodo.21318927`) for reproducibility; the concept DOI (`10.5281/zenodo.21318431`) always
resolves to the latest release.

Zenodo internally labels this deposit **"Version v2"** — an artifact of the initial upload being
code-only and a second version being published with the full frozen archive + `dist/` outputs added.
That is Zenodo's own record versioning and is unrelated to the dataset's release versioning, which
remains **v1.0.0**.
