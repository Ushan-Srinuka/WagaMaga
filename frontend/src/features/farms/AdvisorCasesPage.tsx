import { useState } from 'react'
import { Link } from 'react-router'
import {
  ReviewFilter,
  ReviewTime,
  type ReviewView,
} from '../advisor/ReviewControls'
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
  const [outcome, setOutcome] = useState<AdvisorOutcome | ''>('')
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
        Assigned <ReviewTime value={item.assigned_at} />
      </p>
      <p>
        Expires <ReviewTime value={item.expires_at} />
      </p>
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
          <p>
            Submitted <ReviewTime value={item.review.decided_at} />
          </p>
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
          <label className="field">
            Review outcome
            <select
              value={outcome}
              disabled={save.busy || save.blocked}
              onChange={(event) =>
                setOutcome(event.target.value as AdvisorOutcome | '')
              }
            >
              <option value="">Choose an outcome</option>
              {Object.entries(outcomes).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            disabled={!outcome || !reason.trim() || save.busy || save.blocked}
            onClick={() => {
              if (outcome) decide(outcome)
            }}
          >
            Submit decision
          </button>
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
  const [view, setView] = useState<ReviewView>('pending')
  return (
    <div className="farm-records">
      <div className="page-intro">
        <h1>Assigned plan reviews</h1>
        <p>
          Review the shared evidence. The farmer decides whether to move the
          task.
        </p>
      </div>
      <ReviewFilter view={view} change={setView} />
      <AdvisorCaseList key={view} view={view} />
    </div>
  )
}

export function AdvisorCaseList({
  view,
  summary = false,
}: {
  view: ReviewView
  summary?: boolean
}) {
  const [page, setPage] = useState(1)
  const record = useRecord<Page<AdvisorCase>>(
    `/advisor/cases?page=${page}&view=${view}`,
  )
  const cases = record.data
  return (
    <>
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
            <p role="status">
              {view === 'pending'
                ? 'No current reviews are assigned to you.'
                : 'No reviewed plans are currently available.'}
            </p>
          )}
          {cases.items.map((item) => (
            <article className="panel" key={item.id}>
              <h3>
                <Link to={`/plan-reviews/${item.id}`}>{item.title}</Link>
              </h3>
              <p>
                Assigned <ReviewTime value={item.assigned_at} /> · Expires{' '}
                <ReviewTime value={item.expires_at} />
              </p>
              {item.review && <p>{recorded[item.review.outcome]}</p>}
            </article>
          ))}
          {!summary && (
            <Pagination result={cases} page={page} change={setPage} />
          )}
        </>
      )}
    </>
  )
}
