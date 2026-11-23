import { useState } from 'react'
import Notice from '../../components/Notice'
import { farmWrite } from '../../lib/farms'
import { useSave } from '../farms/record-hooks'

const questions = [
  ['nursery', 'What label does the fictional nursery use?'],
  ['records', 'What details does the fictional field record contain?'],
  ['forecast', 'What is tomorrow’s rainfall forecast?'],
]

type Answer =
  | { status: 'no_evidence' }
  | {
      status: 'answered'
      answer: string
      citation: {
        title: string
        version_id: string
        number: number
        checksum: string
      }
    }

export default function KnowledgeAnswerPreview({
  sourcePath,
}: {
  sourcePath: string
}) {
  const [question, setQuestion] = useState('nursery')
  const [result, setResult] = useState<Answer | null>(null)
  const submission = useSave((error) =>
    error instanceof Error
      ? error.message
      : 'The preview could not be completed.',
  )

  return (
    <section className="panel" aria-labelledby="knowledge-answer-title">
      <h2 id="knowledge-answer-title">Gemini answer preview</h2>
      <p>
        Add, process and publish the built-in demo PDF to try these fictional
        questions.
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          setResult(null)
          void submission.run(
            () =>
              farmWrite<Answer>(`${sourcePath}/answer`, 'POST', { question }),
            setResult,
          )
        }}
      >
        <div className="field">
          <label htmlFor="knowledge-preview-question">Demo question</label>
          <select
            id="knowledge-preview-question"
            value={question}
            disabled={submission.busy}
            onChange={(event) => {
              setQuestion(event.target.value)
              submission.reset()
              setResult(null)
            }}
          >
            {questions.map(([id, label]) => (
              <option key={id} value={id}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <button disabled={submission.busy || submission.blocked}>
          Ask Gemini
        </button>
        {submission.blocked && (
          <button type="button" onClick={submission.reset}>
            Reset preview
          </button>
        )}
      </form>
      {submission.busy && (
        <p role="status">Checking evidence and preparing the answer…</p>
      )}
      {submission.error && <Notice message={submission.error} />}
      {result?.status === 'no_evidence' && (
        <p role="status">No evidence found.</p>
      )}
      {result?.status === 'answered' && (
        <article className="panel" aria-label="Cited answer">
          <p>{result.answer}</p>
          <p>
            {result.citation.title} · Page {result.citation.number}
          </p>
          <details>
            <summary>Citation details</summary>
            <p style={{ overflowWrap: 'anywhere' }}>
              Version ID: {result.citation.version_id}
            </p>
            <p style={{ overflowWrap: 'anywhere' }}>
              SHA-256: {result.citation.checksum}
            </p>
          </details>
        </article>
      )}
    </section>
  )
}
