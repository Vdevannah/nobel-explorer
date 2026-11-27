# Nobel Explorer AI Agent — Real-Model Evaluation Summary

Sanitized summary of the ten required questions run against a real model. Raw execution logs are kept
locally (git-ignored) and are not published. No credentials or request identifiers are included.

* Model: `gpt-6-luna` via Chat Completions, `reasoning_effort="none"`, LangChain `create_agent` with the four Phase 2 tools.
* Runs: R01 from Stage 1 (prompt `2026-11-26.1`); R02–R10 from Phase 3C (prompt `2026-11-26.2`). One run per question.
* Prompt `2026-11-26.3` (Phase 3D) was evaluated with a real model in Phase 4D.2 (section below). Prompt `2026-11-26.4` (Phase 4E.1) was evaluated on six targeted questions in Phase 4E.2.
* Ten questions demonstrate the integration; they do not establish general accuracy.

## Results

| Measure | Original automated (v1) | Revised offline (v2, same saved answers) | Manual review |
|---|---|---|---|
| Tool selection | 10/10 | 10/10 | all sensible |
| Tool arguments (constrained cases) | 5/5 | 5/5 | all reasonable |
| Citation validity | 10/10 | 10/10 | 1 misattributed citation (R07) |
| Grounding | 6/7 (v1 keyword check) | keyword fact presence 5/5; grounding not automated | 5/8 fully grounded; R02, R07, R10 partial |
| Task success | 9/10 | 10/10 | 10/10 factually correct |

*Citation validity* means every cited evidence id was really returned in that request. *Groundedness* means
each claim is supported by the cited evidence text; it was judged manually, because keyword checks cannot
establish entailment.

Totals: 21 model calls, 11 tool calls, 56,584 input tokens (41,359 cached), 922 output tokens,
estimated cost $0.0024 (all twelve paid executions including Stage 1 repeats: $0.0029). Latency mean 3.9 s,
median 2.8 s, max 12.0 s (includes a one-time 6.0 s embedding-model load; warm knowledge searches take 41–105 ms).

## Per question

### R01 — Who won the 2022 Nobel Prize in Chemistry?

* Category: exact_structured. Tools: `search_laureates(year=2022, category="Chemistry")`.
* 2 model calls, 1 tool calls; 4.4 s; 5,198 input (2,097 cached) / 80 output tokens; $0.000371.
* Automated v1: tools pass, citations pass, task pass. Revised v2: task pass.
* Manual: correct; grounding: grounded.

> The 2022 Nobel Prize in Chemistry was shared by Carolyn R. Bertozzi, K. Barry Sharpless, and Morten Meldal, for the development of click chemistry and bioorthogonal chemistry. [E1][E2][E3]

### R02 — What did Albert Einstein win the Nobel Prize for?

* Category: laureate_details. Tools: `search_laureates(name="Albert Einstein", limit=10)`.
* 2 model calls, 1 tool calls; 2.4 s; 4,774 input (4,278 cached) / 65 output tokens; $0.000125.
* Automated v1: tools pass, citations pass, task pass. Revised v2: task pass.
* Manual: correct; grounding: partially grounded; prompt-supported: not for relativity; citation: E1 supports the motivation, not the negation.

> Albert Einstein received the 1921 Nobel Prize in Physics for his services to theoretical physics, especially his discovery of the law of the photoelectric effect—not for relativity. [E1]

### R03 — Explain click chemistry in simple terms.

* Category: semantic. Tools: `search_nobel_knowledge(query="Explain click chemistry in simple terms.", level="Simple", k=5, dedupe_by_document=true)`.
* 2 model calls, 1 tool calls; 3.3 s; 5,963 input (4,275 cached) / 94 output tokens; $0.000259.
* Automated v1: tools pass, citations pass, task pass. Revised v2: task pass.
* Manual: correct; grounding: grounded.

> In Nobel Explorer’s simple explanation, click chemistry is like connecting LEGO pieces: chemists choose molecular building blocks that join together quickly and reliably. Scientists can use these reactions to attach chemical tags to molecules and study what they do in living systems.[E1]

### R04 — Who won the 2023 Medicine prize and what did they discover?

* Category: multi_step. Tools: `search_laureates(year=2023, category="Physiology or Medicine", limit=10)`; `search_nobel_knowledge(query="What did Katalin Karikó and Drew Weissman discover? nucleoside base modifications enabling mRNA vaccines against COVID-19", k=3)`.
* 3 model calls, 2 tool calls; 12.0 s; 9,422 input (5,042 cached) / 150 output tokens; $0.000563.
* Automated v1: tools pass, citations pass, task pass. Revised v2: task pass.
* Manual: correct; grounding: grounded.

> Katalin Karikó and Drew Weissman shared the 2023 Physiology or Medicine prize [E1][E2]. They discovered that modifying nucleosides in synthetic mRNA can reduce unwanted immune activation, helping cells translate the mRNA into protein and enabling effective mRNA vaccines against COVID-19 [E3].

### R05 — Which three birth countries have produced the most Nobel laureates in our database?

* Category: statistics. Tools: `get_nobel_statistics(operation="top_birth_countries", limit=3)`.
* 2 model calls, 1 tool calls; 2.9 s; 4,560 input (4,283 cached) / 65 output tokens; $0.000103.
* Automated v1: tools pass, citations pass, task pass. Revised v2: task pass.
* Manual: correct; grounding: grounded.

> The top three birth countries are the USA, with 296 distinct person laureates; the United Kingdom, with 94; and Germany, with 80. [E1]

### R06 — Who won the Nobel Prize in Mathematics in 1950?

* Category: false_premise. Tools: `search_laureates(year=1950, category="Mathematics", limit=10)` → validation_error.
* 2 model calls, 1 tool calls; 2.8 s; 4,418 input (4,280 cached) / 73 output tokens; $0.000093.
* Automated v1: tools pass, citations pass, task pass. Revised v2: task pass.
* Manual: correct; grounding: not applicable (tool rejected the false premise; no citable evidence); prompt-supported: list of six categories (also in the tool's validation message).

> There is no Nobel Prize in Mathematics, so no one won it in 1950. The Nobel Prize categories are Chemistry, Economic Sciences, Literature, Peace, Physics, and Physiology or Medicine.

### R07 — Explain how solar cells convert sunlight into electricity.

* Category: semantic. Tools: `search_nobel_knowledge(query="Explain how solar cells convert sunlight into electricity", level=null, k=5, dedupe_by_document=true)`.
* 2 model calls, 1 tool calls; 3.7 s; 6,194 input (4,277 cached) / 134 output tokens; $0.000301.
* Automated v1: tools pass, citations pass, task pass. Revised v2: task pass.
* Manual: correct; grounding: partially grounded; citation: misattributed: the metal comparison is in E2 (unverified educational) but cited to E1 (source_linked).

> Solar cells use semiconductor materials to turn light into electrical current. Photons absorbed by the semiconductor generate mobile charge carriers—electrons and “holes.” The cell’s structure separates and collects these charges, making them flow through an external circuit as electric current. [E1]
> >
> > This is related to light-to-electricity physics, but it is not simply the same as light knocking electrons out of a metal in the photoelectric effect. [E1]

### R08 — Tell me about Curie.

* Category: clarification. Tools: `search_laureates(name="Curie", limit=20)`.
* 2 model calls, 1 tool calls; 2.6 s; 5,298 input (4,274 cached) / 135 output tokens; $0.000213.
* Automated v1: tools pass, citations pass, task pass. Revised v2: task pass.
* Manual: correct; grounding: grounded.

> “Curie” could refer to three Nobel laureates:
> >
> > - Marie Curie: shared the 1903 Physics Prize for research on radiation and received the 1911 Chemistry Prize for her work on radium and polonium. [E2]
> - Pierre Curie: shared the 1903 Physics Prize for research on radiation. [E3]
> - Irène Joliot-Curie: shared the 1935 Chemistry Prize for synthesizing new radioactive elements. [E1]
> >
> > Which one would you like to hear more about?

### R09 — Explain sourdough fermentation.

* Category: out_of_scope. Tools: `search_nobel_knowledge(query="Explain sourdough fermentation", k=5, dedupe_by_document=true)`.
* 2 model calls, 1 tool calls; 2.6 s; 5,981 input (4,274 cached) / 60 output tokens; $0.000243.
* Automated v1: tools pass, citations pass, task fail. Revised v2: task pass.
* Manual: correct (abstention); grounding: not applicable (declined).

> Nobel Explorer has no reliable evidence about sourdough fermentation; its search returned only weakly related material.

### R10 — Did Einstein win the Nobel Prize for general relativity?

* Category: false_premise. Tools: `search_laureates(name="Einstein", limit=10)`.
* 2 model calls, 1 tool calls; 2.2 s; 4,776 input (4,279 cached) / 66 output tokens; $0.000125.
* Automated v1: tools pass, citations pass, task pass. Revised v2: task pass.
* Manual: correct; grounding: partially grounded; prompt-supported: not for general relativity; citation: E1 supports the motivation, not the negation.

> No. Einstein received the 1921 Nobel Prize in Physics for his services to theoretical physics, especially his discovery of the law of the photoelectric effect—not for general relativity [E1].

## Known evaluation limitations

* One run per question; model output is not deterministic.
* R09's original v1 failure was a phrase-list false negative; v2 accepts a valid abstention only if no further claims follow.
* R07's original v1 failure required the word "photovoltaic"; v2 checks concept coverage instead.
* R02 and R10 relied on a system-prompt fact for "not for relativity"; prompt v3 removes that fact (not yet re-run).

## Phase 4D.2: real-model browser evaluation of prompt `2026-11-26.3`

Nine questions, each asked once through the React page against the local FastAPI backend
(`gpt-6-luna`, Chat Completions, reasoning effort "none"). Sanitized results:
`docs/teaching/phase4_real_model_screenshots/` (Stage 1, Stage 2 and `phase4d2_consolidated.json`).

| Measure | Result |
|---|---|
| HTTP / status | 9/9 HTTP 200, `completed`; no provider errors or retries |
| Factually correct (manual) | 9/9 |
| Task success (manual) | 9/9 (P4-R05 with a caveat: unrequested 1950 Physics substitution) |
| Citation validity (automated) | 9/9: no fabricated ids or URLs |
| Citation misattribution (manual) | 0/9 |
| Claim support (manual) | fully supported 5 (P4-R01, R02, R03, R04, R09); partially 1 (P4-R08, minor glosses); not applicable 3 (P4-R05 invalid category, R06 abstention, R07 missing 2026 records) |
| Grounding values | cited 7, uncited 1, no_evidence 1 |
| Calls and tokens | 20 model calls, 12 tool calls; 57,574 input (42,776 cached) and 831 output tokens |
| Estimated cost | $0.00232306 for all nine |
| User-perceived latency | mean 3.9 s, median 2.5 s, max 8.5 s (first knowledge search loads the embedding model: 5.5 s) |

Compared with Phase 3 (prompt .2): the solar-cell answer no longer misattributes the photoelectric
comparison, and the Einstein correction is now supported by retrieved evidence (E2: "not general
relativity") rather than a prompt fact. Sourdough abstention is unchanged. The Mathematics question changed
from a rejected tool call plus a category list to an unrequested Physics answer, which prompt v4 addresses.

Abstention check, same saved answers: evaluator v2 recognised 0/2 expected abstentions (P4-R06, P4-R07) because
of their wording; evaluator v3 recognises 2/2 with no false abstentions on the other seven answers. This is an
evaluator change, not a change in the answers.

## Phase 4E.2: targeted real-model validation of prompt `2026-11-26.4`

Six questions, each asked once through the React page (`gpt-6-luna`). Sanitized results:
`docs/teaching/phase4e2_real_model_screenshots/phase4e2_results.json`.

| ID | Question | Result (manual) | Same question under prompt v3 |
|---|---|---|---|
| V01 | Mathematics 1950 | Correct but **substituted** the 1950 Physics laureate (unlabelled). Rule not followed. | P4-R05: identical behaviour |
| V02 | Computer Science 2020 (new) | Correct but **substituted** the 2020 Physics prize, naming one of three laureates (`limit: 1`). Rule not followed; no unrelated award introduced. | — |
| V03 | Einstein / relativity | False premise corrected; fully supported by E1 (motivation) and E2 ("not general relativity"). | P4-R09: equivalent (no Markdown this time) |
| V04 | 2026 Chemistry | Appropriate coverage abstention; no fabricated laureate. | P4-R07: equivalent |
| V05 | 2022 Chemistry | Correct, fully supported. | P4-R01: identical |
| V06 | Sourdough | Appropriate abstention. | P4-R06: equivalent |

All 6 HTTP 200 / `completed`; citation validity 6/6; misattribution 0/6; no fabricated laureates.
13 model calls, 7 tool calls, 35,888 input (27,443 cached) and 454 output tokens; estimated $0.00134593.
User-perceived latency mean 4.0 s, median 2.6 s, max 9.6 s (V03 included the 5.3 s embedding-model load).

Conclusion: the prompt-only rule did not change invalid-category behaviour for this model; the other four
answers did not regress. Evaluator v3 disagreed with manual review on V06 (false negative abstention); the
lexical support review missed V02's spelled-out "three laureates", which comes from tool metadata rather than
the cited record. Six questions do not establish general accuracy.

## Status at the end of Phase 4

Invalid-category substitution (P4-R05, V01, V02) is accepted as a known MVP limitation and documented; no
guardrail or further prompt change was made. Across Phase 4, 15 real-model browser questions were run once
each (9 on prompt v3, 6 on prompt v4) for an estimated $0.00366899 in total.
