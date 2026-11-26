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

const dayFormat = new Intl.DateTimeFormat('en-GB', {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  timeZone: 'UTC',
})
function dayLabel(date: string) {
  return dayFormat.format(new Date(`${date}T00:00:00Z`))
}

export default function WeeklyPlanner({
  path,
  tasksPath,
  planPath,
  timezone,
  revision,
  archived,
  blocked,
  complete,
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
  complete: (task: WeekTask) => void
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
  const today =
    week?.items.filter((task) => task.due_date === week.starts_on) ?? []
  const overdue =
    week?.items.filter((task) => task.due_date < week.starts_on) ?? []
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
          <time dateTime={task.due_date}>{dayLabel(task.due_date)}</time> ·{' '}
          {task.status}
        </p>
        {task.rain_alert && (
          <p className="planner-rain">
            Rain alert ({task.precipitation_mm} mm)
          </p>
        )}
        <div className="button-row">
          {!archived && task.status === 'pending' && (
            <button
              disabled={blocked || Boolean(suggestion)}
              onClick={() => complete(task)}
            >
              Mark done
            </button>
          )}
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
      <h3 id="week-heading" tabIndex={-1}>
        Seven-day planner
      </h3>
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
          planPath={planPath}
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
            {dayLabel(week.starts_on)} to {dayLabel(week.ends_on)} · {timezone}
          </p>
          <section
            className="planner-day"
            aria-label={`Tasks for ${week.starts_on}`}
          >
            <h4>Today’s tasks</h4>
            {today.length > 0 ? (
              <ul className="planner-tasks">{today.map(taskRow)}</ul>
            ) : (
              <p>
                {week.total > week.page_size
                  ? 'No tasks for today on this page.'
                  : 'No tasks for today.'}
              </p>
            )}
          </section>
          {overdue.length > 0 && (
            <section
              className="planner-day planner-overdue"
              aria-label="Overdue tasks"
            >
              <h4>Overdue tasks</h4>
              <ul className="planner-tasks">{overdue.map(taskRow)}</ul>
            </section>
          )}
          {week.items.some((task) => task.due_date > week.starts_on) && (
            <h4>Coming up</h4>
          )}
          <div className="planner-week">
            {dates(week.starts_on)
              .slice(1)
              .map((day) => {
                const entries = week.items.filter(
                  (task) => task.due_date === day,
                )
                if (!entries.length) return null
                return (
                  <section
                    className="planner-day"
                    key={day}
                    aria-label={`Tasks for ${day}`}
                  >
                    <h4>
                      <time dateTime={day}>{dayLabel(day)}</time>
                    </h4>
                    {entries.length > 0 && (
                      <ul className="planner-tasks">{entries.map(taskRow)}</ul>
                    )}
                  </section>
                )
              })}
          </div>
          {week.total === 0 && <p>No overdue or scheduled tasks this week.</p>}
          {!suggestion && week.total > week.page_size && (
            <Pagination result={week} page={page} change={setPage} />
          )}
        </>
      )}
    </section>
  )
}
