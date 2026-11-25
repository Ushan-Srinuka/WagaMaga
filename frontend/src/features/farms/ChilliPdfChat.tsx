import { useEffect, useState } from 'react'
import ConfirmDialog from '../../components/ConfirmDialog'
import Notice from '../../components/Notice'
import { farmWrite, timestamp, type Page } from '../../lib/farms'
import { Pagination, ReadState } from './RecordUI'
import { useRecord, useSave } from './record-hooks'

type Summary = { id: string; revision: number; created_at: string }
type Job = {
  id: string
  revision: number
  state: 'queued' | 'running' | 'failed' | 'succeeded'
}
const messages = {
  answered: '',
  no_evidence:
    'The reviewed sources did not provide an answer to this question.',
  clarify:
    'Check the farm district and confirmed crop stage, or name the topic you want to ask about.',
  unavailable: 'Gemini is unavailable or was not enabled for this question.',
  source_unavailable: 'The supporting passage is no longer available.',
}
type History = Summary & {
  stage: string | null
  district: string
  turns: {
    ordinal: number
    question: string
    outcome: keyof typeof messages
    answer: string | null
    citation: {
      title: string
      publisher: string
      page_number: number
      version_id: string
      language: string
      body: string
    } | null
  }[]
}

export default function ChilliPdfChat({
  path,
  timezone,
  archived,
}: {
  path: string
  timezone: string
  archived: boolean
}) {
  const root = `${path}/chilli-chats`
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<string | null>(null)
  const [question, setQuestion] = useState('')
  const [useGemini, setUseGemini] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const save = useSave()
  const list = useRecord<Page<Summary>>(`${root}?page=${page}`)
  const active = selected ? `${root}/${selected}` : null
  const history = useRecord<History>(active)
  const jobs = useRecord<{ job: Job | null }>(active ? active + '/jobs' : null)
  const job = jobs.data?.job
  const pending = job?.state === 'queued' || job?.state === 'running'
  const reloadJobs = jobs.reload
  const reloadHistory = history.reload
  const reloadList = list.reload
  const revision = history.data?.revision

  useEffect(() => {
    if (pending) {
      const timer = window.setTimeout(reloadJobs, 1200)
      return () => window.clearTimeout(timer)
    }
    if (
      job?.state === 'succeeded' &&
      revision !== undefined &&
      revision <= job.revision
    ) {
      reloadHistory()
      reloadList()
    }
  }, [job, pending, revision, reloadJobs, reloadHistory, reloadList])

  function open(id: string | null) {
    setSelected(id)
    setQuestion('')
    setUseGemini(false)
    save.reset()
  }

  return (
    <section className="panel" aria-labelledby="chilli-pdf-chat-heading">
      <h2 id="chilli-pdf-chat-heading">Ask Chilli AI about reviewed PDFs</h2>
      <div className="button-row">
        {!archived && (
          <button
            type="button"
            disabled={save.busy || save.blocked}
            onClick={() =>
              void save.run(
                () => farmWrite<Summary>(root, 'POST', {}),
                (chat) => {
                  open(chat.id)
                  setPage(1)
                  list.reload()
                },
              )
            }
          >
            New chilli chat
          </button>
        )}
        <label className="field">
          Saved conversations
          <select
            value={
              list.data?.items.some((item) => item.id === selected)
                ? (selected ?? '')
                : ''
            }
            disabled={save.busy || list.loading}
            onChange={(event) => open(event.target.value || null)}
          >
            <option value="">Choose a conversation</option>
            {list.data?.items.map((chat) => (
              <option key={chat.id} value={chat.id}>
                {timestamp(chat.created_at, timezone)} · {chat.revision}{' '}
                questions
              </option>
            ))}
          </select>
        </label>
      </div>
      {list.error !== undefined && (
        <ReadState error={list.error} loading={false} retry={list.reload} />
      )}
      {list.data && (
        <Pagination result={list.data} page={page} change={setPage} />
      )}
      {active && !history.data && (
        <ReadState
          error={history.error}
          loading={history.loading}
          retry={history.reload}
        />
      )}
      {history.data && active && (
        <>
          <p className="muted">
            Recorded district · {history.data.district || 'Unknown'} · Crop
            stage · {history.data.stage ?? 'Unknown'}
          </p>
          <ol aria-label="Conversation" className="record-rows">
            {history.data.turns.map((turn) => (
              <li key={turn.ordinal}>
                <article className="record-inset">
                  <h3 className="record-note">{turn.question}</h3>
                  <p className="record-note">
                    {turn.answer ?? messages[turn.outcome]}
                  </p>
                  {turn.citation && (
                    <details>
                      <summary>
                        {turn.citation.title} · PDF page{' '}
                        {turn.citation.page_number}
                      </summary>
                      <p className="record-note" lang={turn.citation.language}>
                        {turn.citation.body}
                      </p>
                      <small>
                        {turn.citation.publisher} · Version{' '}
                        {turn.citation.version_id}
                      </small>
                    </details>
                  )}
                </article>
              </li>
            ))}
          </ol>
          {pending && <p role="status">Question pending · {job.state}</p>}
          {jobs.error !== undefined && (
            <button type="button" onClick={reloadJobs}>
              Reload question status
            </button>
          )}
          {job?.state === 'failed' &&
            job.revision === history.data.revision && (
              <>
                <Notice message="The question could not be completed. Retry it or ask a different question." />
                {!archived && (
                  <button
                    type="button"
                    disabled={save.busy || save.blocked}
                    onClick={() =>
                      void save.run(
                        () =>
                          farmWrite<Job>(
                            `${active}/jobs/${job.id}/retry`,
                            'POST',
                            {},
                          ),
                        (retried) => jobs.replace({ job: retried }),
                      )
                    }
                  >
                    Retry question
                  </button>
                )}
              </>
            )}
          {!archived && history.data.revision < 20 && (
            <form
              className="record-form"
              onSubmit={(event) => {
                event.preventDefault()
                if (
                  !question.trim() ||
                  save.busy ||
                  save.blocked ||
                  pending ||
                  jobs.loading
                )
                  return
                const revision = history.data?.revision
                void save.run(
                  () =>
                    farmWrite<Job>(active + '/jobs', 'POST', {
                      question: question.trim(),
                      expected_revision: revision,
                      use_gemini: useGemini,
                    }),
                  (queued) => {
                    setQuestion('')
                    jobs.replace({ job: queued })
                  },
                )
              }}
            >
              <label className="field">
                Your chilli question
                <input
                  value={question}
                  required
                  maxLength={240}
                  disabled={save.busy}
                  onChange={(event) => setQuestion(event.target.value)}
                />
              </label>
              <label className="field">
                <input
                  type="checkbox"
                  checked={useGemini}
                  disabled={save.busy}
                  onChange={(event) => setUseGemini(event.target.checked)}
                />
                Use Gemini for answers. This sends the question, recent
                follow-up context and eligible PDF excerpts.
              </label>
              <button
                disabled={
                  !question.trim() ||
                  save.busy ||
                  save.blocked ||
                  pending ||
                  jobs.loading
                }
              >
                Ask about PDFs
              </button>
            </form>
          )}
          {history.data.revision >= 20 && (
            <p>Start a new chat to ask another question.</p>
          )}
          <button
            type="button"
            disabled={save.busy}
            onClick={() => {
              save.reset()
              setConfirmDelete(true)
            }}
          >
            Delete conversation
          </button>
        </>
      )}
      {save.busy && <p role="status">Working on your chilli chat…</p>}
      {save.error && !confirmDelete && <Notice message={save.error} />}
      {save.blocked && !confirmDelete && (
        <button
          type="button"
          onClick={() => {
            save.reset()
            list.reload()
            history.reload()
          }}
        >
          Reload conversations
        </button>
      )}
      {confirmDelete && active && (
        <ConfirmDialog
          eyebrow="Chilli chat"
          title="Delete this conversation?"
          description="This removes the saved conversation from WagaMaga. Farm plans and required audit records are stored separately and retained."
          busy={save.busy}
          error={save.error}
          confirmDisabled={save.blocked}
          confirmLabel="Delete conversation"
          onClose={() => {
            setConfirmDelete(false)
            save.reset()
          }}
          onConfirm={() =>
            void save.run(
              () => farmWrite<void>(active, 'DELETE', undefined),
              () => {
                setConfirmDelete(false)
                open(null)
                setPage(1)
                list.reload()
              },
            )
          }
        />
      )}
    </section>
  )
}
