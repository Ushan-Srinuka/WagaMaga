import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useSession } from '../../app/session-context'
import Brand from '../../components/Brand'
import { request } from '../../lib/accounts'
import { signedInHome } from '../../lib/navigation'
import type { NotificationPage } from '../../lib/notifications'
import './home.css'

const farmFeatures = [
  {
    title: 'My Farms',
    description: 'Keep all your farms and crops in one place.',
    action: 'View farms',
    path: '/farms',
  },
  {
    title: 'Field notes',
    description: 'Save what you notice in the field and find it again later.',
    action: 'Write a note',
    path: '/field-notes/new',
  },
  {
    title: 'Planner',
    description: 'See what’s due today and what’s coming up.',
    action: 'View tasks',
    path: '/planner',
  },
]

export default function HomePage() {
  const { user, phase, restore } = useSession()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuButton = useRef<HTMLButtonElement>(null)
  const [unread, setUnread] = useState<{ id: string; count: number } | null>(
    null,
  )
  useEffect(() => {
    if (!user) return
    let active = true
    function refresh() {
      void request<NotificationPage>('/notifications?page=1&page_size=1')
        .then((result) => {
          if (active && user)
            setUnread({ id: user.id, count: result.unread_count })
        })
        .catch(() => {
          if (active) setUnread(null)
        })
    }
    refresh()
    window.addEventListener('notifications-updated', refresh)
    return () => {
      active = false
      window.removeEventListener('notifications-updated', refresh)
    }
  }, [user])
  const count = unread && unread.id === user?.id ? unread.count : 0
  const isFarmer = user?.role === 'farmer'
  const isVisitor = !user && phase === 'ready'
  return (
    <div className="home-page">
      <a className="skip-link" href="#home-main">
        Skip to content
      </a>
      <header
        className="home-top"
        id="home-top"
        tabIndex={-1}
        onKeyDown={(event) => {
          if (event.key === 'Escape' && menuOpen) {
            setMenuOpen(false)
            menuButton.current?.focus()
          }
        }}
      >
        <Link className="wordmark" to="/" aria-label="WagaMaga AI home">
          <Brand />
        </Link>
        <button
          ref={menuButton}
          className="home-nav-button home-menu-toggle"
          type="button"
          aria-expanded={menuOpen}
          aria-controls="home-navigation"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          Menu
        </button>
        <nav
          id="home-navigation"
          className={menuOpen ? 'home-nav-open' : undefined}
          aria-label="Main navigation"
          onClick={(event) => {
            if (event.target instanceof Element && event.target.closest('a'))
              setMenuOpen(false)
          }}
        >
          <a href="#home-top">Home</a>
          <a href="#chilli-ai">What you can do</a>
          <a href="#farm-features">Farm tools</a>
          <a href="#getting-started">Getting started</a>
          <Link to="/help">Help</Link>
          {isVisitor && (
            <Link className="home-nav-button home-nav-primary" to="/login">
              Log in
            </Link>
          )}
          {user && (
            <>
              <Link
                className="home-nav-button home-notifications"
                to="/notifications"
                aria-label={
                  count ? `Notifications, ${count} unread` : 'Notifications'
                }
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  width="22"
                  height="22"
                >
                  <path d="M18 8a6 6 0 0 0-12 0c0 7-3 8-3 9h18c0-1-3-2-3-9M10 21h4" />
                </svg>
                {count > 0 && (
                  <span className="home-unread-count" aria-hidden="true">
                    {count > 99 ? '99+' : count}
                  </span>
                )}
              </Link>
              <Link className="home-nav-button home-nav-primary" to="/account">
                My account
              </Link>
            </>
          )}
        </nav>
      </header>
      <main id="home-main" tabIndex={-1}>
        <section className="home-hero" aria-labelledby="home-hero-title">
          <img
            className="home-field"
            src="/images/chilli-field-hero-v1.webp"
            width="1672"
            height="941"
            alt=""
            fetchPriority="high"
          />
          <div className="home-hero-inner">
            <div className="home-content">
              {isFarmer ? (
                <>
                  <p className="home-greeting">Hello, {user.display_name}</p>
                  <h1 id="home-hero-title">
                    What would you like to <span>do today?</span>
                  </h1>
                  <nav className="home-tools" aria-label="Farm tools">
                    <Link className="home-ask" to="/knowledge/chilli">
                      Ask Chilli AI <span aria-hidden="true">↗</span>
                    </Link>
                    <Link className="home-note" to="/field-notes/new">
                      Add a field note <span aria-hidden="true">＋</span>
                    </Link>
                    <Link to="/farms">My Farms</Link>
                    <Link to="/planner">Planner</Link>
                  </nav>
                </>
              ) : user ? (
                <>
                  <h1 id="home-hero-title">
                    {user.role === 'advisor'
                      ? 'Advisor workspace'
                      : 'Administration'}
                  </h1>
                  <Link className="home-primary" to={signedInHome(user.role)}>
                    {user.role === 'advisor'
                      ? 'Open advisor inbox'
                      : 'Open admin overview'}
                  </Link>
                </>
              ) : (
                <>
                  <h1 id="home-hero-title">
                    Ask <span>Chilli AI</span>
                  </h1>
                  <p>
                    Ask about growing chilli, keep field notes and plan your
                    farm work.
                  </p>
                  {phase === 'ready' ? (
                    <div className="home-entry">
                      <Link className="home-primary" to="/login?ask=chilli">
                        Log in to ask
                      </Link>
                      <Link to="/register">Create account</Link>
                    </div>
                  ) : phase === 'offline' ? (
                    <div>
                      <p role="alert">We couldn’t check your account.</p>
                      <button onClick={() => void restore()}>Retry</button>
                    </div>
                  ) : (
                    <p role="status">Checking your account…</p>
                  )}
                </>
              )}
            </div>
          </div>
        </section>
        <section
          className="home-section home-ai-section"
          aria-labelledby="chilli-ai"
        >
          <div className="home-section-inner home-ai-grid">
            <div>
              <h2 id="chilli-ai" tabIndex={-1}>
                Ask Chilli AI
              </h2>
              <p>
                Ask a question about growing chilli and open the source behind a
                supported answer.
              </p>
              {(isFarmer || isVisitor) && (
                <Link
                  className="home-section-action"
                  to={isFarmer ? '/knowledge/chilli' : '/login?ask=chilli'}
                >
                  {isFarmer ? 'Ask a chilli question' : 'Sign in for Chilli AI'}
                </Link>
              )}
            </div>
            <figure className="home-question">
              <figcaption>Try asking</figcaption>
              <blockquote>
                What should I check when choosing a chilli nursery site?
              </blockquote>
            </figure>
          </div>
        </section>
        <section className="home-section" aria-labelledby="farm-features">
          <div className="home-section-inner">
            <h2 id="farm-features" tabIndex={-1}>
              Manage your farm
            </h2>
            <ul className="home-feature-list">
              {farmFeatures.map((feature) => (
                <li key={feature.path}>
                  <h3>{feature.title}</h3>
                  <p>{feature.description}</p>
                  {(isFarmer || isVisitor) && (
                    <Link to={isFarmer ? feature.path : '/login'}>
                      {isFarmer
                        ? feature.action
                        : `Log in to ${feature.action.toLowerCase()}`}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </section>
        <section
          className="home-section home-start-section"
          aria-labelledby="getting-started"
        >
          <div className="home-section-inner">
            <h2 id="getting-started" tabIndex={-1}>
              Getting started
            </h2>
            <ol className="home-steps">
              <li>
                <h3>Add a farm</h3>
                <p>Give your farm a name and tell us where it is.</p>
              </li>
              <li>
                <h3>Add a crop</h3>
                <p>Open your farm and choose what you’re growing.</p>
              </li>
              <li>
                <h3>Save a field note</h3>
                <p>
                  Write down something you noticed while checking your crop.
                </p>
              </li>
            </ol>
            {(isFarmer || isVisitor) && (
              <Link
                className="home-section-action"
                to={isFarmer ? '/farms/new' : '/register'}
              >
                {isFarmer ? 'Add a farm' : 'Create a farmer account'}
              </Link>
            )}
          </div>
        </section>
      </main>
      <footer className="home-footer">
        <div className="home-footer-inner">
          <div>
            <a
              className="wordmark"
              href="#home-top"
              aria-label="WagaMaga AI, back to top"
            >
              <Brand />
            </a>
            <p>
              Chilli-growing answers, field notes and farm planning in one
              place.
            </p>
          </div>
          <nav aria-label="Footer navigation">
            <a href="#chilli-ai">Chilli AI</a>
            <a href="#farm-features">Farm tools</a>
            <a href="#getting-started">Getting started</a>
            <Link to="/help">Help centre</Link>
            {isFarmer && <Link to="/support/new">Contact support</Link>}
          </nav>
        </div>
      </footer>
    </div>
  )
}
