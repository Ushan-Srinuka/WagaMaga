import { useState } from 'react'
import Notice from '../../components/Notice'
import type {
  Page,
  PlanOutcome,
  TaskPlan,
  TaskPlanDecision,
  TaskPlanHistory,
} from '../../lib/farms'
import { farmWrite, timestamp } from '../../lib/farms'
import { Pagination, ReadState } from './RecordUI'
import { useRecord, useSave } from './record-hooks'

const outcomes = { accepted: 'Accepted · Task added', rejected: 'Rejected' }

export default function SuggestedPlans({
  path,
  timezone,
  archived,
  blockedByTaskEdit,
  onAccepted,
  review,
}: {
  path: string
  timezone: string
  archived: boolean
  blockedByTaskEdit: boolean
  onAccepted: () => void
  review: () => void
}) {
  const latest = useRecord<{ plan: TaskPlan | null }>(path)
  const save = useSave()
  const plan = latest.data?.plan
  const canDecide =
    !archived && !blockedByTaskEdit && !save.busy && !save.blocked

  function decide(current: TaskPlan, outcome: PlanOutcome) {
    void save.run(
      () =>
        farmWrite<TaskPlanDecision>(
          `${path}/${current.id}/decision`,
          'POST',
          {
            expected_version: current.version,
            action_hash: current.action_hash,
            outcome,
          },
          { 'Idempotency-Key': current.id },
        ),
      (decision) => {
        latest.replace({
          plan: { ...current, state: decision.outcome, decision },
        })
        if (decision.outcome === 'accepted') onAccepted()
      },
    )
  }

  return (
    <section
      className="panel record-inset"
      aria-labelledby="suggested-plans-heading"
    >
      <h3 id="suggested-plans-heading">Suggested plans</h3>
      <p className="muted">Portfolio example · Sample recordkeeping task</p>
      {save.error && <Notice message={save.error} />}
      {save.blocked && (
        <button type="button" onClick={review}>
          Reload cultivation and review
        </button>
      )}
      {!latest.data ? (
        <ReadState
          loading={latest.loading}
          error={latest.error}
          retry={latest.reload}
        />
      ) : (
        <>
          {plan && (
            <div>
              <h4>{plan.title}</h4>
              <p>
                Proposed addition · Due{' '}
                <time dateTime={plan.due_date}>{plan.due_date}</time>
              </p>
              <p>{plan.evidence_text}</p>
              {plan.decision ? (
                <Notice success message={outcomes[plan.decision.outcome]} />
              ) : plan.state === 'expired' || plan.state === 'stale' ? (
                <p role="status">
                  {plan.state === 'expired'
                    ? 'This example expired.'
                    : 'The cultivation records changed.'}
                </p>
              ) : (
                <p className="muted">
                  Review by {timestamp(plan.expires_at, timezone)} · {timezone}
                </p>
              )}
            </div>
          )}
          {!archived && plan?.state !== 'accepted' && (
            <div className="record-toolbar">
              {plan?.state === 'pending' ? (
                <>
                  <button
                    className="primary"
                    disabled={!canDecide}
                    onClick={() => decide(plan, 'accepted')}
                  >
                    Accept and add task
                  </button>
                  <button
                    disabled={!canDecide}
                    onClick={() => decide(plan, 'rejected')}
                  >
                    Reject suggestion
                  </button>
                </>
              ) : (
                <button
                  disabled={!canDecide}
                  onClick={() =>
                    void save.run(
                      () => farmWrite<TaskPlan>(path, 'POST', {}),
                      (created) => latest.replace({ plan: created }),
                    )
                  }
                >
                  {save.busy ? 'Saving…' : 'Review example plan'}
                </button>
              )}
            </div>
          )}
          {archived && !plan && <p>No plan was saved.</p>}
        </>
      )}
    </section>
  )
}

export function PlanHistory({
  path,
  timezone,
}: {
  path: string
  timezone: string
}) {
  const [page, setPage] = useState(1)
  const history = useRecord<Page<TaskPlanHistory>>(
    `${path}/history?page=${page}`,
  )
  return (
    <section className="panel" aria-labelledby="plan-history-heading">
      <h2 id="plan-history-heading">Plan decisions</h2>
      {!history.data ? (
        <ReadState
          loading={history.loading}
          error={history.error}
          retry={history.reload}
        />
      ) : (
        <>
          {history.data.items.length === 0 && <p>No plan decisions yet.</p>}
          {history.data.items.map((decision) => (
            <article className="panel" key={decision.plan_id}>
              <h3>{decision.title}</h3>
              <p>
                {decision.action_type === 'reschedule_task'
                  ? `${decision.outcome === 'accepted' ? 'Accepted' : 'Rejected'} · ${decision.previous_due_date} → ${decision.due_date}`
                  : `${outcomes[decision.outcome]} · Due ${decision.due_date}`}
              </p>
              <p>{decision.evidence_text}</p>
              <p className="muted">
                {timestamp(decision.decided_at, timezone)} · {timezone}
              </p>
            </article>
          ))}
          {history.data.total > history.data.page_size && (
            <Pagination result={history.data} page={page} change={setPage} />
          )}
        </>
      )}
    </section>
  )
}
