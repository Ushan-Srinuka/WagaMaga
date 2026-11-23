import { useId, useState, type FormEvent } from 'react'
import Field from '../../components/Field'
import Notice from '../../components/Notice'
import type {
  DemoForecast,
  FarmTask,
  FarmTaskEvent,
  FarmWeather,
  Page,
  TaskStatus,
} from '../../lib/farms'
import { farmWrite, timestamp } from '../../lib/farms'
import DemoWeather from './DemoWeather'
import LiveWeather from './LiveWeather'
import { Pagination, ReadState, SaveError } from './RecordUI'
import { useRecord, useSave } from './record-hooks'
import SuggestedPlans from './SuggestedPlans'
import WeatherAlerts from './WeatherAlerts'

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
  review,
}: {
  path: string
  planPath: string
  cultivationPath: string
  farmPath: string
  timezone: string
  archived: boolean
  review: () => void
}) {
  const filterId = useId()
  const [filter, setFilter] = useState<TaskStatus | 'all'>('pending')
  const [page, setPage] = useState(1)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [notice, setNotice] = useState('')
  const [showDemo, setShowDemo] = useState(false)
  const [taskRevision, setTaskRevision] = useState(0)
  const tasks = useRecord<Page<FarmTask>>(
    `${path}?status=${filter}&page=${page}`,
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

  return (
    <section className="panel" aria-labelledby="tasks-heading">
      <div className="record-card-top">
        <h2 id="tasks-heading">Farm tasks</h2>
        {!archived && !draft && (
          <button
            className="primary"
            disabled={!canChange || !tasks.data}
            onClick={() => setDraft({ title: '', due_date: '' })}
          >
            Add task
          </button>
        )}
      </div>
      {archived && (
        <p className="muted">Archived cultivation. Tasks are read only.</p>
      )}
      <LiveWeather record={liveWeather} path={livePath} farmPath={farmPath} />
      <WeatherAlerts
        path={livePath + '/alerts'}
        timezone={timezone}
        revision={`${liveWeather.data?.status}:${liveWeather.data?.forecast?.fetched_at}:${taskRevision}`}
        onRescheduled={() => {
          setFilter('pending')
          reloadTasks()
        }}
      />
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
      {notice && <Notice success message={notice} />}
      <SaveError
        {...save}
        create={Boolean(draft && !draft.task)}
        review={review}
      />
      {!archived && draft && (
        <form onSubmit={submit} className="record-stage-form">
          {draft.weatherReview && (
            <p>
              Sample rain falls on the saved due date. Keep it or choose a
              different date.
            </p>
          )}
          <div className="record-form-grid">
            <Field
              label="Task title"
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
      )}
      <div className="field">
        <label htmlFor={filterId}>Task status</label>
        <select
          id={filterId}
          value={filter}
          disabled={save.busy || Boolean(draft)}
          onChange={(event) => {
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
                    <button
                      disabled={!canChange || Boolean(draft)}
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
                      disabled={!canChange || Boolean(draft)}
                      onClick={() => close(task, 'completed')}
                    >
                      Mark complete
                    </button>
                    <button
                      className="danger-action"
                      disabled={!canChange || Boolean(draft)}
                      onClick={() => close(task, 'cancelled')}
                    >
                      Cancel task
                    </button>
                  </div>
                )}
              </article>
            )
          })}
          {tasks.data.total > tasks.data.page_size && (
            <Pagination result={tasks.data} page={page} change={setPage} />
          )}
        </>
      )}
      <SuggestedPlans
        path={planPath}
        timezone={timezone}
        archived={archived}
        blockedByTaskEdit={Boolean(draft) || save.busy || !tasks.data}
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
