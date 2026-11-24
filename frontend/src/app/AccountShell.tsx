import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router'
import { useSession } from './session-context'
import { request, signOut } from '../lib/accounts'
import type { NotificationPage } from '../lib/notifications'
import Notice from '../components/Notice'
import Brand from '../components/Brand'

export default function AccountShell() {
  const { user } = useSession()
  const [menu, setMenu] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [unreadCount, setUnreadCount] = useState<number | null>(null)
  useEffect(() => {
    let active = true
    const loadUnread = () => {
      void request<NotificationPage>('/notifications?page=1&page_size=1')
        .then((result) => {
          if (active) setUnreadCount(result.unread_count)
        })
        .catch(() => {
          if (active) setUnreadCount(null)
        })
    }
    if (!user) return
    loadUnread()
    window.addEventListener('notifications-updated', loadUnread)
    const timer =
      user.role === 'farmer' || user.role === 'advisor'
        ? window.setInterval(() => {
            if (document.visibilityState === 'visible') loadUnread()
          }, 60_000)
        : undefined
    return () => {
      active = false
      window.clearInterval(timer)
      window.removeEventListener('notifications-updated', loadUnread)
    }
  }, [user])
  async function logout() {
    setBusy(true)
    setError('')
    try {
      await signOut()
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : 'Sign out could not be completed.',
      )
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="workspace">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="workspace-header">
        <Link to="/" className="wordmark">
          <Brand />
        </Link>
        <div className="header-account">
          <span className="avatar" aria-hidden="true">
            {user?.display_name.slice(0, 1)}
          </span>
          <span>{user?.display_name}</span>
          <button
            className="menu-button"
            aria-expanded={menu}
            aria-controls="account-nav"
            onClick={() => setMenu(!menu)}
          >
            Menu
          </button>
        </div>
      </header>
      <div className="workspace-body">
        <aside id="account-nav" className={`sidebar ${menu ? 'is-open' : ''}`}>
          <span className="nav-label">Your workspace</span>
          <nav aria-label="Account navigation">
            {user?.role === 'administrator' && (
              <NavLink to="/admin/overview" onClick={() => setMenu(false)}>
                <span aria-hidden="true">⌂</span> Admin Overview
              </NavLink>
            )}
            {user?.role === 'farmer' && (
              <NavLink to="/" onClick={() => setMenu(false)}>
                <span aria-hidden="true">⌂</span> Home
              </NavLink>
            )}
            {user?.role === 'farmer' && (
              <NavLink to="/farms" onClick={() => setMenu(false)}>
                <span aria-hidden="true">♧</span> My Farms
              </NavLink>
            )}
            {user?.role === 'farmer' && (
              <NavLink to="/knowledge/chilli" onClick={() => setMenu(false)}>
                Chilli questions
              </NavLink>
            )}
            <NavLink to="/account" onClick={() => setMenu(false)}>
              <span aria-hidden="true">◉</span> My account
            </NavLink>
            {user?.role === 'advisor' && (
              <NavLink to="/advisor/cases" onClick={() => setMenu(false)}>
                Assigned plan reviews
              </NavLink>
            )}
            {user?.role === 'farmer' && (
              <NavLink to="/support" onClick={() => setMenu(false)}>
                <span aria-hidden="true">?</span> My support requests
              </NavLink>
            )}
            {user?.role === 'administrator' && (
              <NavLink to="/admin/knowledge" onClick={() => setMenu(false)}>
                Knowledge Sources
              </NavLink>
            )}
            {user?.role === 'administrator' && (
              <NavLink to="/admin/support" onClick={() => setMenu(false)}>
                <span aria-hidden="true">?</span> Support inbox
              </NavLink>
            )}
            <NavLink to="/help" onClick={() => setMenu(false)}>
              <span aria-hidden="true">ⓘ</span> Help
            </NavLink>
            {user?.role === 'administrator' && (
              <NavLink to="/admin/users" onClick={() => setMenu(false)}>
                <span aria-hidden="true">☷</span> User management
              </NavLink>
            )}
            {user?.role === 'administrator' && (
              <NavLink to="/admin/audit" onClick={() => setMenu(false)}>
                <span aria-hidden="true">▤</span> Audit history
              </NavLink>
            )}
            <NavLink to="/notifications" onClick={() => setMenu(false)}>
              <span aria-hidden="true">◌</span> Notifications
              {unreadCount !== null && unreadCount > 0 && (
                <span
                  className="notification-count"
                  aria-label={`${unreadCount} unread notifications`}
                >
                  {unreadCount > 99 ? '99+' : unreadCount}
                </span>
              )}
            </NavLink>
          </nav>
          <div className="sidebar-bottom">
            <span className="role-badge">{user?.role}</span>
            <p>
              A considered place
              <br />
              to begin.
            </p>
            <button disabled={busy} onClick={logout}>
              {busy ? 'Signing out…' : 'Sign out'}{' '}
              <span aria-hidden="true">↗</span>
            </button>
          </div>
        </aside>
        <main id="main-content" className="workspace-content">
          {error && <Notice message={error} />}
          <Outlet key={`${user?.id}:${user?.role}`} />
        </main>
      </div>
    </div>
  )
}
