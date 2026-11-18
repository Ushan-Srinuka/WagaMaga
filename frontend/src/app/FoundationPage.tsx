import { useEffect, useState } from 'react'
import Brand from '../components/Brand'
import { readFoundationHealth } from '../lib/api'
import '../App.css'

type Connection =
  | { state: 'loading' }
  | { state: 'connected'; databaseReady: boolean }
  | { state: 'error' }

export default function App() {
  const [attempt, setAttempt] = useState(0)
  const [connection, setConnection] = useState<Connection>({ state: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 8000)
    let cancelled = false

    async function check() {
      try {
        const health = await readFoundationHealth(controller.signal)
        if (!controller.signal.aborted) {
          setConnection({
            state: 'connected',
            databaseReady: health.databaseReady,
          })
        }
      } catch {
        if (!cancelled) setConnection({ state: 'error' })
      } finally {
        window.clearTimeout(timeout)
      }
    }

    void check()
    return () => {
      cancelled = true
      controller.abort()
      window.clearTimeout(timeout)
    }
  }, [attempt])

  function refresh() {
    setConnection({ state: 'loading' })
    setAttempt((value) => value + 1)
  }

  const connected = connection.state === 'connected'
  return (
    <div className="shell">
      <header className="brand">
        <span className="wordmark">
          <Brand />
        </span>
      </header>
      <main>
        <p className="eyebrow">M0 / Project foundation</p>
        <h1>A foundation for informed cultivation.</h1>
        <p className="intro">
          WagaMaga brings farming guidance and cultivation activities together.
          This first build checks the application connection. Farm records,
          advisory and planning will arrive in later milestones.
        </p>
        <section
          className="connection-panel"
          aria-labelledby="connection-title"
        >
          <div className="panel-heading">
            <h2 id="connection-title">Connection status</h2>
            <button onClick={refresh} disabled={connection.state === 'loading'}>
              Check connection
            </button>
          </div>
          <div
            className="status-grid"
            aria-live="polite"
            aria-busy={connection.state === 'loading'}
          >
            <div className="status-item">
              <span className="status-label">API</span>
              <strong>
                {connection.state === 'loading'
                  ? 'Checking...'
                  : connected
                    ? 'Connected'
                    : 'Unavailable'}
              </strong>
            </div>
            <div className="status-item">
              <span className="status-label">Database</span>
              <strong>
                {connection.state === 'loading'
                  ? 'Checking...'
                  : connected && connection.databaseReady
                    ? 'Ready'
                    : 'Not ready'}
              </strong>
            </div>
          </div>
          {connection.state === 'error' && (
            <p className="notice" role="alert">
              The API could not be reached. Start the API and try again.
            </p>
          )}
          {connected && !connection.databaseReady && (
            <p className="notice">
              The API is running. Check PostgreSQL and apply the database
              migration.
            </p>
          )}
          <a
            className="docs-link"
            href="/docs"
            target="_blank"
            rel="noreferrer"
          >
            Open API documentation <span aria-hidden="true">↗</span>
          </a>
        </section>
      </main>
      <footer>Evidence first. Human decisions. Traceable activities.</footer>
    </div>
  )
}
