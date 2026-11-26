import { Link } from 'react-router'
import { useSession } from '../../app/session-context'
import Brand from '../../components/Brand'
import { request } from '../../lib/accounts'
import { useRecord } from '../farms/record-hooks'
import './support.css'

const questions = [
  [
    'How do I start?',
    'Open My Farms and choose Add your first farm. Give it a name and location, then choose Add a crop. From Home, choose Add a field note whenever you notice something.',
  ],
  [
    'Do I need latitude and longitude?',
    'No. Choose your district and enter a village/town, or describe the location yourself. Exact coordinates are optional. If you are at the farm, Use my current location can fill them after you approve browser permission. Check the result before saving.',
  ],
  [
    'Where are my archived farms?',
    'Open My Farms and choose Farm status → Archived. Archive keeps records and history, and makes the farm read-only. Open Farm details and choose Restore farm to use it again. Separately archived crops remain archived.',
  ],
  [
    'Does Delete farm erase all data?',
    'Delete removes access from your workspace after archiving and typing the farm name to confirm. Historical records remain stored. Deleted farms cannot be restored through the site. This is not permanent data erasure.',
  ],
  [
    'Who can read my farm records?',
    'Your farm records belong to your account. Administrators cannot open them just because they manage accounts. A support request shares only the messages you choose to submit, without automatically attaching farm details.',
  ],
  [
    'What if a save fails or says the record changed?',
    'Keep your draft and read the message. For a conflict, reload and review the latest record before sending again. If a connection fails, a save may already have happened: review existing records first to avoid duplicates.',
  ],
  [
    'Can support tell me which fertilizer or treatment to use?',
    'Website support helps with accounts, features and technical problems. Agricultural advice belongs with a qualified agricultural advisor. The advisor case workflow and AI guidance are not available yet; do not rely on website support for crop diagnoses or treatment decisions.',
  ],
]

export default function HelpPage() {
  const { user, phase } = useSession()
  const contact = useRecord<{ email: string | null }>('/help/contact', request)
  return (
    <div className="help-page">
      <a className="skip-link" href="#help-main">
        Skip to content
      </a>
      <header className="help-header help-container">
        <Link className="wordmark" to="/" aria-label="WagaMaga AI home">
          <Brand />
        </Link>
        <nav aria-label="Help navigation">
          <Link to="/">Home</Link>
          {phase === 'loading' ? (
            <span role="status">Checking account…</span>
          ) : user?.role === 'farmer' ? (
            <Link to="/support">My support requests</Link>
          ) : user?.role === 'administrator' ? (
            <Link to="/admin/support">Support inbox</Link>
          ) : user ? (
            <Link to="/account">My account</Link>
          ) : (
            <Link to="/login">Log in</Link>
          )}
        </nav>
      </header>
      <main id="help-main" className="help-container">
        <section className="help-intro">
          <h1>How can we help?</h1>
          <p>
            Get started with your farm records, find an answer or send a
            question to support.
          </p>
          <div className="button-row">
            <a className="primary record-link" href="#common-questions">
              Read common questions
            </a>
            {user?.role === 'farmer' && (
              <Link className="record-link" to="/support/new">
                Contact website support
              </Link>
            )}
          </div>
        </section>
        <section className="help-start" aria-labelledby="help-start-title">
          <h2 id="help-start-title">Your first farm, in three steps</h2>
          <ol>
            <li>
              <strong>Add your farm</strong>
              <p>
                Use a name you recognise and tell us where it is. Coordinates
                and farm size can wait.
              </p>
            </li>
            <li>
              <strong>Add what you are growing</strong>
              <p>
                Choose the crop and record a planting date and planted area. We
                call this a cultivation record.
              </p>
            </li>
            <li>
              <strong>Keep field notes</strong>
              <p>
                Choose Add a field note on Home. Write what you saw, then choose
                Save note.
              </p>
            </li>
          </ol>
          {user?.role === 'farmer' ? (
            <Link className="record-link" to="/farms/new">
              Add a farm ↗
            </Link>
          ) : !user && phase === 'ready' ? (
            <Link className="record-link" to="/register">
              Create a farmer account ↗
            </Link>
          ) : null}
        </section>
        <section
          className="help-faq"
          id="common-questions"
          aria-labelledby="help-questions-title"
        >
          <p className="eyebrow">Common questions</p>
          <h2 id="help-questions-title">Find your answer</h2>
          {questions.map(([question, answer]) => (
            <details key={question}>
              <summary>{question}</summary>
              <p>{answer}</p>
            </details>
          ))}
        </section>
        <section
          id="sign-in"
          className="help-contact"
          aria-labelledby="help-contact-title"
        >
          <div>
            <p className="eyebrow">Still need a hand?</p>
            <h2 id="help-contact-title">Contact website support</h2>
            <p>
              Tell us what you were trying to do and what happened. Never send
              your password. Farm records and crop observations are not shared
              automatically.
            </p>
            {user?.role === 'farmer' ? (
              <Link className="primary record-link" to="/support/new">
                Send a support request
              </Link>
            ) : !user && phase === 'ready' ? (
              <Link className="primary record-link" to="/login">
                Log in to send a request
              </Link>
            ) : null}
          </div>
          <div>
            <h3>Cannot sign in?</h3>
            <p>
              Account recovery is not available yet. Support messages do not
              reset passwords or bypass identity checks.
            </p>
            {contact.loading ? (
              <p role="status">Loading contact details…</p>
            ) : contact.data?.email ? (
              <p>
                <a href={`mailto:${contact.data.email}`}>
                  {contact.data.email}
                </a>
              </p>
            ) : contact.error ? (
              <>
                <p>Contact details could not be loaded.</p>
                <button onClick={contact.reload}>Retry contact details</button>
              </>
            ) : (
              <p>
                A public support email has not been configured yet. Contact your
                pilot organizer using the details they provided.
              </p>
            )}
          </div>
        </section>
        <p className="record-footnote">
          Manual records are available. Initial crop: chilli. Planned guidance
          focuses on Anuradhapura, subject to agricultural review. AI and
          advisor support are not available yet.
        </p>
      </main>
      <footer className="help-container help-footer">
        <Brand />
        <Link to="/">Back to WagaMaga</Link>
      </footer>
    </div>
  )
}
