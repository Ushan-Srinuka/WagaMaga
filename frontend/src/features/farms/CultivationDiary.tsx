import { useState } from 'react'
import { Link } from 'react-router'
import type { Page } from '../../lib/farms'
import { timestamp } from '../../lib/farms'
import { Pagination, ReadState } from './RecordUI'
import { useRecord } from './record-hooks'

const labels = {
  observation: 'Observation',
  completed: 'Task completed',
  cancelled: 'Task cancelled',
  create_task: 'Task added from a plan',
  reschedule_task: 'Task date changed from a plan',
}

type DiaryEntry = {
  id: string
  kind: keyof typeof labels
  occurred_at: string
  description: string
  soil_moisture: string | null
  previous_due_date: string | null
  due_date: string | null
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
            <article className="panel" key={`${entry.kind}:${entry.id}`}>
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
                  Due date:{' '}
                  {entry.previous_due_date && `${entry.previous_due_date} → `}
                  {entry.due_date}
                </p>
              )}
              {entry.kind === 'observation' && (
                <Link to={`${path}/observations/${entry.id}/history`}>
                  View observation history
                </Link>
              )}
            </article>
          ))}
          <Pagination result={diary.data} page={page} change={setPage} />
        </>
      )}
    </section>
  )
}
