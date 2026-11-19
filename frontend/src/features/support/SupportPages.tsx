import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import Notice from '../../components/Notice'
import Field from '../../components/Field'
import { Intro, Pagination, TextArea } from '../farms/RecordUI'
import { useRecord, useSave } from '../farms/record-hooks'
import {
  categories,
  statuses,
  supportError,
  supportRead,
  supportWrite,
  type Category,
  type MessagePage,
  type SupportStatus,
  type Ticket,
  type TicketPage,
} from '../../lib/support'
import { ApiError } from '../../lib/accounts'
import './support.css'

function Failed({
  error,
  loading,
  retry,
}: {
  error: unknown
  loading: boolean
  retry: () => void
}) {
  if (loading) return <p role="status">Loading support requests…</p>
  const denied = error instanceof ApiError && [403, 404].includes(error.status)
  return (
    <section className="panel">
      <h2>{denied ? 'Request unavailable' : 'Let’s reconnect'}</h2>
      <Notice message={supportError(error)} />
      {!denied && <button onClick={retry}>Try again</button>}
    </section>
  )
}
function time(value: string) {
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function SupportListPage({ admin = false }: { admin?: boolean }) {
  const [params, setParams] = useSearchParams()
  const status = ['open', 'in_progress', 'resolved', 'all'].includes(
    params.get('status') ?? '',
  )
    ? params.get('status')!
    : 'all'
  const category = Object.hasOwn(categories, params.get('category') ?? '')
    ? params.get('category')!
    : ''
  const page = Math.max(1, Math.min(10000, Number(params.get('page')) || 1))
  const base = admin ? '/admin/support/tickets' : '/support/tickets'
  const ui = admin ? '/admin/support' : '/support'
  const query = new URLSearchParams({ status, page: String(page) })
  if (category) query.set('category', category)
  const records = useRecord<TicketPage>(`${base}?${query}`, supportRead)
  function filter(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    if (key !== 'page') next.delete('page')
    setParams(next)
  }
  return (
    <div className="support-page farm-records">
      <Intro
        eyebrow={admin ? 'Administration / Support' : 'Help / Your requests'}
        title={admin ? 'Support inbox' : 'My support requests'}
      >
        {admin
          ? 'Help farmers with accounts and the website. Only the conversation they submit is shared with you.'
          : 'Ask about using WagaMaga, follow replies and tell us when your issue is resolved.'}
      </Intro>
      <div className="record-toolbar">
        <Link to="/help">Help and common questions</Link>
        {!admin && (
          <Link className="primary record-link" to="/support/new">
            Contact support
          </Link>
        )}
      </div>
      <section className="panel">
        <div className="record-filters">
          <label className="filter-label">
            Request status
            <select
              value={status}
              onChange={(e) => filter('status', e.target.value)}
            >
              <option value="all">All statuses</option>
              {Object.entries(statuses).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-label">
            Request category
            <select
              value={category}
              onChange={(e) => filter('category', e.target.value)}
            >
              <option value="">All categories</option>
              {Object.entries(categories).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
        {!records.data ? (
          <Failed
            loading={records.loading}
            error={records.error}
            retry={records.reload}
          />
        ) : (
          <>
            <p className="muted">
              {records.data.total} matching{' '}
              {records.data.total === 1 ? 'request' : 'requests'}
            </p>
            {records.data.items.length === 0 ? (
              <div className="empty-state">
                <h2>No requests here yet.</h2>
                <p>
                  {admin
                    ? 'New farmer requests will appear here. Try another filter to see earlier requests.'
                    : 'Start with Help, or contact support if you need a hand.'}
                </p>
              </div>
            ) : (
              <ul className="record-rows">
                {records.data.items.map((ticket) => (
                  <li key={ticket.id}>
                    <div>
                      <span className="status-pill">
                        {statuses[ticket.status]}
                      </span>
                      <h3>
                        <Link to={`${ui}/${ticket.id}`}>{ticket.subject}</Link>
                      </h3>
                      <p>
                        {categories[ticket.category]}
                        {admin ? ` · ${ticket.requester_name}` : ''}
                      </p>
                      <small>Updated {time(ticket.updated_at)}</small>
                    </div>
                    <Link
                      className="record-link"
                      to={`${ui}/${ticket.id}`}
                      aria-label={`Open support request: ${ticket.subject}`}
                    >
                      Open ↗
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            <Pagination
              result={records.data}
              page={page}
              change={(value) => filter('page', String(value))}
            />
          </>
        )}
      </section>
      <p className="record-footnote">
        Support requests do not give administrators access to private farm
        records. Crop advice belongs with an agricultural advisor; that workflow
        is not available yet.
      </p>
    </div>
  )
}

export function NewSupportPage() {
  const navigate = useNavigate()
  const [category, setCategory] = useState<Category | ''>('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const save = useSave(supportError)
  function submit(event: FormEvent) {
    event.preventDefault()
    if (!category || !subject.trim() || !body.trim()) return
    void save.run(
      () =>
        supportWrite<Ticket>('/support/tickets', {
          category,
          subject: subject.trim(),
          body: body.trim(),
        }),
      (ticket) => navigate(`/support/${ticket.id}`, { replace: true }),
    )
  }
  return (
    <div className="support-page farm-records">
      <Link className="back-link" to="/support">
        ← My support requests
      </Link>
      <Intro eyebrow="Help / Contact support" title="How can we help?">
        Send a question about your account, farm records or the website.
      </Intro>
      <p className="record-scope">
        Submitting shares the text below with administrators. No farm details or
        observations are attached automatically. Do not include passwords,
        precise coordinates or other sensitive information.
      </p>
      <section className="panel record-editor">
        <h2>New support request</h2>
        <form className="record-form" onSubmit={submit}>
          <fieldset disabled={save.busy || save.blocked}>
            <label className="field">
              What do you need help with?
              <select
                required
                value={category}
                onChange={(e) => setCategory(e.target.value as Category)}
              >
                <option value="">Choose a category</option>
                {Object.entries(categories).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <Field
              label="Subject"
              required
              maxLength={120}
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              hint="A short description, such as Trouble saving my farm."
            />
            <TextArea
              label="Your message"
              required
              maxLength={4000}
              value={body}
              change={setBody}
            />
            <button className="primary" disabled={save.busy || save.blocked}>
              {save.busy ? 'Sending…' : 'Send request'}
            </button>
          </fieldset>
        </form>
        {save.error && <Notice message={save.error} />}
        {save.blocked && (
          <Link className="record-link" to="/support">
            Review saved requests before sending again
          </Link>
        )}
      </section>
    </div>
  )
}

export function SupportDetailPage({ admin = false }: { admin?: boolean }) {
  const { ticketId = '' } = useParams()
  return (
    <Conversation key={`${admin}:${ticketId}`} id={ticketId} admin={admin} />
  )
}
function Conversation({ id, admin }: { id: string; admin: boolean }) {
  const base = admin ? '/admin/support/tickets' : '/support/tickets'
  const ui = admin ? '/admin/support' : '/support'
  const ticket = useRecord<Ticket>(`${base}/${id}`, supportRead)
  const [page, setPage] = useState(1)
  const messages = useRecord<MessagePage>(
    ticket.data ? `${base}/${id}/messages?page=${page}` : null,
    supportRead,
  )
  const [body, setBody] = useState('')
  const [notice, setNotice] = useState('')
  const save = useSave(supportError)
  function reload() {
    setBody('')
    setNotice('')
    save.reset()
    ticket.reload()
    messages.reload()
  }
  if (ticket.error || messages.error || !ticket.data || !messages.data)
    return (
      <Failed
        loading={
          !ticket.error &&
          !messages.error &&
          (ticket.loading || messages.loading)
        }
        error={ticket.error ?? messages.error}
        retry={reload}
      />
    )
  const record = ticket.data
  const canReply = record.status !== 'resolved' && record.requester_available
  function done(next: Ticket, text: string) {
    ticket.replace(next)
    setBody('')
    setPage(1)
    messages.reload()
    setNotice(text)
    window.dispatchEvent(new Event('notifications-updated'))
  }
  function submit(event: FormEvent) {
    event.preventDefault()
    if (!body.trim() || !canReply) return
    void save.run(
      () =>
        supportWrite<Ticket>(`${base}/${id}/messages`, {
          expected_version: record.version,
          body: body.trim(),
        }),
      (next) => done(next, 'Reply sent.'),
    )
  }
  function change(status: SupportStatus) {
    void save.run(
      () =>
        supportWrite<Ticket>(`${base}/${id}/status`, {
          expected_version: record.version,
          status,
        }),
      (next) => done(next, 'Request status updated.'),
    )
  }
  const blocked = save.busy || save.blocked || Boolean(body.trim())
  return (
    <div className="support-page farm-records">
      <Link className="back-link" to={ui}>
        ← {admin ? 'Support inbox' : 'My support requests'}
      </Link>
      <Intro eyebrow="Help / Support conversation" title={record.subject}>
        {categories[record.category]}
        {admin ? ` · Submitted by ${record.requester_name}` : ''}
      </Intro>
      {notice && <Notice success message={notice} />}
      <div className="record-toolbar">
        <span className="status-pill">{statuses[record.status]}</span>
        {record.status === 'resolved' ? (
          <button disabled={blocked} onClick={() => change('open')}>
            Reopen request
          </button>
        ) : (
          <>
            {admin && record.status === 'open' && (
              <button disabled={blocked} onClick={() => change('in_progress')}>
                Mark in progress
              </button>
            )}
            <button disabled={blocked} onClick={() => change('resolved')}>
              Mark resolved
            </button>
          </>
        )}
        <button disabled={save.busy || Boolean(body.trim())} onClick={reload}>
          Refresh conversation
        </button>
      </div>
      {save.error && <Notice message={save.error} />}
      {save.blocked && (
        <>
          <p>
            Your draft remains here. Reloading discards it and shows the latest
            saved conversation.
          </p>
          <button onClick={reload}>Reload latest conversation</button>
        </>
      )}
      {body.trim() && (
        <p className="muted">
          Send or clear your draft before changing status or refreshing.
        </p>
      )}
      <section className="panel" aria-labelledby="support-conversation">
        <h2 id="support-conversation">Conversation</h2>
        <p className="muted">
          Times use your device timezone. Only the submitted messages are
          shared.
        </p>
        <ol className="support-messages">
          {[...messages.data.items].reverse().map((message) => (
            <li
              key={message.id}
              className={
                message.author_role === 'administrator' ? 'support-answer' : ''
              }
            >
              <div className="record-card-top">
                <strong>
                  {message.author_role === 'administrator'
                    ? 'Support team'
                    : admin
                      ? 'Farmer'
                      : 'You'}
                </strong>
                <time dateTime={message.created_at}>
                  {time(message.created_at)}
                </time>
              </div>
              <p>{message.body}</p>
            </li>
          ))}
        </ol>
        <Pagination result={messages.data} page={page} change={setPage} />
      </section>
      {canReply ? (
        <section className="panel record-editor">
          <h2>{admin ? 'Reply to the farmer' : 'Reply to support'}</h2>
          <form className="record-form" onSubmit={submit}>
            <fieldset disabled={save.busy || save.blocked}>
              <TextArea
                label="Your reply"
                required
                value={body}
                change={setBody}
                maxLength={4000}
              />
              <div className="button-row">
                <button
                  className="primary"
                  disabled={save.busy || save.blocked || !body.trim()}
                >
                  {save.busy ? 'Sending…' : 'Send reply'}
                </button>
                {body && (
                  <button
                    type="button"
                    disabled={save.busy}
                    onClick={() => setBody('')}
                  >
                    Clear draft
                  </button>
                )}
              </div>
            </fieldset>
          </form>
        </section>
      ) : (
        <p className="record-scope">
          {record.status === 'resolved'
            ? 'This request is resolved. Reopen it if you need to continue the conversation.'
            : 'The requester account is unavailable for replies. Support can still resolve the request.'}
        </p>
      )}
      <p className="record-footnote">
        Support cannot access your private farms or act on your behalf. This is
        website support, not agricultural advice or account recovery.
      </p>
    </div>
  )
}
