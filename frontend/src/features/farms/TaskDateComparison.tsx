import type { PlanOutcome, ReschedulePlan } from '../../lib/farms'
import { timestamp } from '../../lib/farms'

export default function TaskDateComparison({
  plan,
  timezone,
  disabled,
  decide,
  allowConfirm = true,
}: {
  plan: ReschedulePlan
  timezone: string
  disabled?: boolean
  decide?: (outcome: PlanOutcome) => void
  allowConfirm?: boolean
}) {
  return (
    <>
      <dl className="record-form-grid">
        <div>
          <dt>Current date</dt>
          <dd>{plan.current_due_date}</dd>
        </div>
        <div>
          <dt>Proposed date</dt>
          <dd>{plan.proposed_due_date}</dd>
        </div>
      </dl>
      <p className="record-note">{plan.evidence_text}</p>
      {plan.forecast_fetched_at && (
        <p className="muted">
          Forecast fetched {timestamp(plan.forecast_fetched_at, timezone)} ·{' '}
          {timezone}
        </p>
      )}
      {decide && (
        <div className="record-toolbar">
          <button
            type="button"
            className="primary"
            disabled={disabled || !allowConfirm}
            onClick={() => decide('accepted')}
          >
            Confirm new date
          </button>
          <button
            type="button"
            disabled={disabled}
            onClick={() => decide('rejected')}
          >
            Keep current date
          </button>
        </div>
      )}
    </>
  )
}
