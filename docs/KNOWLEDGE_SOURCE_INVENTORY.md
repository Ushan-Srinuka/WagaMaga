# Chilli pilot source inventory

These records identify candidate sources for a possible future chilli pilot in Anuradhapura, Sri Lanka. The portfolio demo uses the [built-in fictional guide](KNOWLEDGE_EVALUATION.md#portfolio-demo).

| Source ID | Publisher and edition | Language and availability | Crop, area and date | Review priority |
| --- | --- | --- | --- | --- |
| DOA-CHILLI-2023-SI | Sri Lanka DOA / NAICC, [Chilli Cultivation – 2023, Sinhala](https://drive.google.com/file/d/13lP5aFFSfHuBCTiNEDhbRlbGdk2Tw5z0/view) | Sinhala. Catalogue link and PDF title verified. Pages await inspection. | Chilli. 2023 catalogue edition. Exact publication date, validity and applicability to Anuradhapura pending. | Core guide candidate. |
| DOA-CHILLI-2023-TA | Sri Lanka DOA / NAICC, [Chilli Cultivation – 2023, Tamil](https://drive.google.com/file/d/1RyA4s4WSZeEQp9ZD2dXULGb1-JvFcgvt/view) | Tamil. Catalogue link verified. File preview could not be checked. | Chilli. 2023 catalogue edition. Exact publication date, validity and applicability to Anuradhapura pending. | Alternate edition. Review and version it separately. |
| DOA-CHILLI-WEB-SI | Sri Lanka DOA / FCRDI, [Field Crops – Chilli](https://doa.gov.lk/field-crops-chilli-si/) | Sinhala HTML. Nursery, field planting, irrigation and fertilizer sections inspected for locators. | Chilli. Publication date and validity unknown. District and growing conditions require confirmation. | First HTML parsing candidate. A reviewer must check technical passages for current applicability. |
| DOA-CHILLI-NURSERY-SI | Sri Lanka DOA / NAICC, [Chili nursery management, Other field crops item 3](https://doa.gov.lk/naicc-publications-agriculture-leaflets/) | Sinhala edition listed alongside Tamil. File and pages await inspection. | Chilli nursery. Publication date, validity and applicability to Anuradhapura pending. | Supporting guide. Compare with the core guide to identify gaps or conflicts. |
| DOA-AGROMET-2026-OND-EN | Sri Lanka DOA, [October–December 2026 agro-met advisory](https://drive.google.com/file/d/1OWo_7STnxMwPFnrAsaxCkIqkkX3gDFZ_/view) | English edition listed. File title verified. Pages await inspection. | Seasonal, nominal window October–December 2026 per the catalogue. Exact issue date, crop coverage, zones, validity and supersession require confirmation. | Seasonal evidence candidate. Check the advisory date and zone on every relevant case. |

Listing references include the [2023 core guide catalogue](https://doa.gov.lk/naicc-books/), the [FCRDI download catalogue](https://doa.gov.lk/fcrdi-downloads/) and the [agro-met advisory archive](https://doa.gov.lk/agro-met-advisory/). Catalogue links were checked on 19 November 2026. Reuse permission, reviewer identity and review date are pending for every row.

## Review and publication

### English research PDFs prepared for draft upload

Both publisher copies passed the local extraction check on 19 November 2026. The originals are staged in the ignored `.data/knowledge-import/` directory. These studies are research candidates for local applicability review.

| Source ID | Attribution and publisher | Scope to review | File and SHA-256 |
| --- | --- | --- | --- |
| DOA-CHILLI-DRY-ZONE-2025-EN | H. G. B. P. Darshana, M. A. R. A. Mandanayake and U. G. A. I. Sirisena, *Field Evaluation of Chilli Cultivation Practices and Their Effectiveness in Managing the Leaf Curl Complex under Dry Zone Conditions in Sri Lanka*, Department of Agriculture, 30 June 2025. [Publisher and CC BY 4.0](https://reference-global.com/article/10.4038/ta.v173i1.128?tab=download) | Chilli under Sri Lankan dry zone field conditions. Confirm applicability to the pilot area and production system. | `doa-chilli-dry-zone-2025.pdf`, 18 text pages, `89a3181b9dbc2be5e9007d2c920abb090a14014b5ac26d2fd83cf5cb4cf2723f` |
| RUSL-CHILLI-POLYTUNNEL-2025-EN | D. A. U. D. Devasinghe and W. M. D. M. Wickramasinghe, *Growth and Yield of Hybrid Chilli in Response to Diverse Nutrient Management Strategies in a Soil-Based Medium*, Rajarata University of Sri Lanka, 8 December 2025. [Publisher and CC BY 4.0](https://reference-global.com/article/10.4038/sljae.v7i1.156?tab=download) | Hybrid chilli in polytunnels. Keep the scope tied to the study conditions. | `rajarata-chilli-polytunnel-2025.pdf`, 16 text pages, `aee484eb35844568e555b1dbed8df97e315d3df1a17fd6afcf6193847643699b` |

Keep the publisher attribution and [license link](https://creativecommons.org/licenses/by/4.0/) with extracted evidence. Keep both versions at Draft until review. Gemini processing remains pending.

### Review instructions for a future farmer pilot

Use the [source review packet](KNOWLEDGE_SOURCE_REVIEW.md) for the first edition and case-to-passage review worksheet.

1. Verify the canonical file and edition. Record access date, publisher, original URL, version checksum, extraction results and exact page or section locators.
2. Record the license or other reuse basis for storage, indexing, excerpt display and provider processing. Use sources with terms that cover the intended uses.
3. Have a reviewer who reads the source language check crop, area or agroecological zone, growing conditions, season, expiry and any superseding guidance. Record the reviewer, date, accepted sections and reasons for exclusions. Sinhala and Tamil evidence remains candidate material under the current English-first scope.
4. Require successful file checks, parsing and indexing plus a recorded review before an authorized admin publishes that version. Revisions get new checksums and fresh reviews. Exclude withdrawn and superseded versions from new retrieval.
5. Before the live Gemini prototype, map [the draft cases](../evaluation/datasets/chilli-anuradhapura-v0-draft.md) to exact passages from approved versions. Send fictional farm context and only excerpts permitted for provider processing. [Gemini API terms](https://ai.google.dev/gemini-api/terms)
