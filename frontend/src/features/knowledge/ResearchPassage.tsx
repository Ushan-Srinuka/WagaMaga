import { useId, useState } from 'react'
import { ApiError } from '../../lib/accounts'
import Notice from '../../components/Notice'
import { useRecord } from '../farms/record-hooks'

export type SourcePassage = {
  id: string
  corpus_version: string
  question: string
  source_note: string
  citation: {
    title: string
    publisher: string
    url: string
  } & ({ section: string } | { journal_page: number; pdf_page: number })
}

export default function ResearchPassage({
  version,
  id,
}: {
  version: string
  id: string
}) {
  const [open, setOpen] = useState(false)
  const panelId = useId()
  const record = useRecord<SourcePassage>(
    open ? `/knowledge/chilli/research/sources/${version}/${id}` : null,
  )
  return (
    <>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen(!open)}
      >
        {open ? 'Hide supporting passage' : 'Show supporting passage'}
      </button>
      <div id={panelId} hidden={!open}>
        {record.loading && <p role="status">Loading supporting passage…</p>}
        {record.error !== undefined &&
          (record.error instanceof ApiError &&
          [403, 404].includes(record.error.status) ? (
            <Notice message="This supporting passage is unavailable." />
          ) : (
            <>
              <Notice message="The supporting passage could not be loaded." />
              <button type="button" onClick={record.reload}>
                Retry supporting passage
              </button>
            </>
          ))}
        {record.data && (
          <div
            className="record-inset"
            role="region"
            aria-label="Supporting passage"
          >
            <p className="muted">English paraphrase of the cited source</p>
            <p>{record.data.source_note}</p>
            <small>{record.data.corpus_version}</small>
          </div>
        )}
      </div>
    </>
  )
}
