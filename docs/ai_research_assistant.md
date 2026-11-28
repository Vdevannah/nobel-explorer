# AI Research Assistant — Retrieval (Phase 1), Tools (Phase 2), Agent (Phase 3) and Frontend (Phase 4)

> **Live on Railway** (Phase 5C, commit `c4d18eb`): the backend service runs with `AI_AGENT_ENABLED=true`, behind
> the Phase 5B safeguards.
> Phase 4 (React assistant, tests and real-model browser evaluation) is complete as an MVP; see
> "Known MVP limitations" for accepted issues.

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
| LangChain agent with dynamic tool calling, evidence ids and citation validation | **Implemented (Phase 3)** |
| Real OpenAI model evaluation (gpt-6-luna, 10 questions) | **Done (Phase 3B/3C)** |
| Real-model browser evaluation of prompt v3 (9 questions) | **Done (Phase 4D.2)** |
| Targeted real-model validation of prompt v4 (6 questions) | **Done (Phase 4E.2)**: the no-substitution rule was **not** followed; accepted as a known MVP limitation |
| `POST /ai/chat` endpoint | **Implemented (Phase 3), deployed on Railway (Phase 5C)** — disabled unless `AI_AGENT_ENABLED=true`; rate, concurrency, body-size and spend limits (Phase 5B) |
| "Nobel Intelligence" assistant page (`/assistant`, navbar "Ask AI"): learner-focused answers, collapsible Sources, general-knowledge notes | **Implemented (Phase 4), deployed on Railway (Phase 5C)** |
| Permanent frontend tests (Vitest + React Testing Library) | **Implemented (Phase 4D.1)** |
| Development-only fake agent server (real backend, scripted model) | **Implemented (Phase 4D.1)** |
| Docker / Railway deployment of the AI stack | **Deployed (Phase 5C)** — CPU-only image with the pinned embedding model and packaged index (Phase 5B) |

Phases 1–3 do not change existing routes, frontend, Dockerfiles or database
schema; Phase 3 only registers the new `/ai/chat` router. Phase 4 adds the
`/assistant` page and its navbar link; existing pages are unchanged. LangChain and OpenAI
are imported lazily, so the application runs without AI packages.

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

## Phase 3: research agent (`backend/ai/agent/`) — implemented locally, not deployed

### What it is

A LangChain agent that answers Nobel questions by **choosing and calling** the
four Phase 2 tools, then answering only from the evidence those tools return.
`langchain.agents.create_agent` builds a **LangGraph** state graph (model node,
tool node, middleware nodes) whose state is the message list. The agent is
stateless per request: no conversation memory, no multi-agent orchestration,
no custom graph.

```
backend/ai/agent/
  config.py      AgentConfig from environment (Pydantic only; key held as SecretStr)
  schemas.py     ChatRequest / ChatResponse / Citation / ToolCallSummary / Usage
  prompts.py     system prompt (PROMPT_VERSION)
  evidence.py    request-scoped evidence registry + citation/URL validation
  middleware.py  evidence annotation, call accounting, cooperative deadline
  service.py     build_chat_model, run_agent, error mapping, response assembly
  testing.py     ScriptedChatModel (tool-calling fake) for tests/offline evaluation
backend/routes/ai.py                    POST /ai/chat (LangChain imported lazily)
backend/ai/evaluation/agent_eval_set.json, run_agent_eval.py, grounding.py, reevaluate_saved.py
```

### Request lifecycle

1. `POST /ai/chat {"question": ...}` is validated (Pydantic, length limit). If the
   feature is disabled or `OPENAI_API_KEY` is missing the endpoint returns **503
   without contacting OpenAI**.
2. `run_agent` builds a fresh agent (~1 ms) with the existing tool registry,
   a new evidence registry and three middleware: `AgentRunMiddleware`,
   `ModelCallLimitMiddleware(run_limit=6, exit="end")` and
   `ToolCallLimitMiddleware(run_limit=8, exit="continue")`.
3. The graph loops: the model returns an `AIMessage` with `tool_calls`; the tool
   node runs them (parallel calls allowed); `AgentRunMiddleware` rewrites each
   JSON result with evidence ids (E1, E2, ...) **before** the model reads it.
4. When the model answers without tool calls, `validate_answer` keeps only
   evidence ids issued in this request, replaces others with `[unverified]`,
   removes URLs no tool returned (`[link removed]`) and refuses `related_source`
   URLs as citations.
5. The response carries the answer, `grounding` (`cited`, `partially_cited`,
   `uncited`, `no_evidence`), validated citations with provenance, a tool-call
   summary, evidence limitations, token usage, latency and a request id.
   Raw tool output and internal reasoning are never returned.

### Model configuration

OpenAI deprecated `gpt-4.1-mini` (shutdown 2027-01-14) and lists `gpt-6-luna`
as its replacement; the default is `gpt-6-luna` (`OPENAI_MODEL` is configurable).

```python
# backend/ai/agent/service.py - build_chat_model()
ChatOpenAI(model=config.model, api_key=config.openai_api_key,
           timeout=20, max_retries=1, max_tokens=800,   # sent as max_completion_tokens
           use_responses_api=False,                     # langchain-openai would auto-switch gpt-6* + tools to /v1/responses
           reasoning_effort="none")                     # gpt-6-luna: Chat Completions function calling requires "none"
```

`temperature` is not sent (support is undocumented for gpt-6-luna). A mocked
HTTP transport test pins the exact request: `/v1/chat/completions`,
`reasoning_effort: "none"`, `max_completion_tokens: 800`, four function tools.

### Configuration (environment)

| Variable | Default | Purpose |
|---|---|---|
| `AI_AGENT_ENABLED` | `false` | Feature flag; off unless explicitly enabled |
| `OPENAI_API_KEY` | — | Only in the git-ignored `.env` (mode 600) or the shell; never logged or returned |
| `OPENAI_MODEL` | `gpt-6-luna` | Validated model name |
| `AI_AGENT_REASONING_EFFORT` | `none` | `unset` omits it for non-reasoning models |
| `AI_AGENT_TEMPERATURE` | unset | Sent only if set |
| `AI_AGENT_MAX_QUESTION_CHARS` | 1000 | Input limit |
| `AI_AGENT_MAX_MODEL_CALLS` | 6 | Model-call budget |
| `AI_AGENT_MAX_TOOL_CALLS` | 8 | Tool-call budget (parallel and unknown-tool calls count) |
| `AI_AGENT_MAX_DURATION_SECONDS` | 45 | Request time limit |
| `AI_AGENT_MAX_OUTPUT_TOKENS` | 800 | Per model call |
| `AI_AGENT_PROVIDER_TIMEOUT_SECONDS` / `_MAX_RETRIES` | 20 / 1 | Per provider request |
| `AI_ALLOW_PAID_EVAL` | `0` | Paid evaluation gate (evaluation runner only) |

### Security and cost controls

* Feature flag off by default; 503 without provider contact when disabled or unconfigured.
* Read-only database sessions (Phase 1/2); tools accept only validated arguments; no SQL, shell or browsing tools.
* Budgets: 6 model calls, 8 tool calls, 45 s, 800 output tokens per call; the LangGraph recursion limit (`8 × max_model_calls + 10`) is only a backstop (measured ~6 graph steps per model call).
* Provider errors map to fixed messages via `isinstance` on the SDK classes (langchain-openai re-raises them as subclasses); provider text is never returned because some messages include part of the key.
* Retrieved text is JSON data, never instructions; injected URLs and citation ids are stripped. Prompt injection is mitigated, **not eliminated**.
* Paid evaluation requires `AI_ALLOW_PAID_EVAL=1`, stops on the first provider error and at a shared estimated-cost cap, and refuses to write output containing the API key.
* Each request has its own agent, evidence registry and counters (tested with concurrent requests).
* **Timeout is not cancellation:** `asyncio.wait_for` returns a `timeout` response at the deadline, but synchronous tool work already running in a worker thread finishes in the background, and a cancelled provider request may still be processed (and billed) by the provider.
* Not yet present (required before public exposure): authentication, rate limiting, request-body size limits.

### Real-model evaluation (gpt-6-luna, Chat Completions, reasoning effort "none")

Ten required questions were run with a real model under a hard spend cap:
R01, R04 and R06 in Stage 1, and R02–R10 (including R04 and R06 again with full
execution records) in Phase 3C. The ten-question results combine R01 (Stage 1)
with the nine Phase 3C runs.

**R04 — actual execution (Phase 3C)**

```
HumanMessage  "Who won the 2023 Medicine prize and what did they discover?"
AIMessage     search_laureates(year=2023, category="Physiology or Medicine", limit=10)
ToolMessage   ok  E1 Drew Weissman, E2 Katalin Karikó            (structured_record)
AIMessage     search_nobel_knowledge(query="What did Katalin Karikó and Drew Weissman discover?
              nucleoside base modifications enabling mRNA vaccines against COVID-19", k=3)
ToolMessage   ok  E3 contribution (source_linked, nobelprize.org, similarity 0.84),
                  E4/E5 Simple/Expert explanations (unverified_educational)
AIMessage     final answer (3 model calls, 2 tool calls, 12.0 s, 9,422 input / 5,042 cached / 150 output tokens)
```

> Katalin Karikó and Drew Weissman shared the 2023 Physiology or Medicine prize [E1][E2]. They discovered
> that modifying nucleosides in synthetic mRNA can reduce unwanted immune activation, helping cells
> translate the mRNA into protein and enabling effective mRNA vaccines against COVID-19 [E3].

**Results.** The original automated scores are kept unchanged. The revised
scores re-apply evaluator v2 offline to the saved answers (no model calls).

| | Original automated (v1) | Revised offline (v2) | Manual review |
|---|---|---|---|
| Tool selection | 10/10 | 10/10 | all sensible |
| Tool arguments (where constrained) | 5/5 | 5/5 | all reasonable |
| Citation validity (no invented ids/URLs) | 10/10 | 10/10 | 1 misattribution (R07) |
| "Groundedness" (v1 = keyword presence) | 6/7 | fact presence 5/5; concept coverage replaces R07's keyword | fully grounded 5/8 applicable; partial R02, R07, R10 |
| Task success | 9/10 (R09 false negative) | 10/10 | 10/10 factually correct |

* False premises (R06 Mathematics, R10 relativity) rejected correctly; out-of-scope R09 declined with "no reliable evidence"; R08 asked which Curie.
* R02 and R10 state "not for (general) relativity" from a fact that was in the system prompt (since removed in prompt v3), not from retrieved evidence.
* R07 cites the solar-panel source (E1) for a comparison that came from an unverified educational explanation (E2), and adds "external circuit", which no evidence contains.

**Usage and cost (ten questions).** 21 model calls, 11 tool calls; 56,584 input
tokens (41,359 cached, 73%), 922 output tokens. Estimated cost $0.0024 at
$0.10 / $0.01 / $0.50 per 1M input / cached / output tokens (all twelve paid
executions: $0.0029). Latency mean 3.9 s, median 2.8 s, max 12.0 s; the first
knowledge search in a process loads the embedding model (**cold start 6.0 s**,
warm searches 41–105 ms).

**Prompt versions.** R01 ran with prompt `.1`, R02–R10 with `.2`. Prompt `.3`
(Phase 3D: Einstein-specific fact removed; general guidance to use
`get_laureate_details` for scientific or historical context; corrections must be
evidence-backed) **has not been run against a real model**.

A sanitized per-question summary is in
[`docs/ai_agent_evaluation_summary.md`](ai_agent_evaluation_summary.md). Raw
execution logs stay in the git-ignored `ai_index/`.

### Citation validity versus groundedness

* **Citation validity** (automated, exact): every cited id was issued in this request; no invented URLs.
* **Groundedness** (manual): every claim is supported by the text of the evidence it cites. A valid id can sit next to an unsupported claim.
* `grounding.py` provides deterministic aids — abstention check, concept coverage and a lexical citation-support review that lists numbers and terms absent from the cited evidence — but keyword checks **cannot establish claim-level entailment** (they miss negations and flag paraphrases). Manual evidence review remains required. No paid LLM judge is used.

### Fake-model versus real-model testing

`ScriptedChatModel` implements `bind_tools` and drives the real graph, tools,
database and validation with scripted decisions: it tests orchestration, budgets,
error handling and the evaluator, not model quality. Fake-mode evaluation
(32 cases): every automated metric 32/32 and three deliberately wrong agents
detected. Real-model quality is measured only by the paid runs above.

### Local commands

```bash
# Offline (no paid calls)
set -a; . ./.env.docker; set +a; export DB_HOST=127.0.0.1 DB_PORT=9303 TOKENIZERS_PARALLELISM=false
# Optional: if all-MiniLM-L6-v2 is already in the Hugging Face cache, avoid network update checks
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
.venv-ai/bin/python -m backend.ai.evaluation.run_agent_eval --mode fake --output ai_index/agent_eval_fake.json
.venv-ai/bin/python -m backend.ai.evaluation.reevaluate_saved --stage1 ai_index/agent_eval_openai_stage1.json \
    --stage2 ai_index/agent_eval_openai_stage2_full.json --output ai_index/agent_eval_openai_offline_reeval_v2.json
# Local API (disabled by default -> 503)
.venv-ai/bin/python -m uvicorn backend.main:app --reload
curl -s -X POST localhost:8000/ai/chat -H 'Content-Type: application/json' -d '{"question":"Who won the 2022 Nobel Prize in Chemistry?"}'
# PAID - only with explicit approval; key stays in the git-ignored .env
AI_AGENT_ENABLED=true AI_ALLOW_PAID_EVAL=1 .venv-ai/bin/python -m backend.ai.evaluation.run_agent_eval \
    --mode openai --ids R01 --max-cost-usd 0.05 --output ai_index/<new-file>.json
```

### Remaining work

* Before any public exposure: authentication, rate limiting, request-size limits, spend monitoring.
* Deployment: CPU-only torch image, baked embedding model, warm-up at startup (avoids the 6 s cold start), read-only DB user.
* Invalid-category substitution is accepted as a known MVP limitation (see below); any future remedy would need its own real-model check.
* A larger real-model question set; claim-level grounding review.

## Phase 4: Nobel Intelligence — React assistant (`frontend/`), local only

### Branding and audience

The assistant page is called **Nobel Intelligence** ("Discover the people, ideas and science that changed our
world."). The navbar label stays **Ask AI** and the route stays `/assistant`. The audience is students,
educators and curious learners, so the page hides engineering detail (evidence ids, tool activity) while the
backend keeps every citation, provenance field and tool record unchanged.

### Frontend architecture

`/assistant` is a session-only page: nothing is stored in the browser and each question is answered
independently (no conversation memory, no streaming).

```
AssistantPage            request state: one active request, AbortController, stale-response guard; ?debug flag
├─ header                WelcomeIllustration (golden atom + knowledge network; full size on the welcome
│                        screen, 65% during a conversation; slow CSS animation, off for reduced motion),
│                        "Nobel Intelligence" title (purple), one-line subtitle
├─ SuggestedQuestions    four suggestions, welcome screen only; fill the composer, never send
├─ AssistantExchange ×n  one question and its outcome; all DOM ids prefixed by the exchange id
│  ├─ ResponseStatusNotice   friendly text per status; provider/server diagnostics never shown
│  ├─ AnswerText             escaped React text; evidence ids hidden; **bold** only; [unverified] markers kept
│  ├─ AnswerNotes            general-knowledge note, partial-sourcing note, warnings and plain-language limitations
│  ├─ ResponseActions        copy icon (copies the text as shown, without ids or ** markers)
│  ├─ EvidenceList/Card      collapsed "Sources (n)": provenance label, safe source links, profile links (new tab),
│  │                         and "Supports": the answer statements each source backs; accuracy disclaimer inside
│  └─ ToolActivity           only with /assistant?debug (debugging and evaluation)
└─ AssistantComposer     rounded input, 1,000-character limit, Enter / Shift+Enter, IME-safe, Ask / Cancel / Clear
```

Pure helpers: `utils/assistantText.js` (citation tokens, emphasis, `stripCitations`, `plainAnswerText`,
`claimsByEvidence`), `utils/safeUrl.js` (absolute http(s) only, parsed with `URL`), `utils/assistantEvidence.js`
(citations, grouping, grounding, limitations, knowledge notes, tool activity). API client: `askResearchAssistant()`
in `services/api.js` (one POST, no retries, typed result kinds).

### Rendering rules

* **No HTML or Markdown parser.** Answers are React text nodes. The only formatting is well-formed inline
  `**bold**`: the opening `**` must be followed and the closing `**` preceded by a non-space, non-asterisk
  character, on one line, with no nested `**`. Anything else stays literal. Bullet lines ("- ") display as
  written. Links, images, headings and HTML are never interpreted.
* **Evidence ids are hidden** in the answer text (`stripCitations`). The claim-to-source association is shown
  inside each source card as "Supports" (`claimsByEvidence`: sentences that cite that evidence id; a
  citation-only fragment belongs to the sentence before it). Validation markers `[unverified]` and
  `[link removed]` remain visible.
* **Provenance labels:** "Nobel Explorer database record", "Linked source", "Educational explanation"
  (neutral; the card adds "Nobel Explorer teaching content; no stored external citation"), and "Source not
  specified" for unknown provenance. The educational-provenance notice appears inside Sources, not under the
  answer. Nothing is labelled as verified.
* Only `source_linked` citations with a URL that passes `safeExternalUrl` become external links
  (`target="_blank" rel="noopener noreferrer"`). Related sources are context text, never links.

### Answer notes (under the answer)

| Situation (frontend `knowledgeKind`) | Note |
|---|---|
| No valid citations and not an abstention (`uncited` / `no_evidence`) | ⓘ General scientific knowledge · No retrieved source |
| Cited answer with a substantial paragraph without citations | ⓘ Partly sourced · Some statements use general scientific knowledge |
| Fully cited answer | none (the Sources link is shown) |
| Abstention (for example "the database only covers prizes through 2025") | the existing warnings |
| `partially_cited` (invalid citations removed) | "Some references could not be validated" warning |

Abstentions are recognised with a short pattern check (`looksLikeAbstention`); unusual wording may be
classified as general knowledge. Real problems (failed tool calls, truncated results) are always listed.

### Evidence grouping (Phase 4E.1, presentation only)

The backend issues a new evidence id each time a tool returns a record, so the same record retrieved twice
gets two ids (real example P4-R03: contribution 609 was cited as E4 and E9 from two `get_laureate_details`
calls). The page shows such records as one source card whose "Supports" list merges the statements of
every grouped id. Records are grouped only when **all** of these match: tool, evidence kind, the stable reference
id for that kind (`laureate_id`, `contribution_id`, `connection_id`, `contribution_id`+`level`, statistic
operation+filters+unit, or knowledge `doc_id`+`chunk_id`), provenance, title and every source field.
Anything without a recognised identity stays separate. Backend ids, citations, counts and evaluation results
are unchanged.

### Extended-wait message (bug fixed in Phase 4E.1)

After 8 seconds a pending answer shows "Some questions take longer while the research engine initializes or
retrieves additional information." and announces it once. Phase 4D.2 found that the elapsed counter was reset
in an effect *after* the first render of a new request, so a request following one that took 8 s or more
briefly showed and announced the message (observed on P4-R04). The counter is now reset in the same state
update that starts (and ends, cancels or clears) a request; a regression test fails on the old code.

### Prompt versions

| Version | Change |
|---|---|
| `2026-11-26.3` (Phase 3D) | Removed the Einstein-specific fact; corrections of false premises need evidence. Evaluated on a real model in Phase 4D.2. |
| `2026-11-26.4` (Phase 4E.1) | The ok=false rule now says "fix the arguments once without changing what the user asked about". New rule: "When a question contains an invalid category or a false premise, correct it directly. Do not silently substitute a different category, person, year or question. Offer alternatives only when the user asks for them or they are clearly necessary, and label them as alternatives." Motivated by P4-R05 (a Mathematics question answered with the 1950 Physics laureate). **Real-model result (Phase 4E.2): not followed.** Both invalid-category questions were corrected and then answered with the Physics prize for the same year (V01 Mathematics 1950; V02 Computer Science 2020, one of three laureates). No regressions on the other four questions. |
| `2026-11-27.1` | Educational content is explained directly and cited like other evidence; no verification disclaimers (the interface labels provenance); first STYLE rules (start with the answer). |
| `2026-11-27.2` | **General scientific knowledge fallback.** Retrieved evidence first; cite only results that support a statement. For relevant science questions the evidence does not fully answer, a concise, uncited explanation from well-established knowledge is allowed (mixed answers put it in a final uncited paragraph). Specific Nobel facts (winners, years, motivations, statistics) still come only from tools. Brief abstention for unrelated, current-event or uncertain questions. |
| `2026-11-27.3` (current) | No retrieval commentary ("The search returned…", database coverage) in ordinary explanations; limitations only when genuinely necessary; short paragraphs and "- " bullets; Unicode formulas (E = mc²) instead of LaTeX; applies to every scientific topic. |

Prompts `2026-11-27.1`–`.3` were checked with deterministic tests and the scripted evaluation only; they have
**not** been evaluated with a real model.

### Evaluator versions

| Version | Change |
|---|---|
| v2 (Phase 3D) | Fixed abstention phrase list, concept coverage, lexical citation-support review. |
| v3 (Phase 4E.1) | `abstention_check` matches patterns rather than a fixed list, distinguishes `insufficient_evidence` from `coverage` (missing records / data coverage), handles typographic apostrophes, and checks every clause (text after `;`, "but" or "however" counts), so a claim cannot hide behind an abstention phrase. Bare refusals and factual negations ("There is no Nobel Prize in Mathematics") are not abstentions. |

Offline re-evaluation of the saved Phase 4D.2 answers (no model calls; answers unchanged):

| Measure | Original (v2) | Revised (v3) |
|---|---|---|
| Expected abstentions recognised (P4-R06 out of scope, P4-R07 missing 2026 records) | 0/2 | 2/2 (kinds correct) |
| False abstentions on the seven answer questions | 0/6 recorded (P4-R03 had no v2 check) | 0/7 |

Re-evaluating the Phase 3 saved answers with v3 changes no metric (only the new `kind` field is added).
Naming correction (Phase 4E.2): `reevaluate_saved.py` wrote its revised block as `revised_v2` even when
`EVALUATOR_VERSION` was 3. The key is now `revised_v{EVALUATOR_VERSION}`; scoring is unchanged. The
4E.1 artifact `agent_eval_openai_offline_reeval_v3.json` is kept as written; the correctly named copy is
`agent_eval_openai_offline_reeval_v3_corrected.json` (identical values).

Known evaluator v3 limits found in Phase 4E.2 (not changed): it rejects the valid abstention "its search
results were weak matches and don't describe the process" (V06) as a claim, and the lexical support review
misses spelled-out numbers ("three laureates", V02).
These differences reflect the evaluator, not better model answers. Artifacts:
`ai_index/agent_eval_openai_phase4d2_offline_reeval_v3.json`, `ai_index/agent_eval_openai_offline_reeval_v3.json`
(originals unchanged).

### Development-only fake agent server

`python -m backend.ai.evaluation.fake_agent_server` runs the real application and `/ai/chat` with the real
agent, tools, read-only MySQL, ChromaDB and validation, replacing only the model's decisions with the Phase 3
scripted plans. It binds to loopback only, removes `OPENAI_API_KEY` from its process, refuses to build a real
client, and answers unsupported questions with 503. It is never imported by `backend.main`.

### Local frontend commands

```bash
cd frontend
npm test              # Vitest + React Testing Library, single run
npm run build
VITE_API_BASE_URL=http://127.0.0.1:8000 npx vite --host 127.0.0.1
```

### Known MVP limitations (accepted at the end of Phase 4)

* **Invalid-category substitution.** Asked about a category that does not exist (Mathematics 1950,
  Computer Science 2020), `gpt-6-luna` correctly says there is no such Nobel Prize but then volunteers the
  Physics prize for the same year without labelling it as an alternative (P4-R05, V01, V02). The extra
  sentence is factually correct and validly cited, but it answers a question that was not asked, and in V02
  it named only one of three laureates (the truncation is shown as a limitation). Prompt v4's explicit rule
  did not change this. No guardrail was added; the behaviour is documented rather than fixed.
* **Evaluator v3 limits.** One valid abstention (V06) is scored invalid, and the lexical support review
  misses spelled-out numbers. Claim-level grounding remains a manual judgement.
* **General scientific knowledge.** Since prompt `2026-11-27.2` the model may answer relevant science
  questions from pretrained knowledge when retrieval does not cover them. Such statements are uncited and
  marked by a note, but they are not checked against Nobel Explorer data and may contain errors. Real-model
  behaviour of prompts `2026-11-27.1`–`.3` has not been evaluated.
* **Note classification is heuristic.** The general-knowledge and partial-sourcing notes are derived in the
  browser from citations and a short abstention pattern check.
* **Scope.** Local only (no authentication, rate limiting, spend monitoring or deployment); session-only
  history; only `**bold**` is rendered; duplicate evidence ids are grouped in the UI, not in the backend;
  the first knowledge search after a server start takes about 5 s.

## Tests

Distinct tests (each counted once even when run in two environments):

| Suite | Distinct tests | Result |
|---|---|---|
| Frontend unit and component tests (`frontend/src/**/*.test.*`, Vitest + RTL, jsdom) | 299 | 299 passed |
| AI unit tests (`backend/ai/tests`, SQLite fixtures, fake embedder and fake chat model) | 488 | 488 passed (`.venv-ai` and inside the Linux image) |
| Integration: real all-MiniLM-L6-v2 + live read-only MySQL (opt-in) | 18 | 18 passed |
| Paid real-LLM test (opt-in, needs approval) | 1 | not run |
| Existing backend/ETL regression suite (isolated `nobel_explorer_ai_test`) | 297 | 297 passed in `.venv` and `.venv-ai` |

The base `.venv` (no AI packages) runs 186 of the AI unit tests and skips the
rest cleanly, proving the application works without AI dependencies. Total distinct
permanent tests: 299 frontend + 488 AI unit + 18 integration + 297 backend/ETL = 1,102
(paid test excluded). Counts as of Phase 5B (44 new guard and index-consistency tests).

Evaluations: Phase 2 tool evaluation 30/30; agent fake-model evaluation 32 cases,
every automated metric 32/32, 3/3 negative controls detected (deterministic,
not LLM accuracy); real-model results in the Phase 3 section and in
`docs/ai_agent_evaluation_summary.md` (Phase 4D.2).

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
* Phase 3 agent:
  * Real-model evidence covers only ten questions (one run each); it does not establish general accuracy,
    and prompt v3 has not been run on a real model.
  * Claim-level grounding is assessed manually; the deterministic checks are review aids only.
  * Citations can be valid yet misattributed (R07), and models may add facts from general knowledge.
  * Prompt injection is mitigated, not eliminated.
  * A timeout does not cancel synchronous tool work already running in a thread, and a cancelled
    provider request may still be processed and billed.
  * Evidence ids follow tool completion order for parallel calls.
  * The first knowledge search in a process pays a ~6 s embedding-model cold start (production
    loads the model at startup when the assistant is enabled).
  * The endpoint has no authentication. Phase 5B added rate, daily, concurrency, spending and
    body-size limits; their counters are in memory and reset on restart.
* Phase 4 frontend and evaluation:
  * Not deployed yet (Phase 5B prepared the image and safeguards). Rate-limit rejections show
    the page's generic "currently unavailable" notice.
  * The conversation is lost when the page is left or reloaded (by design: no persistent history).
  * Only `**bold**` is rendered; other Markdown a model may produce appears literally.
  * Evidence grouping is presentation only; the backend still issues duplicate ids for repeated records.
  * Real-model browser evidence covers nine questions on prompt v3 and six on prompt v4 (one run each);
    prompt v4's no-substitution rule was not followed for invalid categories. Grounding labels describe citations, not factual correctness.
  * ChromaDB appends a row to its internal `acquire_write` lock table whenever a client opens the index;
    indexed documents and embeddings do not change.
  * jsdom cannot evaluate the CSS cascade for `[hidden]`; real rendering is checked in Chrome.
* Each tool call opens a short-lived read-only engine (NullPool); fine for an
  assistant, not tuned for high request rates.
* The local Homebrew MySQL on port 3306 rejects the `.env` credentials
  (error 1045); development used the compose database on port 9303.

## Phase 5B: production preparation for Railway (not yet deployed)

Nobel Intelligence runs inside the existing **backend** service; no new Railway
service, volume or database is needed. The assistant stays off until
`AI_AGENT_ENABLED=true` is set, and while it is off the embedding model is never loaded.

### Production image (`backend/Dockerfile`)

* `python:3.12-slim`, CPU-only PyTorch `2.15.0+cpu` from the PyTorch CPU index, then
  `requirements-ai.txt` unchanged (the macOS pins resolve on Linux; `pip check` is clean).
* The pinned model `sentence-transformers/all-MiniLM-L6-v2@1110a243…` is downloaded at
  build time (safetensors weights only) into `/opt/huggingface`.
* The packaged index `deploy/ai-index/chroma` (1,064 chunks) is copied in.
* Runtime is offline: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, Chroma telemetry off.
* Runs as an unprivileged user (uid 10001), single uvicorn worker on port 8000 (unchanged).
* When the assistant is enabled, a background thread loads the model and opens the index
  at startup (`AI_WARMUP`, default true); `/health` is served immediately.

Measured locally with Docker Desktop, `linux/amd64` emulated on an Apple M1 Pro.
Memory figures are representative; timings are pessimistic compared with native amd64.

| Measurement | Current image | New image |
|---|---|---|
| Image size, compressed / unpacked | 68 MB / 205 MB | 651 MB / 2.1 GB |
| Cold build (no cache) | — | 141 s |
| Ready (`/health` 200), AI disabled | 1.3 s | 1.7 s |
| Ready, AI enabled (warm-up continues in background) | — | 2.6–3.8 s |
| Model and index load | — | 7.2–9.9 s |
| Idle memory, AI disabled | 69 MiB | 77 MiB |
| Idle memory, AI enabled, model loaded | — | 512–530 MiB |
| Memory after concurrent AI requests | — | 600 MiB |
| Peak RSS of a retrieval process | — | 674 MiB |
| Knowledge search latency, first / warm | — | 198 ms / 19 ms |

The unpacked size is mostly site-packages (1.9 GB: PyTorch, transformers, ChromaDB and
onnxruntime); the model is 88 MB and the index 9.7 MB.

### Packaged index (`deploy/ai-index/`)

* `chroma/` is a byte-identical copy of the local index; `SHA256SUMS` lists its files and
  `index_manifest.json` is the build manifest without local paths.
* It was checked before committing: 1,064 embeddings, no e-mail addresses, keys,
  credentials or local paths. The only URLs are public sources (nobelprize.org, NASA,
  NIST, energy.gov, royalsociety.org).
* Opening the index makes Chroma append to its internal `acquire_write` table, so
  `chroma.sqlite3` changes inside a running container; embeddings and HNSW files do not.
  The container filesystem is discarded on redeploy.
* The index refers to records by internal database ids. Check that a database matches it
  (read-only) with:

  ```bash
  python -m backend.ai.check_index_consistency --index-dir deploy/ai-index/chroma
  ```

  The check rebuilds the chunk list from the database inside `SET SESSION TRANSACTION READ
  ONLY` sessions, compares chunk ids and content hashes, and opens a temporary copy of the
  index. It prints ids and counts only. Exit codes: 0 consistent, 1 different (rebuild
  the index from that database), 2 could not run. The local database is consistent
  (1,064 of 1,064 chunks).

### Safeguards (`backend/ai/guard.py`)

Checked after validation and the enabled check, before any model call. Only admitted
requests are counted.

| Variable | Default | Effect |
|---|---|---|
| `AI_RATE_PER_IP_PER_MINUTE` | 5 | sliding 60 s window per client; 429 `ip_minute_limit` |
| `AI_RATE_PER_IP_PER_DAY` | 50 | per client per UTC day; 429 `ip_daily_limit` |
| `AI_GLOBAL_DAILY_LIMIT` | 100 | all clients per UTC day; 429 `global_daily_limit` |
| `AI_MAX_CONCURRENT_REQUESTS` | 2 | requests in flight; 429 `busy` immediately, no queue |
| `AI_DAILY_SPEND_LIMIT_USD` | 0.05 | spending guard; 503 `spend_limit` |
| `AI_MONTHLY_SPEND_LIMIT_USD` | 0.90 | spending guard; 503 `spend_limit` |
| `AI_MAX_BODY_BYTES` | 16384 | request body for `/ai/*`; 413 (Content-Length and streamed bodies) |
| `AI_CLIENT_IP_HEADER` | empty | header that holds the client address; `x-real-ip` on Railway |

* **Client address.** Forwarded headers are ignored unless `AI_CLIENT_IP_HEADER` is set.
  Railway's edge overwrites `X-Real-IP` on public requests. A missing or invalid header
  falls back to the TCP peer, which fails safe: all clients then share one bucket.
  `X-Forwarded-For` is never used. Requests over Railway private networking bypass the
  edge, so the backend must not be called from other private services.
* **Spending guard.** Each request reserves its worst case before it runs: 6 model calls ×
  (20,000 input + 800 output tokens) at $0.10 / $0.50 per 1M tokens, which is $0.0144.
  When the request ends, the reservation is replaced by a conservative cost:
  * the reported usage, with cached input at $0.01 per 1M tokens;
  * $0.0024 for each successful call without reported usage;
  * $0.0024 more for a timeout, or for an error the provider may still bill.

  Errors rejected before billing cost nothing: authentication, connection, rate limit,
  bad request, model not found. A crashed or hung request keeps its full reservation.
  A request is admitted only if spent + reserved + its own reservation stays within both
  caps. Two concurrent reservations fit in the daily cap. Thirty days at the daily cap
  would exceed $1, so the $0.90 monthly cap is what keeps spending under the budget.
* **Concurrency and timeouts.** A slot is released only in `finally`, after the agent task
  finished or was cancelled. The route wraps the agent in an outer limit of
  `AI_AGENT_MAX_DURATION_SECONDS` + 15 s, so a hung request always frees its slot. A
  client that disconnects keeps its slot until the server finishes, so it cannot retry
  into a second one (tested with a real uvicorn server).
* **Counters reset on restart.** All counters live in process memory. A restart or redeploy
  clears the rate limits, daily counts and spending totals; each replica would keep its
  own. Run a single replica with a single worker. The OpenAI project budget ($1 per
  month, with usage alerts) is the backstop that survives restarts.
* Rejections return a `ChatResponse` body (status `unavailable`, `error.type` as above,
  `Retry-After` header), so the existing page renders them without UI changes. The page
  shows its generic "currently unavailable" notice, not the specific reason.
* An invalid limit variable makes `/ai/chat` return 503; the rest of the API is unaffected.

### Railway variables (backend service)

| Variable | Value |
|---|---|
| `OPENAI_API_KEY` | key of the existing dedicated OpenAI project; sealed; backend only, never `VITE_*` |
| `AI_AGENT_ENABLED` | `false` for the first deploy; `true` to switch on; `false` is the kill switch |
| `OPENAI_MODEL` | `gpt-6-luna` (default) |
| `AI_CLIENT_IP_HEADER` | `x-real-ip` |
| Limits | defaults above; override only if needed |
| Existing `DB_*`, `FRONTEND_ORIGINS` | unchanged |

The image already sets `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`, `AI_CHROMA_DIR`,
`AI_EMBEDDING_MODEL` and `AI_EMBEDDING_REVISION`. Keep replicas at 1.

### Validation (Phase 5B, no paid calls)

* All test suites pass; see [Tests](#tests).
* Inside the Linux image, all 488 AI unit tests pass and the scripted agent evaluation
  scores 32/32 on every metric (no OpenAI key in the container).
* All 28 existing GET responses and the quiz POST are byte-identical between the current
  and the new image (AI disabled, same database). `/ai/chat` returns 503 while disabled.
* End-to-end in the production container (AI enabled, placeholder key, provider address
  pointed at a local socket that never answers):
  * a 6th request from one address gets 429; a spoofed `X-Forwarded-For` does not reset it;
  * a 3rd concurrent request gets 429 `busy` in 15 ms;
  * abandoned requests keep their slots;
  * the global limit applies;
  * a 20 KB body gets 413;
  * `/health` and `/laureates` stay responsive.

### Remaining deployment steps

1. Commit and push the branch (`deploy/ai-index/` included).
2. Merge into `main`: Railway deploys `main` to production. Deploy with
   `AI_AGENT_ENABLED=false` and `AI_CLIENT_IP_HEADER=x-real-ip`.
3. Check the existing pages. In the backend service shell, run the consistency check
   against the production database; it must print CONSISTENT.
4. Set the OpenAI key, set `AI_AGENT_ENABLED=true`, and ask one or two questions.
5. Rollback: `AI_AGENT_ENABLED=false` switches the assistant off; Railway *Redeploy* of
   the previous deployment restores the old image.
