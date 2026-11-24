import { useEffect, useRef, useState, type FormEvent } from 'react'
import Field from '../../components/Field'
import Notice from '../../components/Notice'
import type {
  PlanOutcome,
  ReschedulePlan,
  TaskPlanDecision,
  WeatherAlert,
  WeatherAlertPage,
  WeatherAlertRule,
} from '../../lib/farms'
import { farmWrite } from '../../lib/farms'
import { Pagination } from './RecordUI'
import TaskDateComparison from './TaskDateComparison'
import { useRecord, useSave } from './record-hooks'

type Review = {
  alert: WeatherAlert
  selectedDate: string
  plan?: ReschedulePlan
}

export default function WeatherAlerts({
  path,
  timezone,
  revision,
  onRescheduled,
  onRuleChanged,
}: {
  path: string
  timezone: string
  revision: string
  onRescheduled: () => void
  onRuleChanged: () => void
}) {
  const [page, setPage] = useState(1)
  const record = useRecord<WeatherAlertPage>(`${path}?page=${page}`)
  const { data, reload } = record
  const [thresholdDraft, setThresholdDraft] = useState<string | null>(null)
  const [review, setReview] = useState<Review | null>(null)
  const [message, setMessage] = useState('')
  const save = useSave((error) =>
    error instanceof Error ? error.message : 'Could not save the change.',
  )
  const lastRevision = useRef(revision)
  useEffect(() => {
    if (lastRevision.current !== revision) {
      lastRevision.current = revision
      reload()
    }
  }, [reload, revision])

  const threshold = thresholdDraft ?? String(data?.rule.threshold_mm ?? '')
  const thresholdMm = Number(threshold)
  const validThreshold =
    Number.isInteger(thresholdMm) && thresholdMm >= 1 && thresholdMm <= 1000
  const canChange = data?.can_edit && !save.busy && !save.blocked
  const prepared = review?.plan

  function saveRule(value: number | null) {
    if (!data || !canChange) return
    setMessage('')
    void save.run(
      () =>
        farmWrite<WeatherAlertRule>(path + '/rule', 'PATCH', {
          threshold_mm: value,
          expected_version: data.rule.version,
        }),
      () => {
        setThresholdDraft(null)
        setPage(1)
        setMessage(
          value === null
            ? 'Weather alerts turned off.'
            : 'Weather alert threshold saved.',
        )
        onRuleChanged()
      },
    )
  }

  function prepare(event: FormEvent) {
    event.preventDefault()
    if (!review || !canChange || !review.selectedDate) return
    const { alert, selectedDate } = review
    setMessage('')
    void save.run(
      () =>
        farmWrite<ReschedulePlan>(
          `${path}/tasks/${alert.task_id}/reschedule`,
          'POST',
          {
            expected_version: alert.task_version,
            expected_rule_version: alert.rule_version,
            expected_forecast_fetched_at: alert.forecast_fetched_at,
            proposed_due_date: selectedDate,
          },
        ),
      (plan) => setReview({ alert, selectedDate, plan }),
    )
  }

  function decide(plan: ReschedulePlan, outcome: PlanOutcome) {
    if (!canChange) return
    void save.run(
      () =>
        farmWrite<TaskPlanDecision>(
          `${path}/reschedules/${plan.id}/decision`,
          'POST',
          {
            expected_version: plan.version,
            action_hash: plan.action_hash,
            outcome,
          },
          { 'Idempotency-Key': plan.id },
        ),
      (decision) => {
        setReview(null)
        setMessage(
          decision.outcome === 'accepted'
            ? 'Task date updated.'
            : 'Task date kept.',
        )
        if (decision.outcome === 'accepted') onRescheduled()
        else reload()
      },
    )
  }

  return (
    <section
      className="panel record-inset"
      aria-labelledby="weather-alert-heading"
    >
      <h3 id="weather-alert-heading">Weather alerts</h3>
      {record.loading && <p role="status">Loading weather alerts…</p>}
      {record.error !== undefined && (
        <>
          <Notice message="Weather alerts could not be loaded." />
          <button type="button" onClick={reload}>
            Retry alerts
          </button>
        </>
      )}
      {message && <Notice success message={message} />}
      {save.error && <Notice message={save.error} />}
      {save.blocked && (
        <button
          type="button"
          onClick={() => {
            setReview(null)
            setThresholdDraft(null)
            save.reset()
            reload()
          }}
        >
          Reload weather alerts
        </button>
      )}
      {data && (
        <>
          {data.can_edit ? (
            <form
              onSubmit={(event) => {
                event.preventDefault()
                if (validThreshold) saveRule(thresholdMm)
              }}
            >
              <Field
                label="Rain alert threshold (mm)"
                type="number"
                min={1}
                max={1000}
                step={1}
                hint="Flag tasks when the forecast precipitation meets this amount."
                value={threshold}
                disabled={!canChange || Boolean(review)}
                onChange={(event) => setThresholdDraft(event.target.value)}
              />
              <div className="record-toolbar">
                <button
                  disabled={!canChange || Boolean(review) || !validThreshold}
                >
                  Save threshold
                </button>
                {data.rule.threshold_mm !== null && (
                  <button
                    type="button"
                    disabled={!canChange || Boolean(review)}
                    onClick={() => saveRule(null)}
                  >
                    Turn off weather alerts
                  </button>
                )}
              </div>
            </form>
          ) : (
            <p>Weather alerts are read only for archived cultivations.</p>
          )}
          {data.can_edit &&
            data.rule.threshold_mm !== null &&
            data.total === 0 && (
              <p>
                {data.forecast_fresh
                  ? 'No pending tasks match the current forecast and threshold.'
                  : 'Fetch a current forecast to check for weather alerts.'}
              </p>
            )}
          {data.items.map((alert) => (
            <article
              className="panel"
              key={`${alert.task_id}:${alert.due_date}`}
            >
              <h4 className="record-note">{alert.title}</h4>
              <p>
                Due {alert.due_date} · {alert.precipitation_mm} mm forecast ·{' '}
                {alert.threshold_mm} mm threshold
              </p>
              <button
                type="button"
                disabled={!canChange || Boolean(review)}
                onClick={() => {
                  setReview({ alert, selectedDate: '' })
                  setMessage('')
                }}
              >
                Review task date
              </button>
            </article>
          ))}
          {(page > 1 || data.total > data.page_size) && !review && (
            <Pagination result={data} page={page} change={setPage} />
          )}
        </>
      )}
      {review && (
        <section className="panel" aria-label="Review task date change">
          <h4 className="record-note">{review.alert.title}</h4>
          {prepared ? (
            <TaskDateComparison
              plan={prepared}
              timezone={timezone}
              disabled={!canChange}
              decide={(outcome) => decide(prepared, outcome)}
            />
          ) : (
            <form onSubmit={prepare}>
              <p>Current date · {review.alert.due_date}</p>
              <Field
                label="Proposed date"
                type="date"
                required
                value={review.selectedDate}
                hint="Choose a different date within the next seven days."
                disabled={!canChange}
                onChange={(event) =>
                  setReview({ ...review, selectedDate: event.target.value })
                }
              />
              <div className="record-toolbar">
                <button
                  className="primary"
                  disabled={
                    !canChange ||
                    !review.selectedDate ||
                    review.selectedDate === review.alert.due_date
                  }
                >
                  Review new date
                </button>
                <button
                  type="button"
                  disabled={save.busy}
                  onClick={() => setReview(null)}
                >
                  Cancel review
                </button>
              </div>
            </form>
          )}
        </section>
      )}
    </section>
  )
}
