import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import Notice from '../../components/Notice'
import { ApiError } from '../../lib/accounts'
import { farmWrite } from '../../lib/farms'
import { useRecord, useSave } from '../farms/record-hooks'

const root = '/admin/knowledge/evaluation'
type Outcome = 'suitable' | 'out_of_scope' | 'missing'
type Decision = {
  outcome: Outcome
  note: string
  revision: number
  approved_excerpt: string
  english_translation: string
}
type PageMatch = {
  version_id: string
  title: string
  number: number
  excerpt: string
}
type CandidatePage = PageMatch & { decision: Decision | null }
type Question = { id: string; question: string }
type ReviewCase = Question & {
  keywords: string
  sinhala_keywords: string
  review_focus: string
  revision: number
  pages: CandidatePage[]
  missing: Decision | null
}

const labels: Record<Outcome, string> = {
  suitable: 'Suitable',
  out_of_scope: 'Out of scope',
  missing: 'Missing evidence',
}

function PageText({ candidate }: { candidate: PageMatch }) {
  const pages = useRecord<{ number: number; text: string }[]>(
    `/admin/knowledge/sources/${candidate.version_id}/pages`,
  )
  const page = pages.data?.find((item) => item.number === candidate.number)
  if (pages.loading) return <p role="status">Loading page text…</p>
  if (!page) return <Notice message="The page text is unavailable." />
  return (
    <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
      {page.text}
    </p>
  )
}

function DraftAnswerPreview({
  caseId,
  page,
  showPage,
}: {
  caseId: string
  page: PageMatch
  showPage: () => void
}) {
  const [quote, setQuote] = useState('')
  const [translation, setTranslation] = useState('')
  const [result, setResult] = useState<{
    answer: string
    citation: PageMatch
  } | null>(null)
  const save = useSave((error) => {
    if (error instanceof ApiError) {
      if (
        error.code === 'INVALID_EXCERPT' ||
        error.code === 'SINHALA_QUOTE_REQUIRED'
      )
        return 'Copy the exact Sinhala quote from the selected page.'
      if (error.code === 'TRANSLATION_REQUIRED')
        return 'Enter the English translation of the quote.'
      if (error.status === 404 || error.status === 409)
        return 'This page is no longer available for the draft preview.'
      return error.message
    }
    return 'The local preview could not be loaded.'
  })

  return (
    <>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          setResult(null)
          void save.run(
            () =>
              farmWrite<{ answer: string; citation: PageMatch }>(
                `${root}/${caseId}/draft-answer`,
                'POST',
                {
                  version_id: page.version_id,
                  page_number: page.number,
                  excerpt: quote.trim(),
                  english_translation: translation.trim(),
                },
              ),
            setResult,
          )
        }}
      >
        <p>
          Check how your draft translation and citation will appear. This
          preview runs locally.
        </p>
        <div className="field">
          <label htmlFor="draft-quote">Exact Sinhala quote</label>
          <textarea
            id="draft-quote"
            lang="si"
            value={quote}
            maxLength={500}
            required
            disabled={save.busy}
            onChange={(event) => {
              setQuote(event.target.value)
              setResult(null)
              save.reset()
            }}
          />
        </div>
        <div className="field">
          <label htmlFor="draft-translation">English translation</label>
          <textarea
            id="draft-translation"
            value={translation}
            maxLength={500}
            required
            disabled={save.busy}
            onChange={(event) => {
              setTranslation(event.target.value)
              setResult(null)
              save.reset()
            }}
          />
        </div>
        <button
          disabled={
            save.busy || save.blocked || !quote.trim() || !translation.trim()
          }
        >
          Show local preview
        </button>
      </form>
      {save.error && <Notice message={save.error} />}
      {result && (
        <section
          className="panel"
          aria-label="Local answer preview"
          aria-live="polite"
        >
          <h3>Draft answer</h3>
          <p>{result.answer}</p>
          <blockquote lang="si" style={{ overflowWrap: 'anywhere' }}>
            {result.citation.excerpt}
          </blockquote>
          <a href={`#draft-page-${result.citation.number}`} onClick={showPage}>
            Read extracted PDF page {result.citation.number}
          </a>
        </section>
      )}
    </>
  )
}

function DraftMatches({
  caseId,
  versionId,
}: {
  caseId: string
  versionId: string
}) {
  const params = new URLSearchParams({ version_id: versionId })
  const record = useRecord<{ keywords: string; pages: PageMatch[] }>(
    `${root}/${caseId}/draft-matches?${params}`,
  )
  const [expanded, setExpanded] = useState<number | null>(null)
  const [previewPage, setPreviewPage] = useState<number | null>(null)

  return (
    <section className="panel" aria-label="Sinhala draft matches">
      {record.loading && <p role="status">Finding matching pages…</p>}
      {record.error !== undefined && (
        <>
          <Notice message="Could not search this draft. Check that it is still a processed draft in Knowledge Sources." />
          <button onClick={record.reload}>Try again</button>
        </>
      )}
      {record.data && (
        <>
          <p>
            Search keywords: <span lang="si">{record.data.keywords}</span>
          </p>
          {record.data.pages.length === 0 && (
            <p>No pages matched in this draft.</p>
          )}
          {record.data.pages.map((page) => (
            <article
              className="panel"
              key={page.number}
              id={`draft-page-${page.number}`}
            >
              <h2>PDF page {page.number}</h2>
              <p lang="si" style={{ overflowWrap: 'anywhere' }}>
                {page.excerpt}
              </p>
              <div className="button-row">
                <button
                  aria-expanded={expanded === page.number}
                  onClick={() =>
                    setExpanded(expanded === page.number ? null : page.number)
                  }
                >
                  {expanded === page.number
                    ? 'Hide page text'
                    : 'Read page text'}
                </button>
                <button
                  aria-expanded={previewPage === page.number}
                  onClick={() =>
                    setPreviewPage(
                      previewPage === page.number ? null : page.number,
                    )
                  }
                >
                  {previewPage === page.number
                    ? 'Hide local preview'
                    : 'Preview answer locally'}
                </button>
              </div>
              {expanded === page.number && <PageText candidate={page} />}
              {previewPage === page.number && (
                <DraftAnswerPreview
                  caseId={caseId}
                  page={page}
                  showPage={() => setExpanded(page.number)}
                />
              )}
            </article>
          ))}
        </>
      )}
    </section>
  )
}

function SavedDecision({ decision }: { decision: Decision }) {
  return (
    <p style={{ overflowWrap: 'anywhere' }}>
      <strong>{labels[decision.outcome]}</strong>
      {decision.note && <> · {decision.note}</>}
      {decision.approved_excerpt && (
        <>
          <br />
          Approved quote: {decision.approved_excerpt}
        </>
      )}
      {decision.english_translation && (
        <>
          <br />
          Approved English translation: {decision.english_translation}
        </>
      )}
    </p>
  )
}

function CaseReview({ caseId }: { caseId: string }) {
  const record = useRecord<ReviewCase>(`${root}/${caseId}`)
  const save = useSave((error) =>
    error instanceof Error ? error.message : 'The decision could not be saved.',
  )
  const [note, setNote] = useState('')
  const [excerpt, setExcerpt] = useState('')
  const [translation, setTranslation] = useState('')
  const [expanded, setExpanded] = useState('')
  const [saved, setSaved] = useState(false)
  const data = record.data
  const disabled = save.busy || save.blocked || record.loading
  const needsTranslation = /[\u0d80-\u0dff]/u.test(excerpt)
  const hasSuitable = data?.pages.some(
    (page) => page.decision?.outcome === 'suitable',
  )

  function decide(outcome: Outcome, candidate?: CandidatePage) {
    if (!data) return
    setSaved(false)
    void save.run(
      () =>
        farmWrite<Decision>(`${root}/${caseId}/decisions`, 'POST', {
          expected_revision: data.revision,
          outcome,
          note: note.trim(),
          approved_excerpt: outcome === 'suitable' ? excerpt.trim() : '',
          english_translation:
            outcome === 'suitable' && needsTranslation
              ? translation.trim()
              : '',
          ...(candidate && {
            version_id: candidate.version_id,
            page_number: candidate.number,
          }),
        }),
      () => {
        setNote('')
        setExcerpt('')
        setTranslation('')
        setSaved(true)
        record.reload()
      },
    )
  }

  return (
    <section className="panel" aria-label="Question evidence">
      <button
        disabled={save.busy}
        onClick={() => {
          save.reset()
          setSaved(false)
          setExpanded('')
          record.reload()
        }}
      >
        Refresh evidence
      </button>
      {record.loading && <p role="status">Loading evidence…</p>}
      {record.error !== undefined && (
        <Notice message="Evidence could not be loaded." />
      )}
      {save.error && <Notice message={save.error} />}
      {saved && <p role="status">Decision saved.</p>}
      {data && (
        <>
          <h2>{data.question}</h2>
          <p>{data.review_focus}</p>
          <p>
            Search keywords: {data.keywords} ·{' '}
            <span lang="si">{data.sinhala_keywords}</span>
          </p>
          <div className="field">
            <label htmlFor="evaluation-note">Review note (optional)</label>
            <textarea
              id="evaluation-note"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              disabled={save.busy}
              maxLength={500}
              rows={2}
            />
            <small>The note is saved with the next decision.</small>
          </div>
          {data.pages.length > 0 && (
            <div className="field">
              <label htmlFor="evaluation-excerpt">
                Approved quote for a suitable page
              </label>
              <textarea
                id="evaluation-excerpt"
                value={excerpt}
                onChange={(event) => {
                  setExcerpt(event.target.value)
                  setTranslation('')
                }}
                disabled={save.busy}
                maxLength={500}
                rows={2}
              />
              <small>
                Copy exact text from the page. Scoring requires a saved quote.
              </small>
            </div>
          )}
          {data.pages.length > 0 && needsTranslation && (
            <div className="field">
              <label htmlFor="evaluation-translation">
                Approved English translation
              </label>
              <textarea
                id="evaluation-translation"
                value={translation}
                onChange={(event) => setTranslation(event.target.value)}
                disabled={save.busy}
                maxLength={500}
                rows={2}
              />
              <small>
                Check that the translation preserves the meaning of the exact
                Sinhala quote.
              </small>
            </div>
          )}
          {data.pages.length === 0 && <p>No published PDF pages matched.</p>}
          {data.missing && <SavedDecision decision={data.missing} />}
          <button
            disabled={disabled || hasSuitable}
            onClick={() => decide('missing')}
          >
            Mark evidence missing
          </button>
          {data.pages.map((candidate) => {
            const key = `${candidate.version_id}:${candidate.number}`
            return (
              <article className="panel" key={key}>
                <h3>
                  {candidate.title} · Page {candidate.number}
                </h3>
                <p>Version {candidate.version_id.slice(0, 8)}</p>
                <p style={{ overflowWrap: 'anywhere' }}>{candidate.excerpt}</p>
                {candidate.decision && (
                  <SavedDecision decision={candidate.decision} />
                )}
                <div className="button-row">
                  <button
                    aria-expanded={expanded === key}
                    onClick={() => setExpanded(expanded === key ? '' : key)}
                  >
                    {expanded === key ? 'Hide page text' : 'Read page text'}
                  </button>
                  <button
                    disabled={
                      disabled || (needsTranslation && !translation.trim())
                    }
                    onClick={() => decide('suitable', candidate)}
                  >
                    Mark suitable
                  </button>
                  <button
                    disabled={disabled}
                    onClick={() => decide('out_of_scope', candidate)}
                  >
                    Mark out of scope
                  </button>
                </div>
                {expanded === key && <PageText candidate={candidate} />}
              </article>
            )
          })}
        </>
      )}
    </section>
  )
}

export default function KnowledgeEvaluationPage() {
  const [params] = useSearchParams()
  const draftId = params.get('draft')
  const questions = useRecord<Question[]>(root)
  const [selected, setSelected] = useState('')
  const caseId = selected || questions.data?.[0]?.id || ''

  return (
    <>
      <div className="page-intro">
        <Link to="/admin/knowledge">Back to Knowledge Sources</Link>
        <h1>
          {draftId ? 'Sinhala draft matches' : 'Chilli evidence evaluation'}
        </h1>
        {draftId ? (
          <p>
            Choose a question to find pages in draft {draftId.slice(0, 8)}.
            Compare the extracted text with the original PDF before using it as
            evidence.
          </p>
        ) : (
          <>
            <Link to="/admin/knowledge/scoring">Open Gemini scoring</Link>
            <p>
              Review the PDF pages found for each question about the
              Anuradhapura pilot.
            </p>
          </>
        )}
      </div>
      {questions.loading && <p role="status">Loading questions…</p>}
      {questions.error !== undefined && (
        <>
          <Notice message="Evaluation questions could not be loaded." />
          <button onClick={questions.reload}>Try again</button>
        </>
      )}
      {questions.data && (
        <div className="field">
          <label htmlFor="evaluation-case">Evaluation question</label>
          <select
            id="evaluation-case"
            value={caseId}
            onChange={(event) => setSelected(event.target.value)}
          >
            {questions.data.map((question) => (
              <option key={question.id} value={question.id}>
                {question.id} · {question.question}
              </option>
            ))}
          </select>
        </div>
      )}
      {caseId &&
        (draftId ? (
          <DraftMatches
            key={`${draftId}:${caseId}`}
            caseId={caseId}
            versionId={draftId}
          />
        ) : (
          <CaseReview key={caseId} caseId={caseId} />
        ))}
    </>
  )
}
