# Knowledge sources and AI evaluation

Signed-in farmers can open **Chilli questions** for answers from published Sri Lankan chilli studies and the Department of Agriculture. The [candidate inventory](KNOWLEDGE_SOURCE_INVENTORY.md) and [10 draft V0 questions](../evaluation/datasets/chilli-anuradhapura-v0-draft.md) support the separate farm guidance workflow.

## Published chilli research

The `chilli-research-v3` reference set contains ten versioned English passages. Study summaries cite the authors, publisher, DOI, journal and PDF page, and CC BY 4.0 license. Practical answers summarize general guidance in English and link to the relevant section of the public Sinhala crop page. Choose **Show supporting passage** on an answer to see the English paraphrase.

| Question | Reviewed source location |
| --- | --- |
| What should I check when choosing a chilli nursery site? | [Department of Agriculture](https://doa.gov.lk/field-crops-chilli-si/), nursery preparation, first bullet. |
| What affects how often field chilli needs irrigation? | [Department of Agriculture](https://doa.gov.lk/field-crops-chilli-si/), irrigation. |
| When does soil testing help with chilli fertilizer decisions? | [Department of Agriculture](https://doa.gov.lk/field-crops-chilli-si/), fertilizer application, note 1. |
| Where was the dry zone chilli field study conducted? | [Darshana et al.](https://doi.org/10.4038/ta.v173i1.128), methods, journal page 32, PDF page 3. |
| What did the dry zone chilli field study measure? | [Darshana et al.](https://doi.org/10.4038/ta.v173i1.128), abstract, journal page 30, PDF page 1. |
| How was chilli grown in the Rajarata study? | [Devasinghe and Wickramasinghe](https://doi.org/10.4038/sljae.v7i1.156), abstract, journal page 21, PDF page 1. |
| Did the Rajarata chilli study find a clear yield difference? | [Devasinghe and Wickramasinghe](https://doi.org/10.4038/sljae.v7i1.156), abstract, journal page 21, PDF page 1. |
| What soil characteristics suit field chilli? | [Department of Agriculture](https://doa.gov.lk/field-crops-chilli-si/), soil. |
| What does the chilli guide say about field drainage before transplanting? | [Department of Agriculture](https://doa.gov.lk/field-crops-chilli-si/), field preparation and planting. |
| What growing-media measurements did the Rajarata polytunnel study take? | [Devasinghe and Wickramasinghe](https://reference-global.com/article/10.4038/sljae.v7i1.156?tab=abstract), abstract, journal page 21, PDF page 1. |

Exact questions and maintained aliases are resolved locally. For other wording, PostgreSQL full-text ranking combines with pgvector cosine similarity over a small hand-curated concept vocabulary. The fallback requires one unambiguous eligible concept and abstains on out-of-scope requests. Farm-specific requests for fertilizer quantities, irrigation dates or treatment choices require separate evidence. If Gemini is configured, the optional study selector receives only the canonical study question and maintained study summaries. The server verifies the exact selection and falls back to the local result. Department of Agriculture summaries are served locally.

The study summaries were checked against the cited PDF pages. The three practical summaries were checked against the linked sections of the public Sinhala crop page. The ten-case guidance workflow checks site-specific applicability independently.

## Portfolio demo

1. In local development, sign in with a synthetic farmer account and open **Chilli questions → Try the local demo**. Ask about the nursery tray label or the irrigation and fertilizer logs. The app returns a fixed answer and PDF page citation from its fictional guide. Ask for a forecast to see **No evidence found**. This flow needs no Gemini key.
2. To show a live model call, sign in as an administrator and open **Knowledge Sources**. Choose **Add Gemini demo PDF**, publish the processed fictional PDF and try a fixed question in **Gemini answer preview**. Follow the [local Gemini setup](DEVELOPMENT.md) for the server key and worker.

The sample is built into WagaMaga, so the portfolio walkthrough needs no publisher outreach or external agricultural review.

The admin **Knowledge Sources** page at `/admin/knowledge` also demonstrates synthetic PDF upload, review, publication and withdrawal. The worker extracts selectable text by PDF page number. Each publication decision records the admin, request and time against an immutable version.

The same page lists the public reference passages used by Chilli questions. For a local PDF, enter a source title, upload, review its extracted text and publish. Choose **Upload replacement PDF** on a published PDF to queue an updated version. Publishing the reviewed replacement withdraws the previous version atomically. Check old extracted pages under the withdrawn version. An uploaded PDF enters the existing reviewed-excerpt workflow independently of the public reference set.

## Initial knowledge scope

English evidence applicable to chilli cultivation in the validated target area. A directory listing or government publisher does not by itself establish reuse rights, freshness or relevance. Sinhala/Tamil sources may be inventoried but do not establish supported multilingual retrieval.

From a processed draft PDF in **Knowledge Sources**, open **Preview Sinhala matches for chilli questions**. Each fixed English question has handpicked Sinhala search terms. The app shows up to ten matching pages from that draft. Compare candidate passages against the original PDF, especially on pages with multiple columns or legacy fonts. The preview is read only and local to administrators. Published evidence review, scoring and farmer eligibility remain separate from the draft preview.

On a matching page, choose **Preview answer locally**, paste an exact Sinhala quote and enter its draft English translation. **Show local preview** displays that translation, the original quote and a link that opens the extracted PDF page. Try PDF page 26 using the [nursery quote and draft translation](KNOWLEDGE_SOURCE_REVIEW.md#ch-01-candidate-translation-for-review). The preview checks that the quote occurs on the page. Review the translation's meaning yourself. The preview sends nothing to Gemini.

Choose **Chilli questions → Search reviewed excerpts locally** to try source-backed answers in development. In Knowledge Sources, publish the eligible PDF and save a suitable decision for the matching question, with the exact quote and a reviewed English translation for Sinhala. The local search supports the three displayed English questions and selected variants about chilli nursery sites, irrigation conditions and fertilizer checks. It returns approved wording with a page citation or **No evidence found**. Withdrawing the PDF or removing the suitable decision makes the passage unavailable. This workflow is separate from live Gemini scoring and the farmer pilot release.

## Source inventory

For each candidate, record stable source ID, publisher, title, original URL/file, language, crop/area applicability, publication date (or explicitly unknown), validity period, access date, rights/permission note, reviewer, review date and inclusion status. Retain rejection reasons and extraction limitations.

Only eligible, reviewed versions enter farmer retrieval. File checks, parsing or indexing success alone does not publish a source. Preserve immutable version/checksum, passage ID, exact text, page/section locator, embedding model and index version. Withdrawn versions are excluded from new retrieval and block dependent new execution; authorized historical citations remain labelled and resolvable under the retention policy.

## Dataset design

Use at least 10 evidence-mapped V0 questions and at least 30 labelled V1 questions. Cover exact crop terms, paraphrases, insufficient farm context, missing/outdated/conflicting evidence, inapplicable area/crop and malicious instructions in sources.

Each case should include case ID, question, authorized synthetic context, corpus version, answerable flag, relevant passage IDs, expected limitations/abstention, prohibited claims and human reviewer notes. Multiple relevant passages may be needed; do not evaluate only one convenient source when the question needs several.

## Retrieval experiments

In **Knowledge Sources**, open **Review the 10 chilli questions**. Select a case, expand the retrieved pages and record **Suitable** or **Out of scope** for each page. Use **Mark evidence missing** if no candidate is suitable. The screen shows the fixed keywords and the pilot context to check. This is a human evidence-labeling step. The workflow stores review decisions locally and does not send agricultural questions or PDF text to Gemini. The built-in fictional Gemini PDF is excluded.

Published evidence review finds pages with the fixed English or Sinhala keywords. Reviews can reference any retrieved PDF page from 1 to 100. For a suitable page, paste the exact portion into **Approved quote for a suitable page**. For a Sinhala quote, verify and enter its English wording in **Approved English translation**. The app verifies the original against the extracted page and stores it alongside the translation. The reviewer checks meaning and applicability. Start with the [nursery passage in the source review worksheet](KNOWLEDGE_SOURCE_REVIEW.md#ch-01-candidate-translation-for-review).

Open **Gemini scoring** and run each case once it is ready. Cited cases require an eligible source fingerprint in the server's outbound allowlist. Gemini receives the approved English wording and must return it exactly with its citation. The farmer sees that English wording and the original quoted text with the PDF page citation. Missing-evidence checks exercise the local abstention path without an API call. CH-06 through CH-10 require missing evidence or missing context for this pilot. The embedded-instruction scenario still needs separate evaluation with an adversarial fixture.

Farmer access requires ten current passes, including at least one cited result, and an explicit release setting. Changes to saved labels, the candidate result set or the configured model require a new score on the affected case. The farmer page offers the fixed pilot questions and shows the cited PDF page as text. Current publication and scoring eligibility are checked on answer and source requests.

The local admin preview implements keyword search over successfully processed, currently published PDF pages. PostgreSQL uses its `simple` full text configuration to match all query terms on one page and rank matches. The results cite the immutable version ID, original SHA-256 and PDF page number. Use synthetic documents to exercise this milestone. Publication state is checked on each search. Hybrid retrieval, applicability filtering and farmer-facing answers remain later work.

Compare full text only, vector only and hybrid on the same corpus/questions. Use the architecture's initial reciprocal-rank fusion and candidate sizes as tuning starting points, not validated optimums. Record query/configuration, ranks, eligible passages, latency and versions.

For an answerable question, Recall@5 is the fraction of its labelled relevant passages present in the first five eligible results. Report the aggregate method and per-case results. V1 target is >= 0.80; unanswerable questions are assessed for abstention rather than included as recall successes. Check source applicability independently of rank.

## Answer review

The local Gemini preview tests fixed fictional questions. It retrieves only published pages of a built-in sample PDF identified by its checksum. The server sends only prewritten question text and its own fictional page text, then checks that the returned citation ID and exact quotation match the retrieved page. The 10 draft agricultural questions require approved versions, confirmed reference passages and human review before a live evaluation. Use the sample preview to verify the request and citation flow independently of agricultural answer quality.

Verify that every citation resolves to a permitted passage. Have a human assess support for each material agricultural claim and applicability to the supplied context. Record supported/unsupported/uncertain outcomes, reviewer identity and reasons. V1 target is >= 90% supported material claims, with the denominator stated. Any unsupported actionable treatment recommendation fails release, regardless of the average score.

An LLM judge may assist triage, but cannot replace the required human review. Schema/citation validity does not prove agricultural correctness. Do not fabricate expert review or validated thresholds for demonstration data.

## Runs and reports

The [32-question candidate PDF baseline](../evaluation/reports/chilli-real-pdf-candidate-2026-11-25.md) measures keyword retrieval on the two CC BY research papers. Independent suitability and claim review remain open. Production farmer advisory release requires the operator’s quality report attestation and the existing applicable pilot checks. [Release configuration](OPERATIONS.md#farmer-advisory-release)

The [32-question local report](../evaluation/reports/chilli-anuradhapura-v1-2026-11-24.md) records the current retrieval and answer checks for the public reference set.

Keep datasets in `evaluation/datasets/` and reports in `evaluation/reports/` when created. Record date, commit, corpus/document versions, embedding/index version, model/provider, prompt version, retrieval settings, timeouts, usage/cost, metrics, human findings and unresolved failures.

Use deterministic provider responses for ordinary integration tests. Run live-model evaluation separately with suitable credentials and an agreed usage budget. A fake embedding/model run verifies plumbing and must not be reported as measured retrieval/answer quality.

Before changing a model, chunking, prompt, fusion setting or evidence corpus, rerun the relevant fixed evaluation and compare with the previous baseline. Keep the prior report; do not overwrite historical evidence.
