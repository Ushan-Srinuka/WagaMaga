import { useState } from 'react'
import PdfAttribution, { type PdfProvenance } from './PdfAttribution'
import { Link } from 'react-router'
import Notice from '../../components/Notice'
import { farmWrite } from '../../lib/farms'
import { useRecord, useSave } from '../farms/record-hooks'
import ResearchPassage from './ResearchPassage'

const chilliPath = '/knowledge/chilli'
const guidancePath = `${chilliPath}/guidance`
const demoPath = `${chilliPath}/demo`
const localPath = `${chilliPath}/local`
const pageContent = {
  research: {
    path: `${chilliPath}/research`,
    heading: 'Ask Chilli AI',
    intro:
      'Find answers about nursery setup, irrigation and soil testing from Sri Lankan sources.',
    help: 'Try an example below. The answers provide general information about chilli cultivation.',
  },
  pilot: {
    path: chilliPath,
    heading: 'Chilli farm guidance',
    intro: 'Find reviewed information for the Anuradhapura chilli pilot.',
    help: '',
  },
  demo: {
    path: demoPath,
    heading: 'Chilli questions demo',
    intro: 'Practise finding answers in a fictional farm notebook.',
    help: 'Ask about the nursery tray label or what the irrigation and fertilizer logs record.',
  },
  local: {
    path: localPath,
    heading: 'Search reviewed chilli excerpts',
    intro: 'Find answers and source excerpts in your local knowledge library.',
    help: 'Ask about nursery site selection, irrigation conditions, or what to check before choosing fertilizer.',
  },
} as const
type Question = { id: string; question: string }
type Answer =
  | { status: 'no_evidence' }
  | {
      status: 'answered'
      kind?: never
      answer: string
      case_id?: string
      reference_only?: boolean
      citation: PdfProvenance & {
        title: string
        version_id: string
        number: number
        excerpt: string
        publisher?: string | null
      }
    }
  | {
      status: 'answered'
      kind: 'research'
      method: 'reference' | 'gemini'
      answer: string
      corpus_version: string
      passage_id: string
      citation: {
        title: string
        publisher: string
        url: string
      } & (
        | {
            section: string
          }
        | {
            authors: string
            year: number
            license_url: string
            journal_page: number
            pdf_page: number
          }
      )
    }

export default function ChilliQuestionsPage({
  mode = 'research',
}: {
  mode?: keyof typeof pageContent
}) {
  const { path: root, heading, intro, help } = pageContent[mode]
  const typed = mode !== 'pilot'
  const record = useRecord<{ released?: boolean; cases: Question[] }>(root)
  const save = useSave((error) =>
    error instanceof Error ? error.message : 'The answer is unavailable.',
  )
  const [selected, setSelected] = useState('')
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<Answer | null>(null)
  const [showPage, setShowPage] = useState(false)
  const selectedId = selected || record.data?.cases[0]?.id || ''
  const canAnswer = typed || record.data?.released === true
  const canSubmit =
    !save.busy && !save.blocked && Boolean(typed ? question.trim() : selectedId)
  const pdf =
    result?.status === 'answered' && result.kind !== 'research' ? result : null
  const citation = pdf?.citation
  const referenceOnly = pdf?.reference_only
  const citedCaseId = pdf && (typed ? pdf.case_id : selectedId)
  const source = useRecord<{ number: number; text: string }>(
    showPage && citation && citedCaseId
      ? `${root}/${citedCaseId}/sources/${citation.version_id}/pages/${citation.number}`
      : null,
  )

  function resetAnswer() {
    setResult(null)
    setShowPage(false)
  }

  function updateQuestion(value: string) {
    setQuestion(value)
    resetAnswer()
    save.reset()
  }

  return (
    <>
      <div className="page-intro">
        <Link className="back-link" to="/">
          ← Home
        </Link>
        <h1>{heading}</h1>
        <p>{intro}</p>
        {mode === 'pilot' && (
          <p>Scope · Chilli cultivations in Anuradhapura District.</p>
        )}
        {mode !== 'research' && (
          <Link to={chilliPath}>Back to Ask Chilli AI</Link>
        )}
        {mode === 'research' && (
          <Link to="/knowledge/chilli/crop">Ask about my crop</Link>
        )}
      </div>
      <section className="panel" aria-label="Chilli answers">
        {record.loading && <p role="status">Loading chilli questions…</p>}
        {record.error !== undefined && (
          <Notice message="Chilli questions could not be loaded." />
        )}
        {mode === 'pilot' && record.data && (
          <p role="status">
            {record.data.released
              ? 'Pilot status · Available for the listed questions.'
              : 'Pilot status · Chilli answers are still being reviewed.'}
          </p>
        )}
        {record.data && canAnswer && (
          <form
            onSubmit={(event) => {
              event.preventDefault()
              if (!canSubmit) return
              resetAnswer()
              void save.run(
                () =>
                  typed
                    ? farmWrite<Answer>(`${root}/ask`, 'POST', {
                        question: question.trim(),
                      })
                    : farmWrite<Answer>(`${root}/answer`, 'POST', {
                        case_id: selectedId,
                      }),
                setResult,
              )
            }}
          >
            {typed ? (
              <>
                <div className="field">
                  <label htmlFor="chilli-question">
                    What would you like to ask about chilli?
                  </label>
                  <input
                    id="chilli-question"
                    type="text"
                    value={question}
                    maxLength={240}
                    required
                    disabled={save.busy}
                    aria-describedby="typed-question-help"
                    onChange={(event) => updateQuestion(event.target.value)}
                  />
                  <small id="typed-question-help">{help}</small>
                </div>
              </>
            ) : (
              <div className="field">
                <label htmlFor="chilli-question">Choose a question</label>
                <select
                  id="chilli-question"
                  value={selectedId}
                  disabled={save.busy}
                  onChange={(event) => {
                    setSelected(event.target.value)
                    resetAnswer()
                    save.reset()
                  }}
                >
                  {record.data.cases.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.question}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <button className="primary" disabled={!canSubmit}>
              Find an answer
            </button>
            {typed && (
              <div
                className="button-row"
                role="group"
                aria-label="Example questions"
              >
                {record.data.cases.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    disabled={save.busy}
                    onClick={() => updateQuestion(item.question)}
                  >
                    {item.question}
                  </button>
                ))}
              </div>
            )}
          </form>
        )}
        {record.error || save.error || mode === 'pilot' ? (
          <button
            disabled={save.busy}
            onClick={() => {
              resetAnswer()
              save.reset()
              record.reload()
            }}
          >
            {mode === 'pilot' ? 'Refresh' : 'Try again'}
          </button>
        ) : null}
        {save.busy && <p role="status">Finding an answer…</p>}
        {save.error && <Notice message={save.error} />}
        {result?.status === 'no_evidence' && (
          <div role="status">
            <p>No evidence found.</p>
            {mode === 'research' && (
              <p>
                Try an example question. Advice for a specific plot needs local
                evidence.
              </p>
            )}
            {mode === 'pilot' && (
              <p>
                The reviewed pilot sources do not support an answer for this
                question.
              </p>
            )}
          </div>
        )}
        {result?.status === 'answered' && result.kind === 'research' && (
          <article
            className="panel"
            aria-label="Cited answer"
            aria-live="polite"
          >
            <p className="muted">
              {result.method === 'gemini'
                ? 'Research summary selected with Gemini'
                : 'section' in result.citation
                  ? 'Department of Agriculture reference'
                  : 'Published research summary'}
            </p>
            <p>{result.answer}</p>
            <ResearchPassage
              key={result.passage_id}
              id={result.passage_id}
              version={result.corpus_version}
            />
            {'section' in result.citation ? (
              <>
                <p>
                  <strong>{result.citation.title}</strong> ·{' '}
                  {result.citation.section}
                </p>
                <a
                  href={result.citation.url}
                  target="_blank"
                  rel="noreferrer"
                  hrefLang="si"
                >
                  Read the Department of Agriculture source (Sinhala)
                </a>
              </>
            ) : (
              <>
                <p>
                  <strong>{result.citation.title}</strong> · Journal page{' '}
                  {result.citation.journal_page} · PDF page{' '}
                  {result.citation.pdf_page}
                </p>
                <p className="muted">
                  {result.citation.authors} ({result.citation.year}) ·{' '}
                  {result.citation.publisher}
                </p>
                <div className="button-row">
                  <a
                    href={result.citation.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Read the published study
                  </a>
                  <a
                    href={result.citation.license_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    CC BY 4.0
                  </a>
                </div>
              </>
            )}
          </article>
        )}
        {pdf && (
          <article className="panel" aria-label="Cited answer">
            {referenceOnly && (
              <p>
                <strong>Local PDF reference</strong> · Draft translation
              </p>
            )}
            <p>{pdf.answer}</p>
            <p>
              {pdf.citation.title} · Page {pdf.citation.number}
            </p>
            <p className="record-note">
              Source version · {pdf.citation.version_id}
            </p>
            {pdf.citation.publisher && <p>{pdf.citation.publisher}</p>}
            <PdfAttribution source={pdf.citation} />
            {!referenceOnly && pdf.citation.excerpt !== pdf.answer && (
              <blockquote lang="si">{pdf.citation.excerpt}</blockquote>
            )}
            <button
              aria-expanded={showPage}
              onClick={() => setShowPage((shown) => !shown)}
            >
              {showPage ? 'Hide' : 'Read'}{' '}
              {referenceOnly ? 'cited excerpt' : 'cited page'}
            </button>
            {source.loading && <p role="status">Loading cited page…</p>}
            {source.error !== undefined && (
              <Notice message="This page is no longer available." />
            )}
            {source.data && (
              <p
                lang={referenceOnly ? 'si' : undefined}
                style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}
              >
                {source.data.text}
              </p>
            )}
          </article>
        )}
      </section>
      {mode === 'research' && (
        <div className="button-row">
          <Link to={guidancePath}>Chilli farm guidance</Link>
          <Link to="/planner">Ask about my tasks</Link>
          {import.meta.env.DEV && (
            <>
              <Link to={localPath}>Search reviewed excerpts locally</Link>
              <Link to={demoPath}>Try the local demo</Link>
            </>
          )}
        </div>
      )}
    </>
  )
}
