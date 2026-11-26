import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import Field from '../../components/Field'
import Notice from '../../components/Notice'
import type {
  DemoForecast,
  FarmTask,
  FarmTaskEvent,
  FarmWeather,
  Page,
  TaskPage,
  TaskStatus,
} from '../../lib/farms'
import { farmWrite, timestamp } from '../../lib/farms'
import DemoWeather from './DemoWeather'
import LiveWeather from './LiveWeather'
import MissedTaskReview from './MissedTaskReview'
import PlannerChat from './PlannerChat'
import { Pagination, ReadState, SaveError } from './RecordUI'
import { useRecord, useSave } from './record-hooks'
import SuggestedPlans from './SuggestedPlans'
import WeatherAlerts from './WeatherAlerts'
import WeeklyPlanner from './WeeklyPlanner'

const statuses = {
  pending: 'Pending',
  completed: 'Completed',
  cancelled: 'Cancelled',
  all: 'All tasks',
}
const actions = {
  created: 'Added',
  edited: 'Edited',
  completed: 'Completed',
  cancelled: 'Cancelled',
}
type Draft = {
  title: string
  due_date: string
  task?: FarmTask
  weatherReview?: boolean
}

export default function TaskPanel({
  path,
  planPath,
  cultivationPath,
  farmPath,
  timezone,
  archived,
  chilli,
  review,
}: {
  path: string
  planPath: string
  cultivationPath: string
  farmPath: string
  timezone: string
  archived: boolean
  chilli?: boolean
  review: () => void
}) {
  const filterId = useId()
  const addTask = useRef<HTMLButtonElement>(null)
  const taskForm = useRef<HTMLFormElement>(null)
  const taskTitle = useRef<HTMLInputElement>(null)
  const restoreAddFocus = useRef(false)
  const [filter, setFilter] = useState<TaskStatus | 'all'>('pending')
  const [page, setPage] = useState(1)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [missedTaskId, setMissedTaskId] = useState<string | null>(null)
  const [focusedTaskId, setFocusedTaskId] = useState<string | null>(null)
  const [notice, setNotice] = useState('')
  const [showDemo, setShowDemo] = useState(false)
  const [taskRevision, setTaskRevision] = useState(0)
  const tasks = useRecord<TaskPage>(
    `${path}?status=${focusedTaskId ? 'all' : filter}&page=${page}${focusedTaskId ? `&task_id=${focusedTaskId}` : ''}`,
  )
  const livePath = cultivationPath + '/weather'
  const liveWeather = useRecord<FarmWeather>(livePath)
  const weather = useRecord<DemoForecast>(
    import.meta.env.DEV && showDemo ? cultivationPath + '/demo-weather' : null,
  )
  const reviewDate =
    weather.data?.source === 'fixture' ? weather.data.review_due_on : null
  const save = useSave()
  const canChange = !archived && !save.busy && !save.blocked
  const taskEditorOpen = Boolean(draft || missedTaskId)
  const creating = !archived && Boolean(draft && !draft.task)
  const farmToday = tasks.data?.farm_today

  useEffect(() => {
    if (creating) {
      taskTitle.current?.focus({ preventScroll: true })
      const reduceMotion = window.matchMedia?.(
        '(prefers-reduced-motion: reduce)',
      ).matches
      taskForm.current?.scrollIntoView?.({
        behavior: reduceMotion ? 'auto' : 'smooth',
        block: 'nearest',
      })
    } else if (restoreAddFocus.current) {
      restoreAddFocus.current = false
      addTask.current?.focus()
    }
  }, [creating])

  function reloadTasks() {
    setPage(1)
    tasks.reload()
    setTaskRevision((value) => value + 1)
  }
  function refresh(message: string) {
    setNotice(message)
    setDraft(null)
    reloadTasks()
  }
  function submit(event: FormEvent) {
    event.preventDefault()
    if (!canChange || !draft?.title.trim() || !draft.due_date) return
    const { task, title, due_date } = draft
    const fields = { title: title.trim(), due_date }
    setNotice('')
    void save.run(
      () =>
        task
          ? farmWrite<FarmTask>(`${path}/${task.id}`, 'PATCH', {
              ...fields,
              expected_version: task.version,
            })
          : farmWrite<FarmTask>(path, 'POST', fields),
      () => {
        if (!task) setFilter('pending')
        refresh(task ? 'Task saved.' : 'Task added.')
      },
    )
  }
  function close(task: FarmTask, status: 'completed' | 'cancelled') {
    setNotice('')
    void save.run(
      () =>
        farmWrite<FarmTask>(`${path}/${task.id}/status`, 'POST', {
          expected_version: task.version,
          status,
        }),
      () => refresh(`Task ${status}.`),
    )
  }

  const saveError = <SaveError {...save} create={creating} review={review} />
  const editor = !archived && draft && (
    <form ref={taskForm} onSubmit={submit} className="record-stage-form">
      {draft.weatherReview && (
        <p>
          Sample rain falls on the saved due date. Keep it or choose a different
          date.
        </p>
      )}
      <div className="record-form-grid">
        <Field
          label="Task title"
          ref={taskTitle}
          value={draft.title}
          maxLength={120}
          required
          disabled={save.busy}
          onChange={(event) =>
            setDraft({ ...draft, title: event.target.value })
          }
        />
        <Field
          label="Due date"
          type="date"
          value={draft.due_date}
          max="9999-12-31"
          required
          autoFocus={draft.weatherReview}
          disabled={save.busy}
          onChange={(event) =>
            setDraft({ ...draft, due_date: event.target.value })
          }
        />
      </div>
      <div className="record-toolbar">
        <button
          className="primary"
          disabled={!canChange || !draft.title.trim() || !draft.due_date}
        >
          {save.busy ? 'Saving…' : 'Save task'}
        </button>
        <button
          type="button"
          disabled={save.busy}
          onClick={() => {
            if (draft.weatherReview && !save.blocked)
              setNotice('Task date kept.')
            restoreAddFocus.current = creating
            setDraft(null)
            if (!save.blocked) save.reset()
          }}
        >
          {draft.weatherReview && !save.blocked
            ? 'Keep task date'
            : 'Discard draft'}
        </button>
      </div>
    </form>
  )

  return (
    <section className="panel" aria-labelledby="tasks-heading">
      <div className="record-card-top">
        <h2 id="tasks-heading">Farm tasks</h2>
        <div className="button-row">
          <a className="record-link" href="#week-heading">
            This week
          </a>
          {!archived && (!draft || creating) && (
            <button
              ref={addTask}
              type="button"
              className="primary"
              aria-expanded={creating}
              disabled={!canChange || !tasks.data || taskEditorOpen}
              onClick={() => setDraft({ title: '', due_date: '' })}
            >
              Add task
            </button>
          )}
        </div>
      </div>
      {saveError}
      {creating && editor}
      {notice && <Notice success message={notice} />}
      {archived && (
        <p className="muted">Archived cultivation. Tasks are read only.</p>
      )}
      <WeeklyPlanner
        path={cultivationPath + '/week'}
        tasksPath={path}
        planPath={planPath}
        timezone={timezone}
        revision={`${liveWeather.data?.status}:${liveWeather.data?.forecast?.fetched_at}:${taskRevision}`}
        archived={archived}
        blocked={taskEditorOpen || save.busy || save.blocked}
        changed={reloadTasks}
        complete={(task) => close(task, 'completed')}
        openTask={(id) => {
          setFocusedTaskId(id)
          setPage(1)
          document
            .getElementById('cultivation-task-list')
            ?.scrollIntoView?.({ block: 'start' })
        }}
      />
      <details className="panel">
        <summary>Weather and alerts</summary>
        <LiveWeather record={liveWeather} path={livePath} farmPath={farmPath} />
        <WeatherAlerts
          path={livePath + '/alerts'}
          timezone={timezone}
          revision={`${liveWeather.data?.status}:${liveWeather.data?.forecast?.fetched_at}:${taskRevision}`}
          onRescheduled={() => {
            setFilter('pending')
            reloadTasks()
          }}
          onRuleChanged={() => setTaskRevision((value) => value + 1)}
        />
      </details>
      {chilli && (
        <PlannerChat
          path={cultivationPath}
          planPath={planPath}
          timezone={timezone}
          archived={archived}
          blocked={taskEditorOpen || save.busy || save.blocked}
          changed={reloadTasks}
        />
      )}
      {import.meta.env.DEV && (
        <div>
          <button
            type="button"
            aria-expanded={showDemo}
            onClick={() => setShowDemo(!showDemo)}
          >
            {showDemo ? 'Hide demo weather' : 'Show demo weather'}
          </button>
          {showDemo && (
            <DemoWeather
              forecast={weather.data}
              loading={weather.loading}
              retry={weather.reload}
            />
          )}
        </div>
      )}
      {!creating && editor}
      {focusedTaskId && (
        <button
          type="button"
          disabled={taskEditorOpen || save.busy}
          onClick={() => {
            setFocusedTaskId(null)
            setPage(1)
          }}
        >
          Back to task list
        </button>
      )}
      <div className="field" id="cultivation-task-list">
        <label htmlFor={filterId}>Task status</label>
        <select
          id={filterId}
          value={focusedTaskId ? 'all' : filter}
          disabled={save.busy || taskEditorOpen}
          onChange={(event) => {
            setFocusedTaskId(null)
            setFilter(event.target.value as TaskStatus | 'all')
            setPage(1)
          }}
        >
          {Object.entries(statuses).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      {!tasks.data ? (
        <ReadState
          loading={tasks.loading}
          error={tasks.error}
          retry={tasks.reload}
        />
      ) : (
        <>
          {tasks.data.items.length === 0 && (
            <p>
              {filter === 'pending'
                ? 'No pending tasks.'
                : 'No tasks match this filter.'}
            </p>
          )}
          {tasks.data.items.map((task) => {
            const overdue =
              farmToday &&
              task.status === 'pending' &&
              task.due_date < farmToday
            const reviewWeather =
              !archived &&
              task.status === 'pending' &&
              task.due_date === reviewDate
            const weatherDay =
              !archived &&
              task.status === 'pending' &&
              liveWeather.data?.status === 'fresh'
                ? liveWeather.data.forecast?.days.find(
                    (day) => day.date === task.due_date,
                  )
                : undefined
            return (
              <article className="panel" key={task.id}>
                <div className="record-card-top">
                  <h3 className="record-note">{task.title}</h3>
                  <span className="status-pill">{statuses[task.status]}</span>
                </div>
                <p>
                  Due <time dateTime={task.due_date}>{task.due_date}</time>
                  {overdue && ' · Overdue'}
                </p>
                {weatherDay && (
                  <p className="muted">
                    Forecast for the due date · {weatherDay.precipitation_mm} mm
                    precipitation
                  </p>
                )}
                {reviewWeather && (
                  <p className="muted">Demo rain on this task’s due date.</p>
                )}
                {!archived && task.status === 'pending' && (
                  <div className="record-toolbar">
                    {overdue && (
                      <button
                        type="button"
                        disabled={!canChange || taskEditorOpen}
                        onClick={() => {
                          setNotice('')
                          setMissedTaskId(task.id)
                        }}
                      >
                        I missed this task
                      </button>
                    )}
                    <button
                      disabled={!canChange || taskEditorOpen}
                      onClick={() =>
                        setDraft({
                          task,
                          title: task.title,
                          due_date: task.due_date,
                          weatherReview: reviewWeather,
                        })
                      }
                    >
                      {reviewWeather ? 'Review this task' : 'Edit task'}
                    </button>
                    <button
                      disabled={!canChange || taskEditorOpen}
                      onClick={() => close(task, 'completed')}
                    >
                      Mark done
                    </button>
                    <button
                      className="danger-action"
                      disabled={!canChange || taskEditorOpen}
                      onClick={() => close(task, 'cancelled')}
                    >
                      Cancel task
                    </button>
                  </div>
                )}
                {!archived && farmToday && missedTaskId === task.id && (
                  <MissedTaskReview
                    task={task}
                    farmToday={farmToday}
                    taskPath={path}
                    planPath={planPath}
                    timezone={timezone}
                    weather={liveWeather.data}
                    close={() => setMissedTaskId(null)}
                    reload={() => {
                      setMissedTaskId(null)
                      liveWeather.reload()
                      reloadTasks()
                    }}
                    finished={(outcome) => {
                      setMissedTaskId(null)
                      setNotice(
                        outcome === 'accepted'
                          ? 'Task date updated.'
                          : 'Task date kept.',
                      )
                      reloadTasks()
                    }}
                  />
                )}
              </article>
            )
          })}
          {tasks.data.total > tasks.data.page_size && !missedTaskId && (
            <Pagination result={tasks.data} page={page} change={setPage} />
          )}
        </>
      )}
      <SuggestedPlans
        path={planPath}
        timezone={timezone}
        archived={archived}
        blockedByTaskEdit={taskEditorOpen || save.busy || !tasks.data}
        onAccepted={() => {
          setFilter('pending')
          reloadTasks()
        }}
        review={review}
      />
    </section>
  )
}

export function TaskHistory({
  path,
  timezone,
}: {
  path: string
  timezone: string
}) {
  const [page, setPage] = useState(1)
  const history = useRecord<Page<FarmTaskEvent>>(`${path}/history?page=${page}`)
  return (
    <section className="panel" aria-labelledby="task-history-heading">
      <h2 id="task-history-heading">Task history</h2>
      {!history.data ? (
        <ReadState
          loading={history.loading}
          error={history.error}
          retry={history.reload}
        />
      ) : (
        <>
          {history.data.items.length === 0 && <p>No task activity yet.</p>}
          {history.data.items.map((entry) => (
            <article
              className="panel"
              key={`${entry.task_id}:${entry.version}`}
            >
              <h3 className="record-note">{entry.title}</h3>
              <p>
                {actions[entry.action]} · Due {entry.due_date}
              </p>
              <p className="muted">
                {timestamp(entry.occurred_at, timezone)} · {timezone}
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
