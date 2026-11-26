import { Link } from 'react-router'
import Notice from '../../components/Notice'
import { farmWrite } from '../../lib/farms'
import { useRecord, useSave } from '../farms/record-hooks'

const root = '/admin/knowledge/evaluation/scores'
type Score = {
  case_id: string
  question: string
  expected: 'pending' | 'cited' | 'no_evidence'
  reason: string
  passed: boolean | null
  detail: string
}

export default function KnowledgeScoringPage() {
  const record = useRecord<{
    cases: Score[]
    ready: boolean
    released: boolean
    independent_review_pending: boolean
  }>(`${root}/summary`)
  const save = useSave((error) =>
    error instanceof Error
      ? error.message
      : 'The check could not be completed.',
  )
  return (
    <>
      <div className="page-intro">
        <Link to="/admin/knowledge/evaluation">Back to evidence review</Link>
        <h1>Gemini scoring</h1>
        <p>Check citations on approved quotes and confirm evidence gaps.</p>
      </div>
      <section className="panel" aria-label="Evaluation results">
        <button
          disabled={save.busy}
          onClick={() => {
            save.reset()
            record.reload()
          }}
        >
          Refresh scores
        </button>
        {record.loading && <p role="status">Loading scores…</p>}
        {record.error !== undefined && (
          <Notice message="Scores could not be loaded." />
        )}
        {save.error && <Notice message={save.error} />}
        {save.busy && <p role="status">Running check…</p>}
        {record.data && (
          <>
            <p>
              {record.data.cases.filter((item) => item.passed === true).length}{' '}
              of 10 passed.{' '}
              {record.data.released
                ? 'Farmer pilot open.'
                : record.data.ready
                  ? 'Ready for pilot release.'
                  : 'Farmer pilot awaiting checks.'}
            </p>
            {record.data.independent_review_pending && (
              <p>
                The independent agricultural quality review is still pending.
              </p>
            )}
            {record.data.cases.map((item) => (
              <article className="panel" key={item.case_id}>
                <h2>
                  {item.case_id} · {item.question}
                </h2>
                <p>
                  {item.reason ||
                    item.detail ||
                    (item.expected === 'cited'
                      ? 'Check a cited quote.'
                      : 'Check the no-evidence result.')}
                </p>
                {item.passed !== null && (
                  <p>
                    <strong>{item.passed ? 'Passed' : 'Failed'}</strong>
                  </p>
                )}
                <button
                  disabled={
                    item.expected === 'pending' || save.busy || save.blocked
                  }
                  onClick={() => {
                    void save.run(
                      () => farmWrite(`${root}/${item.case_id}`, 'POST', {}),
                      record.reload,
                    )
                  }}
                >
                  Run check
                </button>
              </article>
            ))}
          </>
        )}
      </section>
    </>
  )
}
