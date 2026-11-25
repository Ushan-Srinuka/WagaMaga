# Reviewed PDF chat evaluation · 24 November 2026

The [versioned dataset](../datasets/chilli-reviewed-pdf-fixtures-v1.json) contains 32 labelled questions and six fictional PDFs. The fixture uploads, extracts, reviews, publishes and indexes the PDFs through the existing local services. There are 24 answerable questions and eight cases that should return no evidence or ask for clarification. The experiment used synthetic accounts and the Anuradhapura cultivation scope.

## Retrieval with live embeddings

PostgreSQL ran all three modes on the same PDF corpus. Gemini generated 768-dimensional document and query vectors. The denominator is the 24 questions with a labelled relevant document and page.

| Mode | Relevant source in first five | Relevant source ranked first |
| --- | ---: | ---: |
| Keyword | 20/24 | 19/24 |
| Vector | 24/24 | 24/24 |
| Combined | 24/24 | 24/24 |

## Answer and citation checks

- All 32 cases passed the deterministic answer-selection checks using live retrieval results. The quote selector was doubled for this pass. All 24 answerable cases matched the expected document and fact. All eight unsupported cases abstained or requested clarification.
- Eight questions also used the live Gemini quote selector. PDF-01, PDF-05, PDF-09, PDF-13, PDF-17, and PDF-21 each returned a verified quote containing the labelled fact from the correct PDF. PDF-25 and PDF-32 correctly abstained.
- The answer path accepts only a complete supplied sentence with an eligible citation. The privacy test rejects a fabricated quote, denies another account’s chat access, and verifies that deletion preserves an accepted farm plan.
- The source claims describe fictional records. The result supports retrieval, citation, and reference-flow verification for this fixture corpus. Independent agricultural applicability review and evaluation on reviewed real chilli PDFs remain open.

Reproduce with the [PDF chat evaluation commands](../../docs/TESTING.md#reviewed-pdf-chat-and-evaluation).
