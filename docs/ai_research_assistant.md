# AI Research Assistant — Phase 1: Retrieval Foundation

## Status: what exists and what does not

| Capability | Status |
|---|---|
| Read-only extraction of Nobel Explorer data into retrieval documents | **Implemented (Phase 1)** |
| Token-aware chunking for `all-MiniLM-L6-v2` | **Implemented (Phase 1)** |
| Local embeddings (Sentence Transformers, CPU, no paid API) | **Implemented (Phase 1)** |
| Persistent ChromaDB index with idempotent sync | **Implemented (Phase 1)** |
| `search_nobel_knowledge()` semantic retrieval with filters | **Implemented (Phase 1)** — a Python function, not yet an HTTP endpoint |
| Retrieval evaluation (Hit@3, Recall@5, MRR@10, latency) | **Implemented (Phase 1)** |
| LangChain tools (`search_laureates`, `get_laureate_details`, `get_nobel_statistics`) | Planned (Phase 2) |
| LLM answer generation / OpenAI tool calling / agent | Planned (Phase 2–3) — **no LLM calls exist yet** |
| `/ai/chat` API endpoint and frontend assistant page | Planned (Phase 3–4) |
| Docker / Railway deployment of the AI stack | Planned (Phase 5) — Dockerfiles are unchanged |

Phase 1 does not change existing routes, frontend, Dockerfiles or database
schema. LangChain and OpenAI packages are installed in `requirements-ai.txt`
for later phases but are not imported by Phase 1 code.

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
   Chemistry?" retrieved no relevant document in the top 10. The embedding
   model does not represent years/categories precisely. → Phase 2
   `search_laureates` (SQL filters) must handle these.
2. **Duplicate chunks** — multi-chunk documents (e.g. `explanation:38:expert`)
   can occupy several top-5 slots, lowering Recall@5. → Optional per-document
   de-duplication.
3. **Applications outrank definitions** — for "What is click chemistry?" and
   "What is the photoelectric effect?", connection/application documents rank
   above the core explanation.
4. **Out-of-scope detection** — 5 of 6 out-of-scope questions had top-1
   similarity 0.12–0.33 (in-scope minimum 0.49), but "Who won the Nobel
   Prize in Mathematics in 1950?" scored **0.66**. A similarity threshold
   (0.35–0.45 separated this small sample) cannot catch Nobel-sounding but
   unanswerable questions; the agent must reason about them.

## Tests

| Suite | Command | Result |
|---|---|---|
| AI unit tests (SQLite fixtures, `HashingEmbedder` — **not** semantic validation) | `pytest backend/ai/tests` | 80 passed, 9 skipped (gated) |
| Real model + live DB integration | `AI_RUN_REAL_MODEL_TESTS=1 AI_RUN_LIVE_DB_TESTS=1 pytest backend/ai/tests -m "real_model or live_db"` | 9 passed |
| Existing backend/ETL suite (isolated restored DB `nobel_explorer_ai_test`) | `pytest backend ETL --ignore=backend/ai` | 297 passed in both `.venv` and `.venv-ai` |

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

# 4. Evaluate retrieval
.venv-ai/bin/python -m backend.ai.evaluation.run_retrieval_eval --output ai_index/eval_results.json

# 5. Tests
.venv-ai/bin/python -m pytest backend/ai/tests -q
AI_RUN_REAL_MODEL_TESTS=1 AI_RUN_LIVE_DB_TESTS=1 \
  .venv-ai/bin/python -m pytest backend/ai/tests -q -m "real_model or live_db"
```

Generated files (`ai_index/`), environments (`.venv-*/`) and model caches are
git-ignored. The model downloads (≈92 MB) to the Hugging Face cache on first use.

## Limitations

* Deep educational content covers only 4 contributions and 6 laureates;
  ~1,000 laureates are represented by structured data and one motivation.
* Explanations have no stored citations; category descriptions are empty.
* Long sentences make overlap fall back to word level, so some chunks start
  mid-sentence (each still carries its title header).
* Content-hash sync must be run with the full corpus (partial input deletes
  missing chunks by design).
* The local Homebrew MySQL on port 3306 rejects the `.env` credentials
  (error 1045); Phase 1 used the compose database on port 9303.

## Deployment considerations (not yet applied)

* Linux `torch` from PyPI pulls CUDA libraries; use the CPU wheel index and
  re-resolve `requirements-ai.txt` inside `python:3.12-slim`.
* Bake the model into the image (or a volume) to avoid runtime downloads.
* ≈1 GB peak memory while embedding — check the Railway plan.
* Railway's filesystem is ephemeral: rebuild the index at startup (~10 s) or
  mount a volume.
* Use a dedicated SELECT-only MySQL user for AI access.
* Keep Chroma telemetry disabled (already set in code).
