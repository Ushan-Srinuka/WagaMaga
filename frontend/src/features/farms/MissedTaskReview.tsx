import { useState } from 'react'
import Field from '../../components/Field'
import Notice from '../../components/Notice'
import type {
  FarmTask,
  FarmWeather,
  PlanOutcome,
  ReschedulePlan,
  TaskPlanDecision,
} from '../../lib/farms'
import { farmWrite } from '../../lib/farms'
import { TextArea } from './RecordUI'
import TaskDateComparison from './TaskDateComparison'
import { useSave } from './record-hooks'

export default function MissedTaskReview({
  task,
  farmToday,
  taskPath,
  planPath,
  timezone,
  weather,
  close,
  finished,
  reload,
}: {
  task: FarmTask
  farmToday: string
  taskPath: string
  planPath: string
  timezone: string
  weather?: FarmWeather
  close: () => void
  finished: (outcome: PlanOutcome) => void
  reload: () => void
}) {
  const [date, setDate] = useState('')
  const [reason, setReason] = useState('')
  const [plan, setPlan] = useState<ReschedulePlan | null>(null)
  const save = useSave()
  const end = new Date(`${farmToday}T00:00:00Z`)
  end.setUTCDate(end.getUTCDate() + 7)
  const latestDate = end.toISOString().slice(0, 10)
  const forecastDay =
    weather?.status === 'fresh'
      ? weather.forecast?.days.find((day) => day.date === date)
      : undefined
  function decide(outcome: PlanOutcome) {
    if (!plan) return
    void save.run(
      () =>
        farmWrite<TaskPlanDecision>(
          `${planPath}/missed-reviews/${plan.id}/decision`,
          'POST',
          {
            expected_version: plan.version,
            action_hash: plan.action_hash,
            outcome,
          },
          { 'Idempotency-Key': plan.id },
        ),
      (decision) => finished(decision.outcome),
    )
  }
  return (
    <section className="record-inset" aria-label="Review missed task">
      <h4>Review missed task</h4>
      {save.error && <Notice message={save.error} />}
      {plan ? (
        <TaskDateComparison
          plan={plan}
          timezone={timezone}
          disabled={save.busy || save.blocked}
          decide={decide}
        />
      ) : (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (!date || date < farmToday || date > latestDate) return
            void save.run(
              () =>
                farmWrite<ReschedulePlan>(
                  `${taskPath}/${task.id}/missed-review`,
                  'POST',
                  {
                    expected_version: task.version,
                    proposed_due_date: date,
                    reason: reason.trim() || null,
                  },
                ),
              setPlan,
            )
          }}
        >
          <p>Current date · {task.due_date}</p>
          <Field
            label="Proposed date"
            type="date"
            min={farmToday}
            max={latestDate}
            required
            hint="Choose a date from today through the next seven days."
            value={date}
            disabled={save.busy || save.blocked}
            onChange={(event) => setDate(event.target.value)}
          />
          {date && (
            <p className="muted">
              {forecastDay
                ? `Open-Meteo forecasts ${forecastDay.precipitation_mm} mm of rain on ${date}.`
                : 'No current forecast is available for this date.'}
            </p>
          )}
          <TextArea
            label="Why was it missed? (optional)"
            value={reason}
            change={setReason}
            maxLength={240}
            disabled={save.busy || save.blocked}
          />
          <div className="record-toolbar">
            <button
              className="primary"
              disabled={
                !date ||
                date < farmToday ||
                date > latestDate ||
                save.busy ||
                save.blocked
              }
            >
              Review new date
            </button>
            <button type="button" disabled={save.busy} onClick={close}>
              Cancel review
            </button>
          </div>
        </form>
      )}
      {save.blocked && (
        <button type="button" onClick={reload}>
          Reload task and forecast
        </button>
      )}
    </section>
  )
}
