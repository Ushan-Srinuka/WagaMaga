import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { useSession } from '../../app/session-context'
import Brand from '../../components/Brand'
import { request } from '../../lib/accounts'
import type { NotificationPage } from '../../lib/notifications'
import FarmActionBar, { FirstFarm } from './FarmActionBar'
import './home.css'

const fieldImage = '/images/chilli-field-hero-v1.webp'
const iconPaths = {
  leaf: 'M19 4C9 3 3 8 5 15c2 7 13 6 14-11ZM5 20 15 10M9 16v-5M9 16h5',
  records: 'M6 3h12v18H6zM9 7h6M9 11h6M9 15h3',
  book: 'M12 5C8 2 3 4 3 4v15s5-2 9 1c4-3 9-1 9-1V4s-5-2-9 1Zm0 0v15',
  plan: 'M6 4h14v17H6zM9 2v4M17 2v4M9 10h7M9 14l2 2 5-5',
  shield: 'M12 2 3 6v6c0 5 9 10 9 10s9-5 9-10V6l-9-4Zm-4 10 3 3 5-6',
  question: 'M9 8a3 3 0 0 1 6 0c0 3-3 2-3 5M12 17h.01M4 3h16v18H4z',
  control: 'M4 7h16M4 17h16M8 4v6M16 14v6',
  bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4',
} as const

function HomeIcon({ name }: { name: keyof typeof iconPaths }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={iconPaths[name]} />
    </svg>
  )
}

const steps = [
  {
    title: 'Record your farm',
    description:
      'Bring field conditions, planting dates and crop observations together in simple records designed for everyday use.',
    icon: 'records',
  },
  {
    title: 'Explore guidance',
    description:
      'Ask questions and explore answers connected to reviewed agricultural sources, with evidence and limitations in view.',
    icon: 'book',
  },
  {
    title: 'Review your next steps',
    description:
      'Compare proposed changes with your current plan. Review the reasons before deciding what happens next.',
    icon: 'control',
  },
] as const

const principles = [
  {
    title: 'Guidance with visible sources',
    description:
      'The planned guidance experience connects answers to reviewed sources so you can inspect what supports a suggestion.',
    detail: 'Evidence you can inspect',
    icon: 'book',
  },
  {
    title: 'Clear explanations when information is missing',
    description:
      'When evidence or field context is missing, the experience should make that gap clear instead of presenting a guess as certainty.',
    detail: 'Uncertainty made visible',
    icon: 'question',
  },
  {
    title: 'Farmer control over proposed changes',
    description:
      'Suggested changes are designed for review. Required advisor clearance and your acceptance come before any eligible change is applied.',
    detail: 'Your decisions stay central',
    icon: 'control',
  },
] as const

export default function HomePage() {
  const { user, phase, restore } = useSession()
  const [unreadCount, setUnreadCount] = useState<{
    userId: string
    count: number
  } | null>(null)
  useEffect(() => {
    if (!user) return
    let active = true
    void request<NotificationPage>('/notifications?page=1&page_size=1')
      .then((result) => {
        if (active)
          setUnreadCount({ userId: user.id, count: result.unread_count })
      })
      .catch(() => {
        if (active) setUnreadCount(null)
      })
    const refreshUnread = () => {
      void request<NotificationPage>('/notifications?page=1&page_size=1')
        .then((result) => {
          if (active)
            setUnreadCount({ userId: user.id, count: result.unread_count })
        })
        .catch(() => {
          if (active) setUnreadCount(null)
        })
    }
    window.addEventListener('notifications-updated', refreshUnread)
    return () => {
      active = false
      window.removeEventListener('notifications-updated', refreshUnread)
    }
  }, [user])
  return (
    <div className="home-page">
      <a className="skip-link" href="#home-main">
        Skip to content
      </a>
      <header className="home-header home-container">
        <Link to="/" className="wordmark" aria-label="WagaMaga AI home">
          <Brand />
        </Link>
        <nav className="home-section-nav" aria-label="Main navigation">
          {user?.role === 'administrator' && (
            <Link to="/admin/overview">Administration</Link>
          )}
          {user?.role === 'farmer' ? (
            <>
              <Link className="home-nav-current" to="/farms">
                <HomeIcon name="leaf" /> My Farms
              </Link>
              <Link to="/farms/new">
                <HomeIcon name="records" /> Add a farm
              </Link>
            </>
          ) : !user ? (
            <a className="home-nav-current" href="#farm-start">
              <HomeIcon name="leaf" /> Farm records
            </a>
          ) : null}
          <a href="#our-vision">Our vision</a>
          <a href="#how-it-works">How it works</a>
          <Link to="/help">Help</Link>
        </nav>
        <div className="home-header-access">
          {phase === 'loading' ? (
            <span className="home-session-label" role="status">
              Checking account…
            </span>
          ) : user ? (
            <>
              <span className="home-session-label">
                Signed in as <strong>{user.display_name}</strong>
              </span>
              <Link
                className="home-notification-link"
                to="/notifications"
                aria-label={
                  unreadCount?.userId === user.id && unreadCount.count > 0
                    ? `Notifications, ${unreadCount.count} unread`
                    : 'Notifications'
                }
              >
                <HomeIcon name="bell" />
                <span>Notifications</span>
                {unreadCount?.userId === user.id && unreadCount.count > 0 && (
                  <span className="home-notification-count" aria-hidden="true">
                    {unreadCount.count > 99 ? '99+' : unreadCount.count}
                  </span>
                )}
              </Link>
              <Link
                className="home-login home-account-link"
                to="/account"
                aria-label="My account"
              >
                <HomeIcon name="control" />
                <span>My account</span>
              </Link>
              {user.role === 'farmer' && (
                <Link className="home-button home-button-dark" to="/farms/new">
                  Add farm <span aria-hidden="true">＋</span>
                </Link>
              )}
            </>
          ) : phase === 'offline' ? (
            <>
              <span className="home-session-label" role="status">
                Account status unavailable
              </span>
              <button
                className="home-login home-session-retry"
                onClick={() => void restore()}
              >
                Retry
              </button>
            </>
          ) : (
            <>
              <span className="home-session-label">You’re signed out</span>
              <Link className="home-login" to="/login">
                Log in
              </Link>
              <Link className="home-button home-button-dark" to="/register">
                Create account
              </Link>
            </>
          )}
        </div>
      </header>

      <main id="home-main">
        <section className="home-hero" aria-labelledby="home-title">
          <img
            className="home-hero-image"
            src={fieldImage}
            width="1672"
            height="941"
            alt="AI-generated view of a chilli field at sunrise"
            fetchPriority="high"
          />
          <div className="home-container home-hero-content">
            <p className="home-eyebrow home-hero-badge">
              <HomeIcon name="leaf" /> Built for Sri Lankan growers
            </p>
            <h1 id="home-title">
              Your farm.
              <br />
              All in one place.
            </h1>
            <p className="home-intro">
              Your fields, your crops, your everyday observations. Start with
              your farm and keep the details together, wherever you grow.
            </p>
            {user?.role === 'farmer' ? (
              <FarmActionBar key={user.id} />
            ) : !user && phase === 'ready' ? (
              <div className="home-farm-start" id="farm-start">
                <p className="home-launcher-caption">
                  A little less paperwork. A little more growing.
                </p>
                <FirstFarm />
                <p className="home-launcher-links">
                  Already have an account?{' '}
                  <Link to="/login">
                    Log in to your farms <span aria-hidden="true">↗</span>
                  </Link>
                </p>
              </div>
            ) : !user ? (
              <div id="farm-start" className="home-farm-start">
                <p role="status">
                  {phase === 'loading'
                    ? 'Checking your account…'
                    : 'Account status is unavailable. Use Retry in the header to reconnect.'}
                </p>
              </div>
            ) : (
              <div className="home-actions">
                <Link className="home-button" to="/account">
                  Open my account <span aria-hidden="true">↗</span>
                </Link>
              </div>
            )}
            <p className="home-availability">
              <span className="home-status-dot" /> Accounts and private farm
              records are available. Chilli first; guidance for Anuradhapura is
              planned and subject to review.
            </p>
            <ul className="home-hero-notes" aria-label="Product direction">
              <li>
                <HomeIcon name="leaf" /> Sri Lankan chilli cultivation
              </li>
              <li>
                <HomeIcon name="book" /> Evidence-led guidance, planned
              </li>
              <li>
                <HomeIcon name="shield" /> Grower control by design
              </li>
            </ul>
          </div>
        </section>

        <section
          className="home-vision home-section home-container"
          id="our-vision"
          aria-labelledby="vision-title"
        >
          <div className="home-section-heading">
            <div>
              <p className="home-eyebrow">
                <HomeIcon name="leaf" /> Product vision
              </p>
              <h2 id="vision-title">Your farm. A clearer way forward.</h2>
              <p className="home-section-intro">
                A farming companion shaped around Sri Lankan chilli cultivation.
                From everyday field notes to better-informed decisions, here’s
                what we’re working towards.
              </p>
            </div>
            <p className="home-development-note">
              <span className="home-status-dot" /> Farm records available;
              guidance and planning next
            </p>
          </div>
          <div className="home-feature-grid" id="planned-features">
            <article className="home-feature-card">
              <div className="home-card-top">
                <span className="home-icon-tile">
                  <HomeIcon name="records" />
                </span>
                <span className="home-roadmap-label">Available</span>
              </div>
              <h3>Farm records</h3>
              <p>
                Keep private farm and cultivation records, add observations and
                review earlier versions when you edit or archive.
              </p>
              <div
                className="home-preview"
                aria-label="Illustrative farm record"
              >
                <p className="home-preview-label">Illustrative preview</p>
                <div className="home-preview-sheet">
                  <span className="home-preview-kicker">
                    Your field notebook
                  </span>
                  <strong>Chilli · Sample plot</strong>
                  <span className="home-preview-row">
                    Cultivation details <HomeIcon name="leaf" />
                  </span>
                  <span className="home-preview-row">
                    Field observations <HomeIcon name="records" />
                  </span>
                </div>
              </div>
            </article>
            <article className="home-feature-card">
              <div className="home-card-top">
                <span className="home-icon-tile home-icon-mint">
                  <HomeIcon name="book" />
                </span>
                <span className="home-roadmap-label">Planned</span>
              </div>
              <h3>Evidence-based guidance</h3>
              <p>
                Explore agricultural questions with supporting sources. See the
                evidence behind an answer, along with its limits.
              </p>
              <div
                className="home-preview"
                aria-label="Illustrative source card"
              >
                <p className="home-preview-label">Illustrative preview</p>
                <div className="home-preview-sheet">
                  <span className="home-preview-kicker">
                    <HomeIcon name="book" /> A source alongside the answer
                  </span>
                  <blockquote>
                    “What information would help me understand my crop?”
                  </blockquote>
                  <span className="home-source-placeholder">
                    Reviewed references would appear here
                  </span>
                </div>
              </div>
            </article>
            <article className="home-feature-card">
              <div className="home-card-top">
                <span className="home-icon-tile">
                  <HomeIcon name="plan" />
                </span>
                <span className="home-roadmap-label">Planned</span>
              </div>
              <h3>Reviewed planning</h3>
              <p>
                Understand proposed task changes before accepting them. Compare
                the reasons and keep your judgement part of the process.
              </p>
              <div
                className="home-preview"
                aria-label="Illustrative plan review"
              >
                <p className="home-preview-label">Illustrative preview</p>
                <div className="home-preview-sheet">
                  <span className="home-preview-kicker">
                    A change to consider
                  </span>
                  <strong>Current plan → proposed plan</strong>
                  <p>Review the explanation and supporting evidence first.</p>
                  <span className="home-preview-status">
                    Your review matters
                  </span>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section
          className="home-workflow home-section"
          id="how-it-works"
          aria-labelledby="workflow-title"
        >
          <div className="home-container">
            <div className="home-centered-heading">
              <p className="home-eyebrow">The planned experience</p>
              <h2 id="workflow-title">
                Simple, transparent farming
                <br />
                guidance in three steps
              </h2>
              <p>
                A clear path from your daily field observations to decisions you
                can understand. This workflow is still on the roadmap.
              </p>
            </div>
            <div className="home-steps">
              {steps.map((step, index) => (
                <article className="home-step-card" key={step.title}>
                  <div className="home-card-top">
                    <span className="home-step-number">0{index + 1}</span>
                    <span className="home-icon-tile">
                      <HomeIcon name={step.icon} />
                    </span>
                  </div>
                  <h3>{step.title}</h3>
                  <p>{step.description}</p>
                  <div
                    className={`home-step-art home-step-art-${index}`}
                    aria-hidden="true"
                  >
                    <span className="home-art-node">
                      <HomeIcon name={step.icon} />
                    </span>
                    <span className="home-art-line" />
                    <span className="home-art-end" />
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section
          className="home-trust home-section home-container"
          id="trust-principles"
          aria-labelledby="trust-title"
        >
          <p className="home-eyebrow">
            <HomeIcon name="shield" /> Governance &amp; autonomy
          </p>
          <h2 id="trust-title">Trust &amp; control principles</h2>
          <p className="home-section-intro">
            Farming decisions belong to the grower. These principles guide the
            tools we’re building.
          </p>
          <div className="home-trust-grid">
            {principles.map((principle) => (
              <article className="home-trust-card" key={principle.title}>
                <span className="home-icon-tile">
                  <HomeIcon name={principle.icon} />
                </span>
                <h3>{principle.title}</h3>
                <p>{principle.description}</p>
                <span className="home-principle-detail">
                  <span aria-hidden="true">✓</span> {principle.detail}
                </span>
              </article>
            ))}
          </div>
          <div className="home-trust-note">
            <span className="home-icon-tile">
              <HomeIcon name="shield" />
            </span>
            <div>
              <strong>Built around informed decisions</strong>
              <p>
                Clear evidence, honest limitations and a meaningful say in what
                happens on your farm.
              </p>
            </div>
            <a href="#how-it-works">
              Explore the approach <span aria-hidden="true">→</span>
            </a>
          </div>
        </section>

        <section
          className="home-start-wrap home-container"
          aria-labelledby="start-title"
        >
          <div className="home-start">
            <p className="home-eyebrow">Start with your account</p>
            <h2 id="start-title">
              Be part of the next
              <br />
              chapter in farming.
            </h2>
            <p>
              Create your WagaMaga AI account
              <br />
              as we build the farming tools ahead.
            </p>
            <Link
              className="home-button"
              to={
                user?.role === 'farmer'
                  ? '/farms'
                  : user
                    ? '/account'
                    : '/register'
              }
            >
              {user?.role === 'farmer'
                ? 'Open my farms'
                : user
                  ? 'Go to my account'
                  : 'Create account'}{' '}
              <span aria-hidden="true">↗</span>
            </Link>
            <p className="home-start-note">
              Registration, sign-in and profile management are available today.
            </p>
          </div>
        </section>
        <section
          className="home-help home-container"
          aria-labelledby="home-help-title"
        >
          <div>
            <p className="home-eyebrow">A little help, when you need it</p>
            <h2 id="home-help-title">Need a hand with your farm records?</h2>
            <p>Find simple guides or contact us when you need help.</p>
          </div>
          <div className="home-help-actions">
            <Link className="home-button home-button-dark" to="/help">
              Visit Help Centre
            </Link>
            <Link
              className="home-button"
              to={user?.role === 'farmer' ? '/support/new' : '/help#sign-in'}
            >
              Contact Support
            </Link>
          </div>
        </section>
      </main>

      <footer className="home-footer">
        <p className="home-footer-banner">
          <span className="home-status-dot" /> Private farm records are
          available. AI guidance and planning are under development.
        </p>
        <div className="home-container">
          <div className="home-footer-main">
            <div className="home-footer-brand">
              <Link to="/" className="wordmark">
                <Brand />
              </Link>
              <p>
                An agricultural companion being built for Sri Lankan growers,
                beginning with chilli cultivation.
              </p>
              <span className="home-footer-tag">
                Local roots. Thoughtful growth.
              </span>
            </div>
            <nav aria-label="Platform navigation">
              <h3>Explore WagaMaga</h3>
              <Link to="/help">Help and support</Link>
              <a href="#our-vision">Our vision</a>
              <a href="#planned-features">Planned features</a>
              <a href="#how-it-works">How it will work</a>
              <a href="#trust-principles">Trust &amp; control</a>
            </nav>
            <nav aria-label="Account navigation">
              <h3>Your account</h3>
              {user ? (
                <>
                  {user.role === 'farmer' && (
                    <Link to="/farms">Farm records</Link>
                  )}
                  <Link to="/account">My account</Link>
                  <Link to="/notifications">Notifications</Link>
                </>
              ) : (
                <>
                  <Link to="/login">Log in</Link>
                  <Link to="/register">Create account</Link>
                </>
              )}
            </nav>
          </div>
          <div className="home-footer-note">
            <span>© {new Date().getFullYear()} WagaMaga AI</span>
            <span>AI-generated field imagery.</span>
            <span>Crafted for agriculture in Sri Lanka.</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
