import { useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router'
import Notice from '../../components/Notice'
import { request } from '../../lib/accounts'

type AuditAction =
  | 'bootstrap'
  | 'role'
  | 'status'
  | 'account_deleted'
  | 'password_changed'
  | 'audit_viewed'

type AuditEvent = {
  id: string
  actor_id: string
  actor_name: string | null
  target_id: string
  target_name: string | null
  action: string
  previous_value: string | null
  new_value: string
  reason: string
  request_id: string
  created_at: string
}

type AuditPageData = {
  items: AuditEvent[]
  total: number
  page: number
  page_size: number
}

const actionLabels: Record<AuditAction, string> = {
  bootstrap: 'Administrator created',
  role: 'Role changed',
  status: 'Account status changed',
  account_deleted: 'Account removed',
  password_changed: 'Password changed',
  audit_viewed: 'Audit history viewed',
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Colombo',
  }).format(new Date(value))
}

export default function AuditPage() {
  const [params, setParams] = useSearchParams()
  const [query, setQuery] = useState(params.get('q') ?? '')
  const [page, setPage] = useState<AuditPageData | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    let cancelled = false
    void request<AuditPageData>(`/admin/audit-logs?${params.toString()}`)
      .then((result) => {
        if (!cancelled) setPage(result)
      })
      .catch((failure) => {
        if (!cancelled)
          setError(
            failure instanceof Error
              ? failure.message
              : 'Audit history could not be loaded.',
          )
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [params, retry])

  function filter(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    if (key !== 'page') next.delete('page')
    setError('')
    setParams(next)
  }

  function search(event: FormEvent) {
    event.preventDefault()
    filter('q', query)
  }

  return (
    <>
      <div className="page-intro">
        <p className="eyebrow">Administration / Accountability</p>
        <div className="title-row">
          <div>
            <h1>
              Audit history<span>.</span>
            </h1>
            <p>Important account and security actions, in one place.</p>
          </div>
          <span className="count-label">{page?.total ?? '—'} records</span>
        </div>
      </div>
      <section className="panel audit-panel" aria-labelledby="audit-title">
        <div className="users-heading">
          <h2 id="audit-title">Recorded actions</h2>
          <span className="muted">Viewing this history is recorded.</span>
        </div>
        <div className="user-filters audit-filters">
          <form onSubmit={search} className="search-form">
            <label className="visually-hidden" htmlFor="audit-search">
              Search account name or email
            </label>
            <input
              id="audit-search"
              type="search"
              maxLength={100}
              value={query}
              placeholder="Search actor or account"
              onChange={(event) => setQuery(event.target.value)}
            />
            <button>Search</button>
          </form>
          <label className="filter-label">
            Action
            <select
              value={params.get('action') ?? ''}
              onChange={(event) => filter('action', event.target.value)}
            >
              <option value="">All actions</option>
              {Object.entries(actionLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-label">
            From
            <input
              type="date"
              value={params.get('from_date') ?? ''}
              onChange={(event) => filter('from_date', event.target.value)}
            />
          </label>
          <label className="filter-label">
            To
            <input
              type="date"
              value={params.get('to_date') ?? ''}
              onChange={(event) => filter('to_date', event.target.value)}
            />
          </label>
        </div>
        {error && (
          <>
            <Notice message={error} />
            <button
              onClick={() => {
                setError('')
                setRetry((value) => value + 1)
              }}
            >
              Try again
            </button>
          </>
        )}
        {loading ? (
          <p className="empty-state" role="status">
            Loading audit history…
          </p>
        ) : (
          !error &&
          page &&
          (page.items.length === 0 ? (
            <div className="empty-state">
              <h3>No matching actions.</h3>
              <p>Try another account, action or date range.</p>
            </div>
          ) : (
            <>
              <ol className="audit-list">
                {page.items.map((event) => (
                  <li className="audit-entry" key={event.id}>
                    <div className="audit-entry-heading">
                      <div>
                        <span className="section-number">
                          {actionLabels[event.action as AuditAction] ??
                            event.action}
                        </span>
                        <h3>{event.target_name ?? 'Account unavailable'}</h3>
                      </div>
                      <time dateTime={event.created_at}>
                        {formatDate(event.created_at)}
                      </time>
                    </div>
                    <dl className="audit-details">
                      <div>
                        <dt>Actor</dt>
                        <dd>{event.actor_name ?? 'Account unavailable'}</dd>
                      </div>
                      <div>
                        <dt>Change</dt>
                        <dd>
                          {event.previous_value ?? '—'} → {event.new_value}
                        </dd>
                      </div>
                      <div>
                        <dt>Reason</dt>
                        <dd>{event.reason}</dd>
                      </div>
                    </dl>
                    <details className="audit-reference">
                      <summary>Record references</summary>
                      <p>Actor ID: {event.actor_id}</p>
                      <p>Account ID: {event.target_id}</p>
                      <p>Request ID: {event.request_id}</p>
                    </details>
                  </li>
                ))}
              </ol>
              <div className="pagination">
                <span>
                  Page {page.page} · {page.total} matching records
                </span>
                <div className="button-row">
                  <button
                    disabled={page.page <= 1}
                    onClick={() => filter('page', String(page.page - 1))}
                  >
                    Previous
                  </button>
                  <button
                    disabled={page.page * page.page_size >= page.total}
                    onClick={() => filter('page', String(page.page + 1))}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          ))
        )}
      </section>
      <p className="page-footnote">
        This is account audit history, not server diagnostics. Reasons should
        not contain passwords, tokens or private farm information.
      </p>
    </>
  )
}
