import { useState } from 'react'
import Notice from '../../components/Notice'
import { ApiError } from '../../lib/accounts'
import {
  farmWrite,
  failureText,
  type AdvisorCase,
  type AdvisorOutcome,
  type AdvisorReview,
  type Page,
} from '../../lib/farms'
import { Pagination, ReadState, TextArea } from './RecordUI'
import TaskDateComparison from './TaskDateComparison'
import { useRecord, useSave } from './record-hooks'

const outcomes = {
  cleared: 'Clear suggestion',
  declined: 'Decline suggestion',
  changes_requested: 'Request changes',
}
const recorded = {
  cleared: 'Cleared',
  declined: 'Declined',
  changes_requested: 'Changes requested',
}

export function AssignedReview({
  item,
  replace,
  reload,
}: {
  item: AdvisorCase
  replace: (review: AdvisorReview) => void
  reload: () => void
}) {
  const [reason, setReason] = useState('')
  const save = useSave((error) => {
    if (error instanceof ApiError && error.status === 409)
      return 'This review changed. Reload the assigned case before saving.'
    if (error instanceof ApiError && [403, 404].includes(error.status))
      return 'This review is unavailable for your account.'
    return failureText(error)
  })
  function decide(outcome: AdvisorOutcome) {
    if (!reason.trim()) return
    void save.run(
      () =>
        farmWrite<AdvisorReview>(`/advisor/cases/${item.id}/decision`, 'POST', {
          expected_version: item.version,
          action_hash: item.action_hash,
          outcome,
          reason: reason.trim(),
        }),
      replace,
    )
  }
  return (
    <article
      className="panel"
      aria-label={`Advisor review for ${item.title}`}
      aria-busy={save.busy}
    >
      <h2 className="record-note">{item.title}</h2>
      <p>
        Confirmed crop stage · {item.evidence.confirmed_stage ?? 'Not recorded'}
      </p>
      {item.prior_proposed_date && (
        <p>Previous suggestion · {item.prior_proposed_date}</p>
      )}
      <TaskDateComparison plan={item} timezone="UTC" />
      {item.review ? (
        <>
          <p role="status">{recorded[item.review.outcome]}</p>
          <p className="record-note">{item.review.reason}</p>
        </>
      ) : item.can_review ? (
        <>
          <TextArea
            label="Review reason"
            value={reason}
            change={setReason}
            maxLength={500}
            required
            disabled={save.busy || save.blocked}
          />
          <div className="record-toolbar">
            {(Object.keys(outcomes) as AdvisorOutcome[]).map((outcome) => (
              <button
                type="button"
                key={outcome}
                disabled={!reason.trim() || save.busy || save.blocked}
                onClick={() => decide(outcome)}
              >
                {outcomes[outcome]}
              </button>
            ))}
          </div>
          {save.error && <Notice message={save.error} />}
          {save.blocked && (
            <button
              type="button"
              onClick={() => {
                save.reset()
                reload()
              }}
            >
              Reload assigned cases
            </button>
          )}
        </>
      ) : (
        <p role="status">
          This suggestion is no longer current. A fresh suggestion needs a new
          referral.
        </p>
      )}
    </article>
  )
}

export default function AdvisorCasesPage() {
  const [page, setPage] = useState(1)
  const record = useRecord<Page<AdvisorCase>>(`/advisor/cases?page=${page}`)
  const cases = record.data
  return (
    <div className="farm-records">
      <div className="page-intro">
        <h1>Assigned plan reviews</h1>
        <p>
          Review the submitted comparison and explain your decision. The farmer
          decides whether to move the task.
        </p>
      </div>
      {!cases ? (
        <ReadState
          loading={record.loading}
          error={record.error}
          retry={record.reload}
          review
          advisor
        />
      ) : (
        <>
          {!cases.items.length && (
            <p role="status">No current reviews are assigned to you.</p>
          )}
          <button type="button" onClick={record.reload}>
            Refresh reviews
          </button>
          {cases.items.map((item) => (
            <AssignedReview
              key={item.id}
              item={item}
              reload={record.reload}
              replace={(review) =>
                record.replace({
                  ...cases,
                  items: cases.items.map((row) =>
                    row.id === item.id ? { ...row, review } : row,
                  ),
                })
              }
            />
          ))}
          <Pagination result={cases} page={page} change={setPage} />
        </>
      )}
    </div>
  )
}
