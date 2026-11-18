import { useEffect, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router'
import Notice from '../../components/Notice'
import { request, type AccountPage } from '../../lib/accounts'

export default function UsersPage() {
  const [params, setParams] = useSearchParams()
  const [query, setQuery] = useState(params.get('q') ?? '')
  const [page, setPage] = useState<AccountPage | null>(null)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let cancelled = false
    void request<AccountPage>(`/admin/users?${params.toString()}`)
      .then((result) => {
        if (!cancelled) setPage(result)
      })
      .catch((failure) => {
        if (!cancelled)
          setError(
            failure instanceof Error
              ? failure.message
              : 'Could not load accounts.',
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
    setLoading(true)
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
        <p className="eyebrow">Administration / People</p>
        <div className="title-row">
          <div>
            <h1>
              A place for everyone<span>.</span>
            </h1>
            <p>Manage accounts with clarity and care.</p>
          </div>
          <span className="count-label">{page?.total ?? '—'} accounts</span>
        </div>
      </div>
      <section className="panel users-panel" aria-labelledby="users-title">
        <div className="users-heading">
          <h2 id="users-title">User management</h2>
          <span className="muted">Account access only</span>
        </div>
        <div className="user-filters">
          <form onSubmit={search} className="search-form">
            <label className="visually-hidden" htmlFor="user-search">
              Search accounts
            </label>
            <input
              id="user-search"
              type="search"
              value={query}
              maxLength={100}
              placeholder="Search by name or email"
              onChange={(e) => setQuery(e.target.value)}
            />
            <button>Search</button>
          </form>
          <label className="filter-label">
            Role
            <select
              value={params.get('role') ?? ''}
              onChange={(e) => filter('role', e.target.value)}
            >
              <option value="">All roles</option>
              <option value="farmer">Farmer</option>
              <option value="advisor">Advisor</option>
              <option value="administrator">Administrator</option>
            </select>
          </label>
          <label className="filter-label">
            Status
            <select
              value={params.get('status') ?? ''}
              onChange={(e) => filter('status', e.target.value)}
            >
              <option value="">All statuses</option>
              <option value="enabled">Active</option>
              <option value="disabled">Disabled</option>
              <option value="deleted">Deleted</option>
            </select>
          </label>
        </div>
        {error && (
          <>
            <Notice message={error} />
            <button
              onClick={() => {
                setError('')
                setLoading(true)
                setRetry(retry + 1)
              }}
            >
              Try again
            </button>
          </>
        )}
        {loading ? (
          <p className="empty-state" role="status">
            Loading accounts…
          </p>
        ) : (
          !error &&
          page && (
            <>
              {page.items.length === 0 ? (
                <div className="empty-state">
                  <h3>No accounts found.</h3>
                  <p>Try a different name, email or filter.</p>
                </div>
              ) : (
                <div className="user-table">
                  <div className="user-table-head" aria-hidden="true">
                    <span>Account</span>
                    <span>Role</span>
                    <span>Status</span>
                    <span>Details</span>
                  </div>
                  <ul className="user-rows">
                    {page.items.map((account) => (
                      <li key={account.id}>
                        <div className="user-identity">
                          <span className="avatar" aria-hidden="true">
                            {account.display_name.slice(0, 1)}
                          </span>
                          <div>
                            <strong>{account.display_name}</strong>
                            <span className="user-email">{account.email}</span>
                          </div>
                        </div>
                        <span className="role-badge">{account.role}</span>
                        <span
                          className={`status-pill ${account.deleted_at || account.disabled_at ? 'disabled' : ''}`}
                        >
                          {account.deleted_at
                            ? 'Deleted'
                            : account.disabled_at
                              ? 'Disabled'
                              : 'Active'}
                        </span>
                        <Link
                          className="detail-link"
                          to={`/admin/users/${account.id}`}
                          aria-label={`View ${account.display_name}`}
                        >
                          View <span aria-hidden="true">↗</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="pagination">
                <span>
                  Page {page.page} · {page.total} matching accounts
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
          )
        )}
      </section>
      <p className="page-footnote">
        Administrator access manages accounts. Private farming records remain
        private.
      </p>
    </>
  )
}
