import { useEffect, useRef, useState } from 'react'
import Notice from '../../components/Notice'
import type { PlannerWeek, PlanOutcome, WeekTask } from '../../lib/farms'
import { Pagination, ReadState } from './RecordUI'
import WeeklySuggestion from './WeeklySuggestion'
import WeeklyBatch from './WeeklyBatch'
import { useRecord } from './record-hooks'

function dates(start: string) {
  const day = new Date(`${start}T00:00:00Z`)
  return Array.from({ length: 7 }, () => {
    const value = day.toISOString().slice(0, 10)
    day.setUTCDate(day.getUTCDate() + 1)
    return value
  })
}

export default function WeeklyPlanner({
  path,
  tasksPath,
  planPath,
  timezone,
  revision,
  archived,
  blocked,
  openTask,
  changed,
}: {
  path: string
  tasksPath: string
  planPath: string
  timezone: string
  revision: string
  archived: boolean
  blocked: boolean
  openTask: (id: string) => void
  changed: () => void
}) {
  const [page, setPage] = useState(1)
  const [suggestion, setSuggestion] = useState<WeekTask | null>(null)
  const [showBatch, setShowBatch] = useState(false)
  const reviewPanel = useRef<HTMLDivElement>(null)
  const [notice, setNotice] = useState('')
  const record = useRecord<PlannerWeek>(`${path}?page=${page}`)
  const { reload } = record
  const lastRevision = useRef(revision)
  useEffect(() => {
    if (revision !== lastRevision.current) {
      lastRevision.current = revision
      reload()
    }
  }, [revision, reload])
  useEffect(() => {
    if (suggestion) reviewPanel.current?.focus()
  }, [suggestion])

  const week = record.data
  const selectedTask =
    week?.items.find((task) => task.id === suggestion?.id) ?? suggestion
  function decided(outcome: PlanOutcome) {
    setSuggestion(null)
    setNotice(outcome === 'accepted' ? 'Task date updated.' : 'Task date kept.')
    changed()
  }
  function taskRow(task: WeekTask) {
    return (
      <li key={task.id}>
        <strong className="record-note">{task.title}</strong>
        <p className="muted">
          <time dateTime={task.due_date}>{task.due_date}</time> · {task.status}
          {task.rain_alert && ` · Rain alert (${task.precipitation_mm} mm)`}
        </p>
        <div className="button-row">
          <button
            type="button"
            aria-label={`Open task ${task.title}`}
            disabled={blocked || Boolean(suggestion)}
            onClick={() => openTask(task.id)}
          >
            Open task
          </button>
          {!archived &&
            task.status === 'pending' &&
            week &&
            task.due_date >= week.starts_on && (
              <button
                type="button"
                disabled={blocked || Boolean(suggestion)}
                onClick={() => {
                  setNotice('')
                  setSuggestion(task)
                }}
              >
                Review suggestion
              </button>
            )}
        </div>
      </li>
    )
  }
  return (
    <section className="panel record-inset" aria-labelledby="week-heading">
      <h3 id="week-heading">Seven-day planner</h3>
      {notice && <Notice success message={notice} />}
      {!archived && !selectedTask && (
        <button
          type="button"
          aria-expanded={showBatch}
          disabled={blocked}
          onClick={() => setShowBatch(!showBatch)}
        >
          {showBatch ? 'Hide weekly changes' : 'Review weekly changes'}
        </button>
      )}
      {!archived && showBatch && !selectedTask && (
        <WeeklyBatch
          path={planPath + '/weekly-batch'}
          timezone={timezone}
          changed={changed}
        />
      )}
      {!archived && selectedTask && (
        <div ref={reviewPanel} tabIndex={-1}>
          <WeeklySuggestion
            task={selectedTask}
            taskPath={tasksPath}
            planPath={planPath}
            timezone={timezone}
            close={() => setSuggestion(null)}
            changed={decided}
          />
        </div>
      )}
      {!week ? (
        <ReadState
          loading={record.loading}
          error={record.error}
          retry={reload}
        />
      ) : (
        <>
          <p className="muted">
            {week.starts_on} to {week.ends_on} · {timezone}
          </p>
          {week.items.some((task) => task.due_date < week.starts_on) && (
            <section aria-label="Overdue tasks">
              <h4>Overdue tasks</h4>
              <ul className="planner-tasks">
                {week.items
                  .filter((task) => task.due_date < week.starts_on)
                  .map(taskRow)}
              </ul>
            </section>
          )}
          <div className="planner-week">
            {dates(week.starts_on).map((day) => {
              const entries = week.items.filter((task) => task.due_date === day)
              return (
                <section
                  className="planner-day"
                  key={day}
                  aria-label={`Tasks for ${day}`}
                >
                  <h4>
                    <time dateTime={day}>{day}</time>
                  </h4>
                  {entries.length > 0 && (
                    <ul className="planner-tasks">{entries.map(taskRow)}</ul>
                  )}
                </section>
              )
            })}
          </div>
          {week.total === 0 && <p>No overdue or scheduled tasks this week.</p>}
          {!suggestion && (
            <Pagination result={week} page={page} change={setPage} />
          )}
        </>
      )}
    </section>
  )
}
