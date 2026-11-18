import { useEffect, useState } from 'react'
import { request } from '../../lib/accounts'
import type { Notification, NotificationPage } from '../../lib/notifications'
import Notice from '../../components/Notice'

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Colombo',
  }).format(new Date(value))
}

export default function NotificationsPage() {
  const [page, setPage] = useState<NotificationPage | null>(null)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [pageNumber, setPageNumber] = useState(1)
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    let cancelled = false
    const query = new URLSearchParams({
      page: String(pageNumber),
      page_size: '20',
      unread_only: String(unreadOnly),
    })
    void request<NotificationPage>(`/notifications?${query.toString()}`)
      .then((result) => {
        if (!cancelled) setPage(result)
      })
      .catch((failure) => {
        if (!cancelled)
          setError(
            failure instanceof Error
              ? failure.message
              : 'Notifications could not be loaded.',
          )
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [pageNumber, retry, unreadOnly])

  async function changeReadState(item: Notification) {
    setBusyId(item.id)
    setError('')
    try {
      const updated = await request<Notification>(`/notifications/${item.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ read: !item.read_at }),
      })
      setPage((current) =>
        current
          ? {
              ...current,
              items:
                unreadOnly && !item.read_at
                  ? current.items.filter((row) => row.id !== item.id)
                  : current.items.map((row) =>
                      row.id === item.id ? updated : row,
                    ),
              unread_count: current.unread_count + (item.read_at ? 1 : -1),
              total: current.total - (unreadOnly && !item.read_at ? 1 : 0),
            }
          : current,
      )
      if (unreadOnly && !item.read_at) setRetry((value) => value + 1)
      window.dispatchEvent(new Event('notifications-updated'))
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : 'Notification status could not be changed.',
      )
    } finally {
      setBusyId(null)
    }
  }

  return (
    <>
      <div className="page-intro">
        <p className="eyebrow">Your space / Updates</p>
        <div className="title-row">
          <div>
            <h1>
              Notifications<span>.</span>
            </h1>
            <p>Account updates that are just for you.</p>
          </div>
          <span className="count-label">
            {page?.unread_count ?? '—'} unread
          </span>
        </div>
      </div>
      <section
        className="panel notification-panel"
        aria-labelledby="notifications-title"
      >
        <div className="users-heading">
          <h2 id="notifications-title">Your updates</h2>
          <label className="filter-label">
            Show
            <select
              value={unreadOnly ? 'unread' : 'all'}
              onChange={(event) => {
                setPageNumber(1)
                setUnreadOnly(event.target.value === 'unread')
                setError('')
              }}
            >
              <option value="all">All notifications</option>
              <option value="unread">Unread only</option>
            </select>
          </label>
        </div>
        {error && <Notice message={error} />}
        {loading ? (
          <p className="empty-state" role="status">
            Loading notifications…
          </p>
        ) : !error && page ? (
          page.items.length === 0 ? (
            <div className="empty-state">
              <h3>You’re all caught up.</h3>
              <p>New account and security updates will appear here.</p>
            </div>
          ) : (
            <>
              <ul className="notification-list">
                {page.items.map((item) => (
                  <li
                    className={`notification-entry ${item.read_at ? 'is-read' : 'is-unread'}`}
                    key={item.id}
                  >
                    <div className="notification-entry-content">
                      <div className="notification-title-row">
                        <h3>{item.title}</h3>
                        {!item.read_at && (
                          <span className="status-pill">Unread</span>
                        )}
                      </div>
                      <p>{item.body}</p>
                      <time dateTime={item.created_at}>
                        {formatDate(item.created_at)}
                      </time>
                    </div>
                    <button
                      disabled={busyId === item.id}
                      onClick={() => void changeReadState(item)}
                    >
                      {busyId === item.id
                        ? 'Saving…'
                        : item.read_at
                          ? 'Mark unread'
                          : 'Mark read'}
                    </button>
                  </li>
                ))}
              </ul>
              <div className="pagination">
                <span>
                  Page {page.page} · {page.total} notifications
                </span>
                <div className="button-row">
                  <button
                    disabled={page.page <= 1}
                    onClick={() => setPageNumber((value) => value - 1)}
                  >
                    Previous
                  </button>
                  <button
                    disabled={page.page * page.page_size >= page.total}
                    onClick={() => setPageNumber((value) => value + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )
        ) : null}
      </section>
      <p className="page-footnote">
        These are in-app account updates. Email notifications are not enabled.
      </p>
    </>
  )
}
