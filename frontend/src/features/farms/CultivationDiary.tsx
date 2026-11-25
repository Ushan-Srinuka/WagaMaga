import { useState } from 'react'
import { Link } from 'react-router'
import type { Page } from '../../lib/farms'
import { timestamp } from '../../lib/farms'
import { Pagination, ReadState } from './RecordUI'
import { useRecord } from './record-hooks'

const labels = {
  observation: 'Observation',
  created: 'Task added manually',
  edited: 'Task edited manually',
  completed: 'Task completed',
  cancelled: 'Task cancelled',
  create_task: 'Task added from a plan',
  reschedule_task: 'Task date changed from a plan',
  plan_declined: 'Plan declined',
  weather_rescheduled: 'Task date changed after weather review',
  weather_kept: 'Task date kept after weather review',
  missed_task_kept: 'Missed task date kept',
}

type DiaryEntry = {
  id: string
  kind: keyof typeof labels
  occurred_at: string
  description: string
  soil_moisture: string | null
  previous_due_date: string | null
  due_date: string | null
  revision: number | null
  evidence: string | null
  weekly_review: boolean
}

export function CultivationDiary({
  path,
  timezone,
}: {
  path: string
  timezone: string
}) {
  const [page, setPage] = useState(1)
  const diary = useRecord<Page<DiaryEntry>>(`${path}/diary?page=${page}`)
  return (
    <section className="record-history" aria-labelledby="diary-heading">
      <h2 id="diary-heading">Cultivation diary</h2>
      {diary.loading || diary.error || !diary.data ? (
        <ReadState
          loading={diary.loading}
          error={diary.error}
          retry={diary.reload}
        />
      ) : (
        <>
          {diary.data.items.length === 0 && (
            <p className="muted">No activities recorded yet.</p>
          )}
          {diary.data.items.map((entry) => (
            <article
              className="panel"
              key={`${entry.kind}:${entry.id}:${entry.revision}`}
            >
              <h3>{labels[entry.kind]}</h3>
              <time className="muted" dateTime={entry.occurred_at}>
                {timestamp(entry.occurred_at, timezone)} · {timezone}
              </time>
              <p className="record-note">{entry.description}</p>
              {entry.soil_moisture && (
                <p>Reported soil moisture: {entry.soil_moisture}</p>
              )}
              {entry.due_date && (
                <p>
                  {[
                    'weather_kept',
                    'missed_task_kept',
                    'plan_declined',
                  ].includes(entry.kind)
                    ? entry.previous_due_date
                      ? `Kept ${entry.previous_due_date} · Suggested ${entry.due_date}`
                      : `Declined date ${entry.due_date}`
                    : `Due date: ${
                        entry.previous_due_date &&
                        entry.previous_due_date !== entry.due_date
                          ? `${entry.previous_due_date} → `
                          : ''
                      }${entry.due_date}`}
                </p>
              )}
              {entry.evidence && (
                <p className="record-note">{entry.evidence}</p>
              )}
              {entry.kind === 'observation' && (
                <Link to={`${path}/observations/${entry.id}/history`}>
                  View observation history
                </Link>
              )}
              {entry.weekly_review && (
                <Link to={`/plan-reviews/${entry.id}`}>
                  View weekly plan review
                </Link>
              )}
              {!entry.weekly_review && entry.evidence && (
                <a href="#plan-history-heading">View plan decisions</a>
              )}
              {!entry.evidence && entry.kind !== 'observation' && (
                <a href="#task-history-heading">View task history</a>
              )}
            </article>
          ))}
          <Pagination result={diary.data} page={page} change={setPage} />
        </>
      )}
    </section>
  )
}
