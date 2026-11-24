import { useState } from 'react'
import { Link } from 'react-router'
import Notice from '../../components/Notice'
import {
  farmWrite,
  weeklyPlanStatus,
  type Page,
  type TaskPlanDecision,
  type WeeklyPlan,
} from '../../lib/farms'
import { Pagination, ReadState } from './RecordUI'
import TaskDateComparison from './TaskDateComparison'
import { useRecord, useSave } from './record-hooks'

export default function WeeklyBatch({
  path,
  timezone,
  changed,
}: {
  path: string
  timezone: string
  changed: () => void
}) {
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<WeeklyPlan[]>([])
  const [saved, setSaved] = useState<WeeklyPlan[]>([])
  const [notice, setNotice] = useState('')
  const record = useRecord<Page<WeeklyPlan>>(`${path}?page=${page}`)
  const save = useSave()
  const disabled = save.busy || save.blocked

  function prepare() {
    setSaved([])
    setNotice('')
    void save.run(
      () => farmWrite<{ prepared: number }>(`${path}/prepare`, 'POST', {}),
      (result) => {
        setNotice(
          result.prepared
            ? 'Weekly suggestions are ready to review.'
            : 'No new suggestions are supported by the current forecast.',
        )
        setSelected([])
        setPage(1)
        record.reload()
      },
    )
  }

  function accept() {
    setSaved([])
    setNotice('')
    void save.run(
      () =>
        farmWrite<{ decisions: TaskPlanDecision[] }>(`${path}/accept`, 'POST', {
          changes: selected.map((item) => ({
            plan_id: item.id,
            expected_version: item.version,
            action_hash: item.action_hash,
          })),
        }),
      (result) => {
        const accepted = new Set(
          result.decisions.map((decision) => decision.plan_id),
        )
        setSaved(selected.filter((item) => accepted.has(item.id)))
        setSelected([])
        setPage(1)
        record.reload()
        changed()
      },
    )
  }

  return (
    <section className="panel" aria-label="Review weekly changes">
      <h4>Review weekly changes</h4>
      <p>Choose the ready changes you want to save together.</p>
      <div className="record-toolbar">
        <button type="button" disabled={disabled} onClick={prepare}>
          Prepare weekly suggestions
        </button>
        <button
          type="button"
          disabled={save.busy}
          onClick={() => {
            save.reset()
            setSelected([])
            record.reload()
          }}
        >
          Refresh weekly suggestions
        </button>
      </div>
      {notice && <p role="status">{notice}</p>}
      {save.error && <Notice message={save.error} />}
      {saved.length > 0 && (
        <section aria-label="Saved weekly changes">
          <h5>Saved weekly changes</h5>
          <ul>
            {saved.map((item) => (
              <li key={item.id}>
                {item.title} · {item.current_due_date} →{' '}
                {item.proposed_due_date}
              </li>
            ))}
          </ul>
        </section>
      )}
      {!record.data ? (
        <ReadState
          loading={record.loading}
          error={record.error}
          retry={record.reload}
        />
      ) : (
        <>
          {record.data.items.length === 0 && (
            <p>No pending weekly suggestions.</p>
          )}
          {record.data.items.map((item) => {
            const checked = selected.some((plan) => plan.id === item.id)
            const canAccept = item.state === 'ready' || item.state === 'cleared'
            return (
              <article className="record-inset" key={item.id}>
                <h5 className="record-note">{item.title}</h5>
                <p>{weeklyPlanStatus[item.state]}</p>
                <TaskDateComparison plan={item} timezone={timezone} />
                {canAccept && (
                  <label>
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={disabled || (!checked && selected.length >= 20)}
                      onChange={(event) =>
                        setSelected(
                          event.target.checked
                            ? [...selected, item]
                            : selected.filter((plan) => plan.id !== item.id),
                        )
                      }
                    />{' '}
                    Select change for {item.title}
                  </label>
                )}{' '}
                <Link to={`/plan-reviews/${item.id}`}>Open suggestion</Link>
              </article>
            )
          })}
          {!save.busy && (
            <Pagination result={record.data} page={page} change={setPage} />
          )}
          <button
            type="button"
            className="primary"
            disabled={disabled || selected.length === 0}
            onClick={accept}
          >
            Accept selected changes ({selected.length})
          </button>
        </>
      )}
    </section>
  )
}

export function WeeklyReviewHistory({
  path,
  timezone,
}: {
  path: string
  timezone: string
}) {
  const [page, setPage] = useState(1)
  const record = useRecord<Page<WeeklyPlan>>(`${path}/history?page=${page}`)
  return (
    <section className="panel" aria-label="Weekly suggestion history">
      <h2>Weekly suggestion history</h2>
      {!record.data ? (
        <ReadState
          loading={record.loading}
          error={record.error}
          retry={record.reload}
        />
      ) : (
        <>
          {!record.data.items.length && <p>No weekly suggestions yet.</p>}
          {record.data.items.map((item) => (
            <article key={item.id} className="record-inset">
              <h3 className="record-note">{item.title}</h3>
              <p>{weeklyPlanStatus[item.state]}</p>
              <TaskDateComparison plan={item} timezone={timezone} />
              {item.prior_proposed_date && (
                <p>Previous suggestion · {item.prior_proposed_date}</p>
              )}
              {item.advisor_reason && (
                <p className="record-note">
                  Advisor reason · {item.advisor_reason}
                </p>
              )}
              <Link to={`/plan-reviews/${item.id}`}>Open suggestion</Link>
            </article>
          ))}
          <Pagination result={record.data} page={page} change={setPage} />
        </>
      )}
    </section>
  )
}
