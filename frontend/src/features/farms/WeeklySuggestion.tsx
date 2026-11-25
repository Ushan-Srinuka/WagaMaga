import { useState } from 'react'
import Field from '../../components/Field'
import Notice from '../../components/Notice'
import { Link } from 'react-router'
import {
  farmWrite,
  weeklyPlanStatus,
  type PlanOutcome,
  type TaskPlanDecision,
  type WeeklyPlan,
  type WeekTask,
} from '../../lib/farms'
import TaskDateComparison from './TaskDateComparison'
import { useRecord, useSave } from './record-hooks'
import { ReadState } from './RecordUI'

export default function WeeklySuggestion({
  task,
  taskPath,
  planPath,
  timezone,
  changed,
  close,
  sourcePath,
  onRevised,
}: {
  task: WeekTask
  taskPath: string
  planPath: string
  timezone: string
  changed: (outcome: PlanOutcome) => void
  close?: () => void
  sourcePath?: string
  onRevised?: (id: string) => void
}) {
  const path = `${taskPath}/${task.id}/weekly-suggestion`
  const record = useRecord<{ plan: WeeklyPlan | null }>(sourcePath ?? path)
  const save = useSave()
  const [assigning, setAssigning] = useState(false)
  const [email, setEmail] = useState('')
  const [revising, setRevising] = useState(false)
  const [revisedDate, setRevisedDate] = useState('')
  const plan = record.data?.plan
  const canDecide =
    plan && !['stale', 'accepted', 'rejected'].includes(plan.state)
  const canGenerate =
    !sourcePath &&
    record.data &&
    !plan?.can_revise &&
    (!plan ||
      [
        'stale',
        'revoked',
        'declined',
        'changes_requested',
        'rejected',
      ].includes(plan.state))
  const binding = plan
    ? { expected_version: plan.version, action_hash: plan.action_hash }
    : null
  const reviewPath = `${planPath}/weekly/${plan?.id}`
  const disabled = save.busy || save.blocked
  const setPlan = (next: WeeklyPlan) => record.replace({ plan: next })

  function decide(outcome: PlanOutcome) {
    if (!plan || !binding) return
    void save.run(
      () =>
        farmWrite<TaskPlanDecision>(
          reviewPath + '/decision',
          'POST',
          {
            ...binding,
            outcome,
          },
          { 'Idempotency-Key': plan.id },
        ),
      (decision) => changed(decision.outcome),
    )
  }

  return (
    <section
      className="panel record-inset"
      aria-label="Weekly date suggestion"
      aria-busy={save.busy}
    >
      <h4>{task.title}</h4>
      {record.loading && <p role="status">Loading suggestion…</p>}
      {record.error !== undefined && (
        <ReadState
          loading={false}
          error={record.error}
          retry={record.reload}
          review
        />
      )}
      {save.error && <Notice message={save.error} />}
      {plan && (
        <>
          <p role="status">{weeklyPlanStatus[plan.state]}</p>
          {plan.state === 'stale' && (
            <p>
              Refresh the planner and review a new suggestion before changing
              this task.
            </p>
          )}
          {plan.revises_plan_id && (
            <p>
              Previous suggestion ·{' '}
              <Link to={`/plan-reviews/${plan.revises_plan_id}`}>
                {plan.prior_proposed_date}
              </Link>
            </p>
          )}
          <p>
            Confirmed crop stage ·{' '}
            {plan.evidence.confirmed_stage ?? 'Not recorded'}
          </p>
          <TaskDateComparison
            plan={plan}
            timezone={timezone}
            disabled={disabled || assigning || revising}
            allowConfirm={plan.state === 'ready' || plan.state === 'cleared'}
            decide={canDecide ? decide : undefined}
          />
          {plan.advisor_reason && (
            <p className="record-note">
              Advisor reason · {plan.advisor_reason}
            </p>
          )}
          {plan.can_revise && !revising && (
            <button
              type="button"
              disabled={disabled}
              onClick={() => setRevising(true)}
            >
              Revise suggested date
            </button>
          )}
          {(plan.state === 'ready' || plan.state === 'advisor_required') &&
            !assigning && (
              <button
                type="button"
                disabled={disabled}
                onClick={() => setAssigning(true)}
              >
                Ask an advisor
              </button>
            )}
          {plan.advisor_assigned && (
            <button
              type="button"
              disabled={disabled}
              onClick={() =>
                void save.run(
                  () =>
                    farmWrite<WeeklyPlan>(
                      reviewPath + '/advisor/revoke',
                      'POST',
                      binding,
                    ),
                  setPlan,
                )
              }
            >
              Revoke advisor access
            </button>
          )}
        </>
      )}
      {revising && plan && binding && (
        <form
          className="record-form"
          onSubmit={(event) => {
            event.preventDefault()
            if (!revisedDate || revisedDate === plan.proposed_due_date) return
            void save.run(
              () =>
                farmWrite<WeeklyPlan>(reviewPath + '/revise', 'POST', {
                  ...binding,
                  proposed_due_date: revisedDate,
                }),
              (next) => {
                setRevising(false)
                setRevisedDate('')
                setPlan(next)
                onRevised?.(next.id)
              },
            )
          }}
        >
          <Field
            label="Revised date"
            type="date"
            autoFocus
            value={revisedDate}
            required
            disabled={disabled}
            hint="Choose a different later date this week with rainfall below your threshold."
            onChange={(event) => setRevisedDate(event.target.value)}
          />
          <div className="record-toolbar">
            <button
              type="submit"
              className="primary"
              disabled={
                disabled ||
                !revisedDate ||
                revisedDate === plan.proposed_due_date
              }
            >
              Send revised suggestion
            </button>
            <button
              type="button"
              disabled={save.busy}
              onClick={() => setRevising(false)}
            >
              Cancel revision
            </button>
          </div>
        </form>
      )}
      {assigning && binding && (
        <form
          className="record-form"
          onSubmit={(event) => {
            event.preventDefault()
            void save.run(
              () =>
                farmWrite<WeeklyPlan>(reviewPath + '/advisor', 'POST', {
                  ...binding,
                  advisor_email: email.trim(),
                }),
              (next) => {
                setPlan(next)
                setAssigning(false)
                setEmail('')
              },
            )
          }}
        >
          <p>
            Share this task’s title, dates, confirmed stage and forecast figures
            with the assigned advisor.
          </p>
          <Field
            label="Advisor account email"
            type="email"
            autoFocus
            value={email}
            required
            maxLength={254}
            disabled={disabled}
            onChange={(event) => setEmail(event.target.value)}
          />
          <div className="record-toolbar">
            <button
              type="submit"
              className="primary"
              disabled={disabled || !email.trim()}
            >
              Send for review
            </button>
            <button
              type="button"
              disabled={save.busy}
              onClick={() => setAssigning(false)}
            >
              Cancel sharing
            </button>
          </div>
        </form>
      )}
      {!plan && record.data && !task.rain_alert && (
        <p>A current rainfall alert is needed to suggest another date.</p>
      )}
      {!plan && record.data && task.rain_alert && (
        <p>No date suggestion has been saved for this task yet.</p>
      )}
      <div className="record-toolbar">
        {canGenerate && task.rain_alert && (
          <button
            type="button"
            className="primary"
            disabled={disabled}
            onClick={() =>
              void save.run(
                () =>
                  farmWrite<WeeklyPlan>(path, 'POST', {
                    expected_version: task.version,
                  }),
                setPlan,
              )
            }
          >
            Suggest a date
          </button>
        )}
        {record.error === undefined && (
          <button
            type="button"
            disabled={save.busy}
            onClick={() => {
              save.reset()
              record.reload()
            }}
          >
            Refresh suggestion
          </button>
        )}
        {close && (
          <button type="button" disabled={save.busy} onClick={close}>
            Close suggestion
          </button>
        )}
      </div>
    </section>
  )
}
