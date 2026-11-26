# AI Research Assistant — Retrieval Foundation (Phase 1) and Tools (Phase 2)

## Status: what exists and what does not

| Capability | Status |
|---|---|
| Read-only extraction of Nobel Explorer data into retrieval documents | **Implemented (Phase 1)** |
| Token-aware chunking for `all-MiniLM-L6-v2` | **Implemented (Phase 1)** |
| Local embeddings (Sentence Transformers, CPU, no paid API) | **Implemented (Phase 1)** |
| Persistent ChromaDB index with idempotent sync | **Implemented (Phase 1)** |
| `search_nobel_knowledge()` semantic retrieval with filters | **Implemented (Phase 1)** |
| Retrieval evaluation (Hit@3, Recall@5, MRR@10, latency) | **Implemented (Phase 1)** |
| Optional document de-duplication and provisional weak-match flag | **Implemented (Phase 2)** — retrieval defaults unchanged |
| Four validated, read-only LangChain tools (`search_laureates`, `get_laureate_details`, `get_nobel_statistics`, `search_nobel_knowledge`) | **Implemented (Phase 2)** — directly invocable, no LLM |
| Scripted tool evaluation (30 cases) | **Implemented (Phase 2)** — measures tool correctness, *not* LLM tool selection |
| LLM answer generation / OpenAI tool calling / autonomous agent | Planned (Phase 3) — **no LLM is instantiated and no LLM calls exist yet** |
| `/ai/chat` API endpoint and frontend assistant page | Planned (Phase 3–4) |
| Docker / Railway deployment of the AI stack | Planned (Phase 5) — Dockerfiles are unchanged |

Phases 1–2 do not change existing routes, frontend, Dockerfiles or database
schema. `langchain-core` is used only for tool definitions; the OpenAI
packages in `requirements-ai.txt` are not imported.

## Architecture

```
MySQL (existing models / repositories / services, READ ONLY session)
   │  documents.py   build_all_documents()          → 1,050 SourceDocument
   ▼
chunking.py   chunk_documents(count_tokens=model tokenizer) → 1,064 Chunk (≤256 tokens)
   ▼
embeddings.py SentenceTransformerEmbedder (all-MiniLM-L6-v2, 384-d, L2-normalised)
   ▼
vector_store.py NobelVectorStore.sync()  → ChromaDB PersistentClient, cosine space
   ▼                                        ai_index/chroma  (+ ai_index/index_manifest.json)
retrieval.py  search_nobel_knowledge(query, level, laureate_id, k) → SearchResponse
   ▼
evaluation/run_retrieval_eval.py  → Hit@3 / Recall@5 / MRR@10 / latency
```

| Module | Responsibility |
|---|---|
| `backend/ai/config.py` | Embedding, chunking, index and retrieval settings (env-overridable); citation-status vocabulary |
| `backend/ai/documents.py` | Read-only extraction into `SourceDocument`s with deterministic IDs and provenance metadata |
| `backend/ai/chunking.py` | Sentence-aware, token-validated, deterministic chunking with overlap |
| `backend/ai/embeddings.py` | `SentenceTransformerEmbedder`; test-only `HashingEmbedder` |
| `backend/ai/vector_store.py` | Chroma collection lifecycle, embedding-fingerprint guard, metadata validation, idempotent sync |
| `backend/ai/build_index.py` | CLI: extract → chunk → sync → reopen check → manifest |
| `backend/ai/retrieval.py` | Validated semantic search returning scores, metadata, source and citation status |
| `backend/ai/evaluation/` | Ground-truth question set and metrics runner |

### Identifiers (deterministic)

| Document | ID | Basis |
|---|---|---|
| Laureate record | `laureate:nobel-<nobel_laureate_id>` | Official Nobel API id (stable across databases) |
| Contribution | `contribution:<contribution_id>` | Database primary key |
| Explanation | `explanation:<contribution_id>:<level>` | Unique (contribution, level) constraint |
| Connection | `connection:<connection_id>` | Database primary key |
| Chunk | `<doc_id>#c<n>` | Position within parent document |

Each chunk stores a `content_hash` (SHA-256 of chunk text + metadata). Sync
re-embeds only chunks whose hash changed and deletes chunks whose source
records disappeared.

### Citation status (provenance, not truth)

| Value | Used for | Meaning |
|---|---|---|
| `source_linked` | Contributions, connections with a stored URL | The record stores its own `source_name` / `source_url`. The URL is a reference page for the record; individual sentences are not verified. |
| `structured_record` | Laureate records | Fields imported from the Nobel Prize API by the ETL. No per-record URL is stored, so **no URL is reported** (none is invented). |
| `unverified_educational` | Explanations (and any record without a URL) | Authored teaching text with no stored citation. The parent contribution's URL is exposed as `related_source_*` — **context only, not a citation**. |

### Retrieval scores

* `distance` — cosine distance reported by Chroma. **Lower = more similar.**
* `similarity` — `1 - distance` (cosine similarity). **Higher = more similar.**
* Results are nearest neighbours, not verified evidence. Filters can force
  irrelevant matches (observed: similarity −0.07 when filtering Expert-level
  content of an mRNA laureate for "photoelectric effect"). Optional
  `min_similarity` drops weak matches.
* `level` restricts results to explanations at that level; `laureate_id`
  (internal Nobel Explorer id) matches chunks whose `laureate_ids` list
  contains it; `k` is limited to 1–10; queries to 1–500 characters.
* Invalid input raises `SearchValidationError` (a subclass of the existing
  `ServiceValidationError`, so it maps to HTTP 400 in the existing app).

## Data (verified 2026-11-26)

Live development database (`nobel-mysql-compose`, MySQL 8.4.11, port 9303)
matched the `docker/mysql/nobel_explorer.sql` dump exactly for all 12 tables
(Alembic head `c4e8a21d6f09`).

| Table | Rows | | Documents | Chunks |
|---|---|---|---|---|
| laureate | 1,018 | → | 1,018 laureate records | 1,018 |
| laureate_prize (motivations) | 1,026 | merged into laureate records | | |
| award_affiliation / institution | 847 / 358 | merged into laureate records | | |
| contribution | 4 | → | 4 | 5 |
| explanation (4 contributions × 4 levels) | 16 | → | 16 | 29 |
| connection | 12 | → | 12 | 12 |
| **Total** | | | **1,050** | **1,064** |

## Configuration

| Setting | Value |
|---|---|
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` |
| Dimensions | 384 (verified) |
| Normalisation | `normalize_embeddings=True` (the model also ends with a `Normalize` module); unit length verified |
| Max sequence length | 256 tokens incl. `[CLS]`/`[SEP]` (model tokenizer limit; longer input would be truncated) |
| Chunk size / overlap | 900 / 150 characters (`AI_CHUNK_SIZE`, `AI_CHUNK_OVERLAP`) |
| Token ceiling | 256 (`AI_CHUNK_MAX_TOKENS`); measured max chunk 202, mean 73.7 |
| Distance | cosine (explicit `configuration={"hnsw": {"space": "cosine"}}`) |
| Index location | `ai_index/chroma` (`AI_CHROMA_DIR`), collection `nobel_knowledge` |

## Measurements

Benchmark environment: Apple M1 Pro (8 cores, 16 GB), macOS 26.5.1,
Python 3.12.15, CPU inference, torch 2.15.0, chromadb 1.5.9. Single runs;
timings vary between runs and will differ on Railway hardware.

| Measurement | Value |
|---|---|
| Full rebuild (`--rebuild`), wall clock | 9.85 s |
| Embedding 1,064 chunks | 2.61 s |
| Model load (cached weights) | 3.5–4.8 s |
| Extraction + chunking | ≈0.4 s |
| Peak resident memory during rebuild | ≈1.0 GB |
| Index size on disk | 10,053,360 bytes (9.7 MB) |
| Re-run without changes | 0 added / 0 updated / 1,064 unchanged / 0 deleted; 0 embedded |
| Persistence | Fresh client reopened 1,064 chunks, distance space `cosine` |

## Retrieval evaluation

Dataset: `backend/ai/evaluation/retrieval_eval_set.json` — 22 in-scope
questions (photoelectric effect, general relativity, mRNA, click chemistry,
prize motivations; direct, paraphrased and level-filtered) and 6
out-of-scope questions. Relevant document IDs were fixed **before** the
first retrieval run.

**Relevance level:** ranking is chunk-level (top-10 chunks); relevance is
judged at **parent-document level** (each chunk maps to its `doc_id`). It is
not contribution-level: `contribution:38` and `explanation:38:simple` are
distinct documents. Two chunks of the same document take two rank positions
but count once toward recall.

| Scope | n | Hit@3 | Recall@5 | MRR@10 |
|---|---|---|---|---|
| **All in-scope** | 22 | **0.955** | **0.771** | **0.811** |
| General relativity | 4 | 1.00 | 0.95 | 1.00 |
| Photoelectric effect | 5 | 1.00 | 0.76 | 0.90 |
| mRNA | 3 | 1.00 | 0.67 | 1.00 |
| Prize motivations | 6 | 1.00 | 0.86 | 0.81 |
| Click chemistry | 4 | 0.75 | 0.55 | 0.375 |

Metrics were reproduced identically across two runs and by an independent
recomputation from the per-question results.

Latency (`search_nobel_knowledge`, all 28 queries, warm): mean ≈9 ms;
p50 8–9 ms; p95 11–15 ms across runs.

### Known retrieval failures

1. **Year + category questions** — "Who won the 2022 Nobel Prize in
   Chemistry?" retrieves no relevant document in the top 10 *semantically*.
   **Resolved in Phase 2 by the structured `search_laureates` tool**, which
   returns Carolyn R. Bertozzi, K. Barry Sharpless and Morten Meldal from SQL.
2. **Duplicate chunks** — multi-chunk documents can occupy several top-5
   slots. **Phase 2 adds optional per-document de-duplication** (Recall@5
   0.7712 → 0.8167; see below).
3. **Applications outrank definitions** — for "What is click chemistry?" and
   "What is the photoelectric effect?", application documents still rank
   above the core explanation (unchanged by de-duplication).
4. **Out-of-scope detection** — "Who won the Nobel Prize in Mathematics in
   1950?" scores **0.66** and is *not* flagged weak. Only structured
   validation catches it (`search_laureates` rejects the category).

## Phase 2: tool layer (`backend/ai/tools/`)

```
LLM (Phase 3, not built) ──► LangChain StructuredTool (name, description, args_schema)
                                   │  Pydantic validation (schemas.py) ─► error envelope on failure
                                   ▼
                    run_safely (results.py): JSON envelope, safe errors, no tracebacks
                 ┌─────────────────┼──────────────────────┬─────────────────────────┐
     search_laureates     get_laureate_details    get_nobel_statistics     search_nobel_knowledge
     (structured.py)      (structured.py)         (statistics.py)          (semantic.py)
     laureate_service     laureate/contribution/  analytics_service +      Phase 1 retrieval
                          explanation/connection  analytics_repository     (Chroma, MiniLM)
                          services
                 └──────── read-only session (ToolContext → Phase 1 read_only_session) ─┘
```

| Module | Responsibility |
|---|---|
| `schemas.py` | Pydantic input models: categories (6, with aliases), years 1901–current, bounded limits, country/gender normalisation, LIKE-wildcard rejection, per-operation filter rules, `extra="forbid"` |
| `structured.py` | `search_laureates`, `get_laureate_details` over existing services; matched vs other awards; birth vs affiliation country; honest empty results |
| `statistics.py` | `get_nobel_statistics`: 9 allow-listed operations, each with metric definition and counting unit |
| `semantic.py` | Compact wrapper over `search_nobel_knowledge` (dedupe on by default for the tool) |
| `results.py` | `{"tool", "ok", "data"}` / `{"tool", "ok": false, "error": {"type", "message"}}` envelopes; credential-safe error translation; JSON round-trip |
| `context.py` | `ToolContext` (session factory + index provider); refuses to create an index on read |
| `langchain_tools.py` | `StructuredTool.from_function` definitions with explicit `args_schema` and `handle_validation_error` |
| `registry.py` | Exactly four tools, in a fixed order |

### The four tools

| Tool | Use when | Arguments (required in bold) |
|---|---|---|
| `search_laureates` | Exact "who won" lookups; obtaining `laureate_id`s | `name`, `year`, `category`, `birth_country`, `gender`, `limit` (≥1 filter) |
| `get_laureate_details` | One known laureate: awards, motivations, affiliations, educational content | **`laureate_id`**, `include_explanation_level` |
| `get_nobel_statistics` | "How many" / trend questions | **`operation`**, `category`, `start_year`, `end_year`, `affiliation_country`, `limit` |
| `search_nobel_knowledge` | "Explain / how / why" questions | **`query`**, `level`, `laureate_id`, `k`, `dedupe_by_document` |

Statistics operations and counting units: `summary` (distinct laureates,
laureate-prize awards, persons vs organizations, prizes, birth countries,
women %), `laureates_by_category` (distinct laureates), `laureates_by_gender`
(distinct persons), `prizes_by_decade` (prizes), `laureates_by_decade`
(distinct laureates), `top_birth_countries` (distinct persons, ties
alphabetical), `women_by_era` (distinct known-gender persons),
`average_age_at_award` (age observations), `laureates_by_affiliation_institution`
(distinct laureates, by *institution* country). In the live database:
1,018 distinct laureates (990 persons, 28 organizations), 1,026 awards and 633 prizes.

### De-duplication benchmark (same 22 questions)

| | Hit@3 | Recall@5 | MRR@10 |
|---|---|---|---|
| Baseline (default, unchanged) | 0.9545 | 0.7712 | 0.8106 |
| `dedupe_by_document=True` | 0.9545 | **0.8167** | 0.8106 |

4 questions improved Recall@5 (pe-1 0.2→0.4, gr-1 0.8→1.0, mrna-1 0.4→0.8,
mrna-2 0.6→0.8); 18 unchanged; none got worse on any metric. With
de-duplication, the top-5 holds five *distinct* documents, so Recall@5
measures document coverage rather than chunk repetition; the trade-off is
that other relevant chunks of the same document are hidden. Latency was
within run-to-run noise (mean ≈8–12 ms either way). All values were
recomputed independently from the saved per-question results.

**When can de-duplication not lower Hit@3, Recall@5 or MRR@10?** The
de-duplicated list is the *first occurrence of each document* in a candidate
list of `max(k, min(4k, 40))` chunks. Every document's rank can then only
stay the same or improve, so document-level metrics cannot decrease,
**provided that**:

1. **Same candidate ordering** — the first k chunks of the larger
   (over-fetched) query equal the baseline top-k. Approximate (HNSW) search
   could break this if `n_results` exceeded `ef_search` (100 here; we fetch
   ≤ 40) or with exact distance ties. Verified empirically on all 28
   evaluation queries: 28/28 prefix-consistent, 0 ties.
2. **At least k candidates** — guaranteed by `max(k, …)`. A configured cap
   below k would otherwise shrink the pool (fixed during the Phase 2 review;
   regression-tested).
3. **Same filters and index** in both runs (the evaluation uses identical
   `level` filters and the same collection).
4. **Relevance at document level or coarser** (document, contribution).
   With **chunk-level** relevance, de-duplication *can* lower recall by
   hiding a relevant second chunk of an already-listed document.
5. `min_similarity` does not break it: a document whose best chunk is below
   the threshold has all of its chunks below it.

### Weak-evidence indicator (provisional threshold 0.40, not calibrated)

| Query | Top similarity | `all_results_weak` |
|---|---|---|
| Explain the photoelectric effect simply | 0.738 | false |
| "photoelectric effect" + level Expert + Karikó (incompatible filters) | −0.075 | **true** |
| Sourdough recipe | 0.188 | **true** |
| 2022 FIFA World Cup | 0.333 | **true** |
| Bitcoin price | 0.125 | **true** |
| **Nobel Prize in Mathematics 1950 (false premise)** | **0.660** | **false** |

Results are flagged, never discarded. The false premise shows why the
flag is not enough: structured validation (`search_laureates` rejects
"Mathematics") and evidence inspection remain necessary.

### Scripted tool evaluation

`backend/ai/evaluation/tool_eval_set.json`: 30 cases (exact structured 6,
details 3, statistics 6, semantic 4, multi-step 3, ambiguous 2, false
premise 2, unsupported category 1, out-of-scope 3). Expected values were
derived with independent raw SQL before running the tools. The runner
invokes the **expected** tools directly: **30/30 passed**. This verifies
tool correctness only; it is **not** LLM tool-selection accuracy (Phase 3).

### Phase 2 review corrections

| Issue | Fix | Regression test |
|---|---|---|
| `default_store_provider(config)` checked a custom index directory but then returned the cached **default** store | Build the store from the checked config | `test_custom_index_config_is_actually_used` |
| A de-duplication cap configured below `k` could shrink the candidate pool under the baseline | Candidates = `max(k, min(4k, 40))` | `test_dedupe_never_fetches_fewer_candidates_than_k` |
| Tool JSON schemas emitted non-standard `ge`/`le` | `Field(...)` before `BeforeValidator` | `test_schemas_use_standard_json_schema_bounds` |
| `get_laureate_details` description lacked *when* to use it | Description rewritten | `test_tool_schema_and_description` |
| Importing `tools.schemas` required LangChain | Lazy package exports | base-`.venv` test run |
| Hard-coded level order in `structured.py` | Uses `EDUCATIONAL_LEVELS` | existing details tests |

## Tests

| Suite | Command | Result |
|---|---|---|
| AI unit tests (SQLite fixtures, `HashingEmbedder` — **not** semantic validation) | `pytest backend/ai/tests` | **243 passed**, 16 skipped (gated) — 80 Phase 1 + 163 Phase 2 |
| Real model + live DB integration | `AI_RUN_REAL_MODEL_TESTS=1 AI_RUN_LIVE_DB_TESTS=1 pytest backend/ai/tests -m "real_model or live_db"` | **16 passed** (9 Phase 1 + 7 Phase 2): 6 real-model, 9 live read-only DB, 1 both |
| Existing backend/ETL suite (isolated restored DB `nobel_explorer_ai_test`) | `pytest backend ETL --ignore=backend/ai` | 297 passed in both `.venv` and `.venv-ai` |
| AI tests in the base `.venv` (no AI packages) | `pytest backend/ai` | schema and Phase 1 tests run; AI-dependent tests skip cleanly |

## Reproduce

```bash
# 1. Separate environment (existing .venv untouched)
python3.12 -m venv .venv-ai
.venv-ai/bin/python -m pip install -r requirements-ai.txt

# 2. Point at a development database (example: compose MySQL on 9303).
#    Values come from .env.docker; nothing is printed.
docker start nobel-mysql-compose
set -a; . ./.env.docker; set +a
export DB_HOST=127.0.0.1 DB_PORT=9303 TOKENIZERS_PARALLELISM=false

# 3. Build / sync the index
.venv-ai/bin/python -m backend.ai.build_index --dry-run   # extract + chunk only
.venv-ai/bin/python -m backend.ai.build_index             # idempotent sync
.venv-ai/bin/python -m backend.ai.build_index --rebuild   # drop and recreate

# 4. Evaluate retrieval (baseline, and baseline vs de-duplicated)
.venv-ai/bin/python -m backend.ai.evaluation.run_retrieval_eval --output ai_index/eval_results.json
.venv-ai/bin/python -m backend.ai.evaluation.run_retrieval_eval --compare-dedupe --output ai_index/dedupe_comparison.json

# 5. Scripted tool evaluation
.venv-ai/bin/python -m backend.ai.evaluation.run_tool_eval --output ai_index/tool_eval_results.json

# 6. Use a tool directly (no LLM)
.venv-ai/bin/python -c "from backend.ai.tools import get_tool_registry; \
print(get_tool_registry()['search_laureates'].invoke({'year': 2022, 'category': 'Chemistry'}))"

# 7. Tests
.venv-ai/bin/python -m pytest backend/ai/tests -q
AI_RUN_REAL_MODEL_TESTS=1 AI_RUN_LIVE_DB_TESTS=1 \
  .venv-ai/bin/python -m pytest backend/ai/tests -q -m "real_model or live_db"
```

Generated files (`ai_index/`), environments (`.venv-*/`) and model caches are
git-ignored. The model downloads (≈92 MB) to the Hugging Face cache on first use;
the first knowledge-tool call in a process loads it (≈4–5 s), later calls take ~10–25 ms.

## Limitations

* Deep educational content covers only 4 contributions and 6 laureates;
  ~1,000 laureates are represented by structured data and one motivation.
* Explanations have no stored citations; category descriptions are empty.
* Long sentences make overlap fall back to word level, so some chunks start
  mid-sentence (each still carries its title header).
* Content-hash sync must be run with the full corpus (partial input deletes
  missing chunks by design).
* Country filters match stored Nobel API names ("USA", "the Netherlands");
  only a few unambiguous aliases are mapped, and historical names
  (e.g. "Russian Empire" for Marie Curie) are not mapped to modern countries.
* Name search is a substring match; accent-insensitivity depends on the
  MySQL collation (true for the current `utf8mb4_0900_ai_ci`).
* The weak-match threshold (0.40) is provisional and uncalibrated.
* Each tool call opens a short-lived read-only engine (NullPool); fine for an
  assistant, not tuned for high request rates.
* The local Homebrew MySQL on port 3306 rejects the `.env` credentials
  (error 1045); development used the compose database on port 9303.

## Deployment considerations (not yet applied)

* Linux `torch` from PyPI pulls CUDA libraries; use the CPU wheel index and
  re-resolve `requirements-ai.txt` inside `python:3.12-slim`.
* Bake the model into the image (or a volume) to avoid runtime downloads.
* ≈1 GB peak memory while embedding — check the Railway plan.
* Railway's filesystem is ephemeral: rebuild the index at startup (~10 s) or
  mount a volume.
* Use a dedicated SELECT-only MySQL user for AI access (tools already run in READ ONLY sessions).
* Keep Chroma telemetry disabled (already set in code).
