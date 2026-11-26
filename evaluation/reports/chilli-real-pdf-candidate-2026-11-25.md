# Chilli PDF candidate baseline · 25 November 2026

The [versioned candidate dataset](../datasets/chilli-real-pdf-candidate-v1.json) contains 32 English questions and synthetic farm contexts. Twenty questions have provisional PDF page labels. Twelve cover missing evidence, expired evidence, conflicting contextual claims, applicability, privacy or untrusted instructions. Local files matched the two published SHA-256 checksums in the dataset. Both papers carry a CC BY 4.0 license. The field study reports dry-zone comparisons, and the Rajarata paper reports a polytunnel experiment. Applicability to an actual Anuradhapura farm still requires independent review. [Dry-zone field study](https://reference-global.com/article/10.4038/ta.v173i1.128?tab=download) · [Rajarata polytunnel study](https://reference-global.com/article/10.4038/sljae.v7i1.156?tab=download)

The runner used the pypdf extraction subprocess, the `page-900-v1` passage rules, the application’s cultivation-scoped keyword query and PostgreSQL 18 with pgvector 0.8.7. A page hit means at least one chunk from the labelled document and page was among the first five chunks. The runner rolled back imported evidence and temporary benchmark changes. It issued zero provider calls. [Reproduction commands](../../docs/TESTING.md#screened-knowledge-and-candidate-evaluation)

| Check | Observation |
| --- | --- |
| Keyword page Recall@5 | 16 of 20, or 80% |
| Missed labels | RP-03, RP-11, RP-13, RP-14 |
| Expired-only corpus | Both cases returned zero chunks |
| Other evidence-gap cases | All ten returned candidates. Candidate retrieval alone cannot show whether the answer should abstain. |

The page labels describe this small candidate corpus. Passage-level semantic and hybrid measurements, independent claim support, actual answer abstentions and unsupported treatment findings remain unmeasured for this corpus. AT04 stays open and the production farmer pilot stays disabled.

For the independent review, confirm the locator and applicability of each label, and record the release-approved source versions, growing conditions and reuse permissions. After an approved corpus and provider budget are available, compare keyword, vector and hybrid results using identical questions and passage-level labels. For each answer, record the citation, support for each material claim, any site-specific limitation and any unsupported actionable recommendation. Keep the signed-off report with the tested model and corpus versions.
