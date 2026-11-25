# Chilli reference evaluation · 24 November 2026

- Dataset [chilli-anuradhapura-v1](../datasets/chilli-anuradhapura-v1.json) with 20 answerable questions and 12 expected abstentions.
- Corpus `chilli-research-v3` with ten curated passages. Retrieval ran against local PostgreSQL with pgvector using English full text and a ten-dimensional hand-defined topic vocabulary. The optional Gemini selector was disabled. This run used the actual maintained reference text and a synthetic farmer account.
- Reproduction [test commands](../../docs/TESTING.md#chilli-reference-library-and-evaluation).

| Method | Relevant passage in top 5 | Relevant passage ranked first |
| --- | ---: | ---: |
| Keyword | 20/20 | 17/20 |
| Concept vector | 20/20 | 20/20 |
| Combined | 20/20 | 20/20 |

All 20 answerable cases returned the labelled passage, contained the expected fact and resolved to the same citation in the source viewer. All 12 unsupported cases returned **No evidence found**. The dataset includes paraphrases, missing plot context, unsupported treatment or quantity requests, a different crop, ambiguous follow-ups and a private-data request.

The corpus, topic vocabulary and this small evaluation set were built together. The numbers describe this run. Independent agronomic review, an unseen holdout set and live-model scoring remain unmeasured. PDF lifecycle integration tests use synthetic files.
