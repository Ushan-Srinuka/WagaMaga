# Knowledge sources and AI evaluation

Status: curation and evaluation plan. No source has been approved, no labelled dataset exists and no quality target has been measured.

## Initial knowledge scope

English evidence applicable to chilli cultivation in the validated target area. A directory listing or government publisher does not by itself establish reuse rights, freshness or relevance. Sinhala/Tamil sources may be inventoried but do not establish supported multilingual retrieval.

## Source inventory

For each candidate, record stable source ID, publisher, title, original URL/file, language, crop/area applicability, publication date (or explicitly unknown), validity period, access date, rights/permission note, reviewer, review date and inclusion status. Retain rejection reasons and extraction limitations.

Only eligible, reviewed versions enter farmer retrieval. File checks, parsing or indexing success alone does not publish a source. Preserve immutable version/checksum, passage ID, exact text, page/section locator, embedding model and index version. Withdrawn versions are excluded from new retrieval and block dependent new execution; authorized historical citations remain labelled and resolvable under the retention policy.

## Dataset design

Use at least 10 evidence-mapped V0 questions and at least 30 labelled V1 questions. Cover exact crop terms, paraphrases, insufficient farm context, missing/outdated/conflicting evidence, inapplicable area/crop and malicious instructions in sources.

Each case should include case ID, question, authorized synthetic context, corpus version, answerable flag, relevant passage IDs, expected limitations/abstention, prohibited claims and human reviewer notes. Multiple relevant passages may be needed; do not evaluate only one convenient source when the question needs several.

## Retrieval experiments

Compare full text only, vector only and hybrid on the same corpus/questions. Use the architecture's initial reciprocal-rank fusion and candidate sizes as tuning starting points, not validated optimums. Record query/configuration, ranks, eligible passages, latency and versions.

For an answerable question, Recall@5 is the fraction of its labelled relevant passages present in the first five eligible results. Report the aggregate method and per-case results. V1 target is >= 0.80; unanswerable questions are assessed for abstention rather than included as recall successes. Check source applicability independently of rank.

## Answer review

Verify that every citation resolves to a permitted passage. Have a human assess support for each material agricultural claim and applicability to the supplied context. Record supported/unsupported/uncertain outcomes, reviewer identity and reasons. V1 target is >= 90% supported material claims, with the denominator stated. Any unsupported actionable treatment recommendation fails release, regardless of the average score.

An LLM judge may assist triage, but cannot replace the required human review. Schema/citation validity does not prove agricultural correctness. Do not fabricate expert review or validated thresholds for demonstration data.

## Runs and reports

Keep datasets in `evaluation/datasets/` and reports in `evaluation/reports/` when created. Record date, commit, corpus/document versions, embedding/index version, model/provider, prompt version, retrieval settings, timeouts, usage/cost, metrics, human findings and unresolved failures.

Use deterministic provider responses for ordinary integration tests. Run live-model evaluation separately with suitable credentials and an agreed usage budget. A fake embedding/model run verifies plumbing and must not be reported as measured retrieval/answer quality.

Before changing a model, chunking, prompt, fusion setting or evidence corpus, rerun the relevant fixed evaluation and compare with the previous baseline. Keep the prior report; do not overwrite historical evidence.
